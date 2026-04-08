"""Cross-disorder analysis: SNP overlap and genetic correlation approximation."""

import time

import numpy as np
import polars as pl

from pgc_explorer.config import DisorderDataset, normalize_columns
from pgc_explorer.loader import get_connection, build_hf_path


# ---------------------------------------------------------------------------
# Existing helpers (used by the relaxed-threshold fallback)
# ---------------------------------------------------------------------------

def compute_snp_overlap(df_a: pl.DataFrame, df_b: pl.DataFrame) -> pl.DataFrame:
    """Find SNPs present in both disorder DataFrames.

    Returns DataFrame with columns from both, suffixed _b for the second.
    """
    if "snp" not in df_a.columns or "snp" not in df_b.columns:
        return pl.DataFrame()

    return df_a.join(df_b, on="snp", how="inner", suffix="_b")


def _beta_correlation(df_a: pl.DataFrame, df_b: pl.DataFrame) -> tuple[float, int]:
    """Compute Pearson correlation of effect sizes (beta) for shared SNPs.

    Returns:
        Tuple of (correlation, overlap_count).
    """
    overlap = compute_snp_overlap(df_a, df_b)

    if len(overlap) < 3:
        return 0.0, len(overlap)

    beta_a = overlap["beta"].to_numpy()
    beta_b_col = "beta_b" if "beta_b" in overlap.columns else "beta"
    beta_b = overlap[beta_b_col].to_numpy()

    # Remove NaN pairs
    mask = np.isfinite(beta_a) & np.isfinite(beta_b)
    n_valid = int(mask.sum())
    if n_valid < 3:
        return 0.0, n_valid

    corr = np.corrcoef(beta_a[mask], beta_b[mask])[0, 1]
    return (float(corr) if np.isfinite(corr) else 0.0), n_valid


def compute_correlation_matrix(disorders: dict[str, pl.DataFrame]) -> dict:
    """Compute pairwise beta correlation matrix across disorders.

    This is the fallback method that operates on pre-loaded DataFrames
    (typically filtered to a p-value threshold). Use
    compute_full_correlation_matrix() for the preferred DuckDB approach.

    Returns:
        Dict with "labels", "values" (2D list), and "overlap_counts" (2D list).
    """
    labels = list(disorders.keys())
    n = len(labels)
    matrix = np.eye(n)
    counts = np.zeros((n, n), dtype=int)

    for i in range(n):
        for j in range(i + 1, n):
            corr, count = _beta_correlation(disorders[labels[i]], disorders[labels[j]])
            matrix[i, j] = corr
            matrix[j, i] = corr
            counts[i, j] = count
            counts[j, i] = count

    return {
        "labels": labels,
        "values": matrix.tolist(),
        "overlap_counts": counts.tolist(),
    }


# ---------------------------------------------------------------------------
# Option 1 — DuckDB full-dataset correlation (no p-value filter)
# ---------------------------------------------------------------------------

def _discover_columns(con, hf_path: str) -> dict[str, str]:
    """Discover and normalize column names for a remote parquet dataset."""
    schema_df = con.execute(f"SELECT * FROM '{hf_path}' LIMIT 1").fetchdf()
    return normalize_columns(list(schema_df.columns))


def _build_beta_expr(col_map: dict[str, str], alias: str) -> str | None:
    """Build a SQL expression for the beta column, converting OR if needed."""
    if "beta" in col_map:
        return f'{alias}."{col_map["beta"]}"'
    if "or_val" in col_map:
        return f'LN({alias}."{col_map["or_val"]}")'
    return None


def _duckdb_pair_correlation(
    con,
    path_a: str,
    path_b: str,
    col_map_a: dict[str, str],
    col_map_b: dict[str, str],
) -> tuple[float, int]:
    """Compute Pearson correlation between two remote datasets via DuckDB.

    Joins on SNP ID and computes CORR() on beta values across ALL shared
    SNPs — no p-value filter. DuckDB streams through the Parquet files
    so the full datasets never need to fit in memory.

    Returns:
        Tuple of (correlation, overlap_count).
    """
    snp_a = col_map_a.get("snp")
    snp_b = col_map_b.get("snp")
    if not snp_a or not snp_b:
        return 0.0, 0

    expr_a = _build_beta_expr(col_map_a, "a")
    expr_b = _build_beta_expr(col_map_b, "b")
    if not expr_a or not expr_b:
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
    if result is None:
        return 0.0, 0

    corr_val = result[0]
    count = int(result[1])
    corr = float(corr_val) if corr_val is not None and np.isfinite(corr_val) else 0.0
    return corr, count


def compute_full_correlation_matrix(
    disorder_configs: list[DisorderDataset],
    max_retries: int = 3,
) -> dict:
    """Compute pairwise correlation matrix using DuckDB on full remote datasets.

    Queries HuggingFace Parquet files directly, joining on SNP ID and
    computing Pearson correlation on ALL shared SNPs — no p-value filter.
    This avoids the selection bias of threshold-based approaches.

    Args:
        disorder_configs: List of DisorderDataset configs to include.
        max_retries: Number of retries per pair on transient failures.

    Returns:
        Dict with "labels", "values" (2D list), and "overlap_counts" (2D list).
    """
    con = get_connection()

    # Discover column names for each disorder
    col_maps: dict[str, dict[str, str]] = {}
    valid: list[DisorderDataset] = []
    paths: dict[str, str] = {}

    for d in disorder_configs:
        hf_path = build_hf_path(d)
        try:
            col_map = _discover_columns(con, hf_path)
            if "snp" not in col_map:
                print(f"    {d.name}: no SNP column found, skipping")
                continue
            if "beta" not in col_map and "or_val" not in col_map:
                print(f"    {d.name}: no beta/OR column found, skipping")
                continue
            col_maps[d.name] = col_map
            paths[d.name] = hf_path
            valid.append(d)
            print(f"    {d.name}: ready")
        except Exception as e:
            print(f"    {d.name}: column discovery failed — {e}")

    labels = [d.name for d in valid]
    n = len(labels)
    matrix = np.eye(n)
    counts = np.zeros((n, n), dtype=int)

    total_pairs = n * (n - 1) // 2
    done = 0

    for i in range(n):
        for j in range(i + 1, n):
            done += 1
            name_a, name_b = labels[i], labels[j]
            print(f"    [{done}/{total_pairs}] {name_a} × {name_b} ...", end=" ", flush=True)

            corr, count = 0.0, 0
            for attempt in range(1, max_retries + 1):
                try:
                    corr, count = _duckdb_pair_correlation(
                        con,
                        paths[name_a], paths[name_b],
                        col_maps[name_a], col_maps[name_b],
                    )
                    break
                except Exception as e:
                    if attempt < max_retries:
                        wait = 30 * attempt
                        print(f"retry in {wait}s ({e})", end=" ", flush=True)
                        time.sleep(wait)
                    else:
                        print(f"FAILED after {max_retries} attempts: {e}")

            matrix[i, j] = corr
            matrix[j, i] = corr
            counts[i, j] = count
            counts[j, i] = count
            print(f"r={corr:+.4f}  n={count:,}")

            # Brief pause between pairs to be kind to HuggingFace
            time.sleep(2)

    con.close()

    return {
        "labels": labels,
        "values": matrix.tolist(),
        "overlap_counts": counts.tolist(),
    }
