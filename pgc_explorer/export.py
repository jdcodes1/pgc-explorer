"""Export processed data to JSON snapshots for the frontend."""

import json
import math
from pathlib import Path

import polars as pl


def export_manhattan_data(disorders: dict[str, pl.DataFrame], output_dir: Path) -> None:
    """Export per-disorder Manhattan plot data as JSON.

    Each disorder gets a file: output_dir/manhattan/<name>.json
    Contains SNPs with: snp, chr, bp, neglog10p, beta
    """
    manhattan_dir = output_dir / "manhattan"
    manhattan_dir.mkdir(parents=True, exist_ok=True)

    for name, df in disorders.items():
        records = []
        for row in df.iter_rows(named=True):
            p = row.get("p", 1.0)
            neglog10p = -math.log10(p) if p and p > 0 else 0
            records.append({
                "snp": row.get("snp", ""),
                "chr": row.get("chr"),
                "bp": row.get("bp"),
                "neglog10p": round(neglog10p, 2),
                "beta": round(row.get("beta", 0) or 0, 4),
            })

        # Sort by chromosome then position
        records.sort(key=lambda r: (r["chr"] or 0, r["bp"] or 0))

        data = {"disorder": name, "snps": records, "count": len(records)}
        safe_name = name.replace("/", "-")
        (manhattan_dir / f"{safe_name}.json").write_text(json.dumps(data))


def export_network_graph(
    correlation: dict,
    sig_counts: dict[str, int],
    colors: dict[str, str],
    min_edge_weight: float = 0.05,
) -> dict:
    """Build network graph JSON from correlation matrix.

    Args:
        correlation: Dict with "labels" and "values" (from compute_correlation_matrix).
        sig_counts: Dict mapping disorder name to number of significant loci.
        colors: Dict mapping disorder name to hex color.
        min_edge_weight: Minimum absolute correlation to include an edge.

    Returns:
        Dict with "nodes" and "links" for react-force-graph.
    """
    labels = correlation["labels"]
    values = correlation["values"]

    nodes = []
    for label in labels:
        nodes.append({
            "id": label,
            "sigLoci": sig_counts.get(label, 0),
            "color": colors.get(label, "#888888"),
        })

    links = []
    for i in range(len(labels)):
        for j in range(i + 1, len(labels)):
            weight = values[i][j]
            if abs(weight) >= min_edge_weight:
                links.append({
                    "source": labels[i],
                    "target": labels[j],
                    "weight": round(weight, 4),
                })

    return {"nodes": nodes, "links": links}


def export_correlation_matrix(correlation: dict, output_dir: Path) -> None:
    """Write correlation matrix to JSON."""
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "correlation_matrix.json").write_text(json.dumps(correlation))


def export_metadata(disorders: dict[str, pl.DataFrame], colors: dict[str, str], output_dir: Path) -> None:
    """Write metadata JSON with disorder info and counts."""
    output_dir.mkdir(parents=True, exist_ok=True)
    meta = {
        "disorders": [
            {"name": name, "snpCount": len(df), "color": colors.get(name, "#888")}
            for name, df in disorders.items()
        ],
        "totalSnps": sum(len(df) for df in disorders.values()),
    }
    (output_dir / "metadata.json").write_text(json.dumps(meta))
