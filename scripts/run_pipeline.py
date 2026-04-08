"""Run the full PGC data pipeline — standalone script version of the notebook."""

import os
import sys
import json
import time
from pathlib import Path

# Add project root to path
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

# P-value thresholds
P_THRESHOLD_MANHATTAN = 1e-5   # strict — for Manhattan plots (significant hits)
P_THRESHOLD_FALLBACK = 0.05   # relaxed — fallback for correlation if DuckDB fails


def main():
    print("=" * 60)
    print("PGC Explorer — Data Pipeline")
    print("=" * 60)

    # ------------------------------------------------------------------
    # Step 1: Load significant SNPs for Manhattan plots (p < 1e-5)
    # ------------------------------------------------------------------
    print("\n[Step 1] Loading disorders from HuggingFace (p < 1e-5 for Manhattan)...\n")
    disorders = {}
    failed = []

    for i, d in enumerate(DISORDERS):
        if i > 0:
            time.sleep(5)  # Small delay between datasets to avoid rate limits
        print(f"  Loading {d.name} ({d.hf_id}, config={d.config})...")
        try:
            df = load_disorder(d, p_threshold=P_THRESHOLD_MANHATTAN)
            disorders[d.name] = df
            print(f"    -> {len(df):,} significant SNPs")
        except Exception as e:
            failed.append((d.name, str(e)))
            print(f"    -> FAILED: {e}")

    print(f"\n  Loaded {len(disorders)}/{len(DISORDERS)} disorders")
    if failed:
        print(f"  Failed: {[f[0] for f in failed]}")

    if not disorders:
        print("ERROR: No disorders loaded. Exiting.")
        sys.exit(1)

    # ------------------------------------------------------------------
    # Step 2: Compute correlation matrix
    # ------------------------------------------------------------------
    # Option 1: DuckDB on full datasets (no p-value filter).
    # Falls back to Option 2: relaxed threshold (p < 0.05) if DuckDB fails.
    # ------------------------------------------------------------------
    print("\n[Step 2] Computing cross-disorder correlation matrix...")

    loaded_configs = [d for d in DISORDERS if d.name in disorders]

    correlation = None

    # --- Option 1: full-dataset DuckDB correlation ---
    print("\n  Attempting DuckDB full-dataset correlation (no p-value filter)...")
    try:
        correlation = compute_full_correlation_matrix(loaded_configs)
        print("  DuckDB full-dataset correlation succeeded.")
    except Exception as e:
        print(f"  DuckDB full-dataset correlation failed: {e}")

    # --- Option 2 fallback: relaxed threshold ---
    if correlation is None:
        print(f"\n  Falling back to relaxed threshold (p < {P_THRESHOLD_FALLBACK})...")
        disorders_relaxed = {}
        for i, d in enumerate(loaded_configs):
            if i > 0:
                time.sleep(5)
            print(f"    Reloading {d.name} with p < {P_THRESHOLD_FALLBACK}...")
            try:
                df = load_disorder(d, p_threshold=P_THRESHOLD_FALLBACK)
                disorders_relaxed[d.name] = df
                print(f"      -> {len(df):,} SNPs")
            except Exception as e:
                print(f"      -> FAILED: {e}")

        if disorders_relaxed:
            correlation = compute_correlation_matrix(disorders_relaxed)
            print("  Relaxed-threshold correlation succeeded.")
        else:
            print("  Relaxed-threshold loading failed — using strict-threshold data.")
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
