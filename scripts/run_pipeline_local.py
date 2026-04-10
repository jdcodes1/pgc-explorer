"""Run the PGC pipeline with local parquet download for reliable correlation.

Downloads parquet files locally in batches (Step 1), then runs DuckDB
correlation entirely offline (Step 2). No HF requests during correlation.
"""

import os
import sys
import json
import time
import pickle
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load .env for HF_TOKEN
env_file = project_root / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            key, val = line.split("=", 1)
            os.environ.setdefault(key.strip(), val.strip())

import duckdb
import numpy as np
import polars as pl

from pgc_explorer.config import DISORDERS, DATA_DIR, DisorderDataset, normalize_columns
from pgc_explorer.loader import load_disorder, get_connection, build_hf_path
from pgc_explorer.analysis import _build_beta_expr
from pgc_explorer.export import (
    export_manhattan_data,
    export_network_graph,
    export_correlation_matrix,
    export_metadata,
)

P_THRESHOLD_MANHATTAN = 1e-5
BATCH_SIZE = 2
PAUSE_BETWEEN_BATCHES = 180  # 3 min between batches
PAUSE_BETWEEN_DATASETS = 30  # 30s between datasets
MAX_RETRIES = 5
RETRY_BACKOFF = 90  # seconds

LOCAL_PARQUET_DIR = project_root / "data" / "parquet_cache"
CACHE_FILE = project_root / "data" / ".pipeline_cache.pkl"


def _verify_parquet(path: Path) -> bool:
    """Check if a parquet file is valid (not truncated/corrupt)."""
    try:
        con = duckdb.connect()
        count = con.execute(f"SELECT COUNT(*) FROM '{path}'").fetchone()[0]
        con.close()
        return count > 0
    except Exception:
        return False


def load_cached():
    if CACHE_FILE.exists():
        with open(CACHE_FILE, "rb") as f:
            return pickle.load(f)
    return {}


def save_cached(data):
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_FILE, "wb") as f:
        pickle.dump(data, f)


def download_parquet(disorder: DisorderDataset) -> Path:
    """Download all parquet files for a disorder to local disk.

    Uses DuckDB to COPY the remote parquet glob into a single local parquet file.
    This means DuckDB handles auth, streaming, and schema merging.
    """
    local_dir = LOCAL_PARQUET_DIR / disorder.config
    local_file = local_dir / "data.parquet"

    if local_file.exists():
        if _verify_parquet(local_file):
            return local_file
        else:
            local_file.unlink()

    local_dir.mkdir(parents=True, exist_ok=True)
    hf_path = build_hf_path(disorder)

    con = get_connection()
    try:
        # First discover columns to check for schema issues
        schema_df = con.execute(f"SELECT * FROM '{hf_path}' LIMIT 1").fetchdf()
        col_map = normalize_columns(list(schema_df.columns))

        # Build SELECT with only the columns we need for correlation
        select_cols = []
        for canonical, source in col_map.items():
            if canonical in ("snp", "chr", "bp", "p", "beta", "or_val", "se"):
                select_cols.append(f'"{source}"')

        if not select_cols:
            raise ValueError(f"No usable columns in {disorder.name}")

        select_str = ", ".join(select_cols)

        # Download via CREATE TABLE then export — this ensures the data is
        # fully materialized before writing, so partial downloads don't
        # create corrupt parquet files.
        con.execute(f"""
            CREATE TABLE _download AS
            SELECT {select_str}
            FROM '{hf_path}'
        """)
        row_count = con.execute("SELECT COUNT(*) FROM _download").fetchone()[0]
        if row_count == 0:
            raise RuntimeError("Downloaded 0 rows")
        con.execute(f"""
            COPY _download TO '{local_file}' (FORMAT PARQUET, COMPRESSION ZSTD)
        """)
        con.execute("DROP TABLE _download")
    finally:
        con.close()

    # Verify the download isn't corrupt
    if not _verify_parquet(local_file):
        local_file.unlink(missing_ok=True)
        raise RuntimeError(f"Downloaded file is corrupt (truncated parquet)")

    return local_file


def download_with_retry(disorder: DisorderDataset) -> Path | None:
    """Download with retries and exponential backoff."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            path = download_parquet(disorder)
            size_mb = path.stat().st_size / (1024 * 1024)
            print(f"    -> downloaded ({size_mb:.1f} MB)")
            return path
        except Exception as e:
            err = str(e)
            if ("429" in err or "503" in err) and attempt < MAX_RETRIES:
                wait = RETRY_BACKOFF * attempt
                print(f"    Rate limited, waiting {wait}s (attempt {attempt}/{MAX_RETRIES})...")
                time.sleep(wait)
            elif "union_by_name" in err.lower() or "schema mismatch" in err.lower():
                # Schema mismatch — try with union_by_name
                print(f"    Schema mismatch, trying union_by_name...")
                try:
                    return download_parquet_union(disorder)
                except Exception as e2:
                    print(f"    -> FAILED even with union_by_name: {e2}")
                    return None
            else:
                if attempt < MAX_RETRIES:
                    wait = RETRY_BACKOFF * attempt
                    print(f"    Error: {e}, retrying in {wait}s...")
                    time.sleep(wait)
                else:
                    print(f"    -> FAILED after {MAX_RETRIES} attempts: {e}")
                    return None
    return None


def download_parquet_union(disorder: DisorderDataset) -> Path:
    """Download with union_by_name=True for datasets with mixed schemas."""
    local_dir = LOCAL_PARQUET_DIR / disorder.config
    local_file = local_dir / "data.parquet"
    local_dir.mkdir(parents=True, exist_ok=True)
    hf_path = build_hf_path(disorder)

    con = get_connection()
    try:
        # Use read_parquet with union_by_name
        schema_df = con.execute(
            f"SELECT * FROM read_parquet('{hf_path}', union_by_name=True) LIMIT 1"
        ).fetchdf()
        col_map = normalize_columns(list(schema_df.columns))

        select_cols = []
        for canonical, source in col_map.items():
            if canonical in ("snp", "chr", "bp", "p", "beta", "or_val", "se"):
                select_cols.append(f'"{source}"')

        if not select_cols:
            raise ValueError(f"No usable columns in {disorder.name}")

        select_str = ", ".join(select_cols)

        con.execute(f"""
            CREATE TABLE _download AS
            SELECT {select_str}
            FROM read_parquet('{hf_path}', union_by_name=True)
        """)
        row_count = con.execute("SELECT COUNT(*) FROM _download").fetchone()[0]
        if row_count == 0:
            raise RuntimeError("Downloaded 0 rows")
        con.execute(f"""
            COPY _download TO '{local_file}' (FORMAT PARQUET, COMPRESSION ZSTD)
        """)
        con.execute("DROP TABLE _download")
    finally:
        con.close()

    if not _verify_parquet(local_file):
        local_file.unlink(missing_ok=True)
        raise RuntimeError(f"Downloaded file is corrupt (truncated parquet)")

    size_mb = local_file.stat().st_size / (1024 * 1024)
    print(f"    -> downloaded with union_by_name ({size_mb:.1f} MB)")
    return local_file


def local_pair_correlation(
    path_a: Path, path_b: Path,
    col_map_a: dict, col_map_b: dict,
) -> tuple[float, int]:
    """Compute correlation between two LOCAL parquet files via DuckDB."""
    con = duckdb.connect()

    snp_a = col_map_a.get("snp")
    snp_b = col_map_b.get("snp")
    if not snp_a or not snp_b:
        con.close()
        return 0.0, 0

    expr_a = _build_beta_expr(col_map_a, "a")
    expr_b = _build_beta_expr(col_map_b, "b")
    if not expr_a or not expr_b:
        con.close()
        return 0.0, 0

    query = f"""
        SELECT CORR({expr_a}, {expr_b}) AS rg,
               COUNT(*) AS n_snps
        FROM '{path_a}' a
        JOIN '{path_b}' b
          ON a."{snp_a}" = b."{snp_b}"
        WHERE {expr_a} IS NOT NULL
          AND {expr_b} IS NOT NULL
    """

    result = con.execute(query).fetchone()
    con.close()

    if result is None:
        return 0.0, 0

    corr_val = result[0]
    count = int(result[1])
    corr = float(corr_val) if corr_val is not None and np.isfinite(corr_val) else 0.0
    return corr, count


def main():
    print("=" * 60)
    print("PGC Explorer — Local Download Pipeline")
    print("=" * 60)

    # ------------------------------------------------------------------
    # Step 1a: Download full parquet files locally (for correlation)
    # ------------------------------------------------------------------
    print("\n[Step 1a] Downloading full parquet files locally...")
    LOCAL_PARQUET_DIR.mkdir(parents=True, exist_ok=True)

    local_paths: dict[str, Path] = {}
    col_maps: dict[str, dict] = {}

    # Check what's already downloaded
    for d in DISORDERS:
        local_file = LOCAL_PARQUET_DIR / d.config / "data.parquet"
        if local_file.exists() and local_file.stat().st_size > 1000:
            local_paths[d.name] = local_file
            print(f"  {d.name}: already cached ({local_file.stat().st_size / 1024 / 1024:.1f} MB)")

    remaining = [d for d in DISORDERS if d.name not in local_paths]
    if remaining:
        print(f"\n  Downloading {len(remaining)} remaining disorders in batches of {BATCH_SIZE}...")
        batches = [remaining[i:i + BATCH_SIZE] for i in range(0, len(remaining), BATCH_SIZE)]

        for batch_idx, batch in enumerate(batches):
            if batch_idx > 0:
                print(f"\n  Pausing {PAUSE_BETWEEN_BATCHES}s between batches...")
                time.sleep(PAUSE_BETWEEN_BATCHES)

            print(f"\n  [Batch {batch_idx + 1}/{len(batches)}]")
            for j, d in enumerate(batch):
                if j > 0:
                    time.sleep(PAUSE_BETWEEN_DATASETS)
                print(f"  Downloading {d.name} ({d.hf_id}/{d.config})...")
                path = download_with_retry(d)
                if path:
                    local_paths[d.name] = path

    # Discover columns for all downloaded files
    print(f"\n  Discovering columns for {len(local_paths)} local files...")
    for name, path in local_paths.items():
        try:
            con = duckdb.connect()
            schema_df = con.execute(f"SELECT * FROM '{path}' LIMIT 1").fetchdf()
            con.close()
            col_maps[name] = normalize_columns(list(schema_df.columns))
        except Exception as e:
            print(f"    {name}: column discovery failed — {e}")

    print(f"\n  Downloaded: {len(local_paths)}/{len(DISORDERS)} disorders")

    # ------------------------------------------------------------------
    # Step 1b: Load significant SNPs for Manhattan plots (p < 1e-5)
    # ------------------------------------------------------------------
    print(f"\n[Step 1b] Loading significant SNPs (p < {P_THRESHOLD_MANHATTAN}) for Manhattan plots...")
    disorders: dict[str, pl.DataFrame] = {}

    # Try loading from local files first, fall back to HF
    for d in DISORDERS:
        if d.name in local_paths and d.name in col_maps:
            try:
                cm = col_maps[d.name]
                if "p" not in cm:
                    continue
                p_col = cm["p"]
                select_cols = []
                for canonical, source in cm.items():
                    if canonical in ("snp", "chr", "bp", "p", "beta", "or_val", "se", "freq"):
                        select_cols.append(f'"{source}" AS {canonical}')
                select_str = ", ".join(select_cols)

                con = duckdb.connect()
                result = con.execute(f"""
                    SELECT {select_str}
                    FROM '{local_paths[d.name]}'
                    WHERE "{p_col}" < {P_THRESHOLD_MANHATTAN}
                    AND "{p_col}" IS NOT NULL
                """).fetchdf()
                con.close()

                df = pl.from_pandas(result)
                if "or_val" in df.columns and "beta" not in df.columns:
                    df = df.with_columns(pl.col("or_val").log().alias("beta"))
                if "chr" in df.columns:
                    df = df.with_columns(pl.col("chr").cast(pl.Int32, strict=False))
                if "bp" in df.columns:
                    df = df.with_columns(pl.col("bp").cast(pl.Int64, strict=False))

                disorders[d.name] = df
                print(f"  {d.name}: {len(df):,} significant SNPs (from local cache)")
            except Exception as e:
                print(f"  {d.name}: local load failed ({e}), skipping")
        else:
            print(f"  {d.name}: no local data available")

    if not disorders:
        print("ERROR: No disorders loaded. Exiting.")
        sys.exit(1)

    print(f"\n  Loaded {len(disorders)}/{len(DISORDERS)} disorders for Manhattan")

    # ------------------------------------------------------------------
    # Step 2: Compute correlation matrix on LOCAL files
    # ------------------------------------------------------------------
    print("\n[Step 2] Computing correlation matrix on local parquet files...")

    # Only use disorders that have both local parquet and valid col_maps
    valid_names = [d.name for d in DISORDERS
                   if d.name in local_paths and d.name in col_maps
                   and "snp" in col_maps[d.name]
                   and ("beta" in col_maps[d.name] or "or_val" in col_maps[d.name])]

    n = len(valid_names)
    matrix = np.eye(n)
    counts = np.zeros((n, n), dtype=int)
    total_pairs = n * (n - 1) // 2
    done = 0

    for i in range(n):
        for j in range(i + 1, n):
            done += 1
            name_a, name_b = valid_names[i], valid_names[j]
            print(f"  [{done}/{total_pairs}] {name_a} × {name_b} ...", end=" ", flush=True)

            corr, count = local_pair_correlation(
                local_paths[name_a], local_paths[name_b],
                col_maps[name_a], col_maps[name_b],
            )
            matrix[i, j] = corr
            matrix[j, i] = corr
            counts[i, j] = count
            counts[j, i] = count
            print(f"r={corr:+.4f}  n={count:,}")

    correlation = {
        "labels": valid_names,
        "values": matrix.tolist(),
        "overlap_counts": counts.tolist(),
    }

    # Print matrix
    print("\n  Correlation matrix:")
    for i, label in enumerate(correlation["labels"]):
        row = [f"{v:+.2f}" for v in correlation["values"][i]]
        print(f"    {label:20s} {' '.join(row)}")

    print("\n  Overlap counts (shared SNPs per pair):")
    for i, label in enumerate(correlation["labels"]):
        row = [f"{v:>12,}" for v in correlation["overlap_counts"][i]]
        print(f"    {label:20s} {' '.join(row)}")

    # ------------------------------------------------------------------
    # Step 3: Export JSON snapshots
    # ------------------------------------------------------------------
    print("\n[Step 3] Exporting JSON snapshots...")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    colors = {d.name: d.color for d in DISORDERS}

    export_correlation_matrix(correlation, DATA_DIR)
    print("  -> correlation_matrix.json")

    export_manhattan_data(disorders, DATA_DIR)
    print("  -> manhattan/*.json")

    sig_counts = {name: len(df) for name, df in disorders.items()}
    graph = export_network_graph(correlation, sig_counts, colors)
    (DATA_DIR / "network_graph.json").write_text(json.dumps(graph))
    print("  -> network_graph.json")

    export_metadata(disorders, colors, DATA_DIR)
    print("  -> metadata.json")

    print(f"\n  All snapshots written to {DATA_DIR}")
    print("\n" + "=" * 60)
    print("Pipeline complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
