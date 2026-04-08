"""Tests for snapshot export functions."""

import json
from pathlib import Path

import polars as pl

from pgc_explorer.export import export_manhattan_data, export_network_graph


def _make_df(snps, chroms, bps, pvals, betas):
    return pl.DataFrame({"snp": snps, "chr": chroms, "bp": bps, "p": pvals, "beta": betas})


def test_export_manhattan_data(tmp_path):
    df = _make_df(
        ["rs1", "rs2", "rs3"],
        [1, 1, 2],
        [1000, 2000, 50000],
        [1e-8, 1e-6, 1e-10],
        [0.1, 0.2, 0.3],
    )
    export_manhattan_data({"SCZ": df}, tmp_path)

    result = json.loads((tmp_path / "manhattan" / "SCZ.json").read_text())
    assert len(result["snps"]) == 3
    assert result["snps"][0]["snp"] == "rs1"
    assert result["snps"][0]["chr"] == 1
    assert result["snps"][0]["neglog10p"] > 7  # -log10(1e-8) = 8


def test_export_network_graph():
    correlation = {
        "labels": ["A", "B", "C"],
        "values": [[1.0, 0.5, 0.1], [0.5, 1.0, 0.8], [0.1, 0.8, 1.0]],
    }
    sig_counts = {"A": 100, "B": 200, "C": 50}
    colors = {"A": "#ff0000", "B": "#00ff00", "C": "#0000ff"}

    graph = export_network_graph(correlation, sig_counts, colors)

    assert len(graph["nodes"]) == 3
    assert len(graph["links"]) == 3  # 3 pairs: A-B, A-C, B-C
    # Nodes should have size based on sig_counts
    node_b = next(n for n in graph["nodes"] if n["id"] == "B")
    assert node_b["sigLoci"] == 200
