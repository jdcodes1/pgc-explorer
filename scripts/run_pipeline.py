"""Run the full PGC data pipeline — standalone script version of the notebook."""

import os
import sys
import json
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
from pgc_explorer.analysis import compute_correlation_matrix
from pgc_explorer.export import (
    export_manhattan_data,
    export_network_graph,
    export_correlation_matrix,
    export_metadata,
)


def main():
    print("=" * 60)
    print("PGC Explorer — Data Pipeline")
    print("=" * 60)

    # Step 1: Load and filter all disorders
    print("\n[Step 1] Loading disorders from HuggingFace...\n")
    disorders = {}
    failed = []

    for d in DISORDERS:
        print(f"  Loading {d.name} ({d.hf_id}, config={d.config})...")
        try:
            df = load_disorder(d, p_threshold=1e-5)
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

    # Step 2: Compute correlation matrix
    print("\n[Step 2] Computing cross-disorder correlation matrix...")
    correlation = compute_correlation_matrix(disorders)
    print("  Correlation matrix:")
    for i, label in enumerate(correlation["labels"]):
        row = [f"{v:+.2f}" for v in correlation["values"][i]]
        print(f"    {label:20s} {' '.join(row)}")

    # Step 3: Export JSON snapshots
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
