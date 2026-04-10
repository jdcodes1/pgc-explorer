"""Run the PGC data pipeline in small batches to avoid HuggingFace rate limits."""

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

from pgc_explorer.config import DISORDERS, DATA_DIR
from pgc_explorer.loader import load_disorder
from pgc_explorer.analysis import (
    compute_correlation_matrix,
    compute_full_correlation_matrix,
)
from pgc_explorer.export import (
    export_manhattan_data,
    export_network_graph,
    export_correlation_matrix,
    export_metadata,
)

P_THRESHOLD_MANHATTAN = 1e-5
BATCH_SIZE = 3
PAUSE_BETWEEN_BATCHES = 120  # 2 minutes between batches
PAUSE_BETWEEN_DATASETS = 15  # 15 seconds between datasets in a batch
MAX_RETRIES = 3
RETRY_BACKOFF = 90  # seconds

CACHE_FILE = project_root / "data" / ".pipeline_cache.pkl"


def load_cached():
    """Load previously cached disorder data to resume from where we left off."""
    if CACHE_FILE.exists():
        with open(CACHE_FILE, "rb") as f:
            return pickle.load(f)
    return {}


def save_cached(disorders):
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_FILE, "wb") as f:
        pickle.dump(disorders, f)


def load_with_retry(d, p_threshold, retries=MAX_RETRIES):
    for attempt in range(retries):
        try:
            df = load_disorder(d, p_threshold=p_threshold)
            return df
        except Exception as e:
            err = str(e)
            if "429" in err or "503" in err:
                wait = RETRY_BACKOFF * (attempt + 1)
                print(f"    Rate limited, waiting {wait}s (attempt {attempt + 1}/{retries})...")
                time.sleep(wait)
            else:
                raise
    raise RuntimeError(f"Failed after {retries} retries")


def main():
    print("=" * 60)
    print("PGC Explorer — Batched Data Pipeline")
    print("=" * 60)

    # Load any cached results from previous runs
    disorders = load_cached()
    if disorders:
        print(f"\n  Resuming with {len(disorders)} cached disorders: {list(disorders.keys())}")

    # Figure out what still needs loading
    remaining = [d for d in DISORDERS if d.name not in disorders]
    if not remaining:
        print("\n  All disorders already cached!")
    else:
        print(f"\n  Need to load {len(remaining)} disorders in batches of {BATCH_SIZE}")

    # Process in batches
    batches = [remaining[i:i + BATCH_SIZE] for i in range(0, len(remaining), BATCH_SIZE)]

    for batch_idx, batch in enumerate(batches):
        if batch_idx > 0:
            print(f"\n  Pausing {PAUSE_BETWEEN_BATCHES}s between batches...")
            time.sleep(PAUSE_BETWEEN_BATCHES)

        print(f"\n[Batch {batch_idx + 1}/{len(batches)}]")

        for j, d in enumerate(batch):
            if j > 0:
                time.sleep(PAUSE_BETWEEN_DATASETS)

            print(f"  Loading {d.name} ({d.hf_id}, config={d.config})...")
            try:
                df = load_with_retry(d, P_THRESHOLD_MANHATTAN)
                disorders[d.name] = df
                print(f"    -> {len(df):,} significant SNPs")
                save_cached(disorders)
            except Exception as e:
                print(f"    -> FAILED: {e}")

    print(f"\n  Total loaded: {len(disorders)}/{len(DISORDERS)} disorders")
    if len(disorders) == 0:
        print("ERROR: No disorders loaded. Exiting.")
        sys.exit(1)

    # Compute correlation matrix
    print("\n[Step 2] Computing cross-disorder correlation matrix...")
    loaded_configs = [d for d in DISORDERS if d.name in disorders]

    correlation = None
    print("\n  Attempting DuckDB full-dataset correlation (no p-value filter)...")
    try:
        correlation = compute_full_correlation_matrix(loaded_configs)
        print("  DuckDB full-dataset correlation succeeded.")
    except Exception as e:
        print(f"  DuckDB full-dataset correlation failed: {e}")

    if correlation is None:
        print(f"\n  Falling back to in-memory correlation...")
        correlation = compute_correlation_matrix(disorders)

    # Print matrix
    print("\n  Correlation matrix:")
    for i, label in enumerate(correlation["labels"]):
        row = [f"{v:+.2f}" for v in correlation["values"][i]]
        print(f"    {label:20s} {' '.join(row)}")

    if "overlap_counts" in correlation:
        print("\n  Overlap counts (shared SNPs per pair):")
        for i, label in enumerate(correlation["labels"]):
            row = [f"{v:>8,}" for v in correlation["overlap_counts"][i]]
            print(f"    {label:20s} {' '.join(row)}")

    # Export
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

    # Clean up cache
    if CACHE_FILE.exists():
        CACHE_FILE.unlink()
        print("  -> cleaned up pipeline cache")

    print(f"\n  All snapshots written to {DATA_DIR}")
    print("\n" + "=" * 60)
    print("Pipeline complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
