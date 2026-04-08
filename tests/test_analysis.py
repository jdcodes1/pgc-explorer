"""Tests for cross-disorder analysis functions."""

import polars as pl

from pgc_explorer.analysis import compute_snp_overlap, compute_correlation_matrix


def _make_disorder_df(snps: list[str], chroms: list[int], bps: list[int], pvals: list[float], betas: list[float]) -> pl.DataFrame:
    return pl.DataFrame({
        "snp": snps,
        "chr": chroms,
        "bp": bps,
        "p": pvals,
        "beta": betas,
    })


def test_compute_snp_overlap_shared():
    df_a = _make_disorder_df(["rs1", "rs2", "rs3"], [1, 1, 2], [100, 200, 300], [1e-8, 1e-7, 1e-6], [0.1, 0.2, 0.3])
    df_b = _make_disorder_df(["rs2", "rs3", "rs4"], [1, 2, 3], [200, 300, 400], [1e-9, 1e-5, 1e-8], [0.15, 0.25, 0.35])
    overlap = compute_snp_overlap(df_a, df_b)
    assert set(overlap["snp"].to_list()) == {"rs2", "rs3"}


def test_compute_snp_overlap_none():
    df_a = _make_disorder_df(["rs1"], [1], [100], [1e-8], [0.1])
    df_b = _make_disorder_df(["rs9"], [2], [200], [1e-8], [0.2])
    overlap = compute_snp_overlap(df_a, df_b)
    assert len(overlap) == 0


def test_correlation_matrix():
    disorders = {
        "A": _make_disorder_df(["rs1", "rs2", "rs3", "rs6"], [1, 1, 2, 3], [100, 200, 300, 600], [1e-8, 1e-7, 1e-6, 1e-9], [0.1, 0.2, 0.3, 0.4]),
        "B": _make_disorder_df(["rs2", "rs3", "rs4", "rs6"], [1, 2, 3, 3], [200, 300, 400, 600], [1e-9, 1e-5, 1e-8, 1e-7], [0.15, 0.25, 0.35, 0.45]),
        "C": _make_disorder_df(["rs5"], [4], [500], [1e-8], [0.5]),
    }
    matrix = compute_correlation_matrix(disorders)
    assert matrix["labels"] == ["A", "B", "C"]
    # A-B should have positive correlation (shared rs2, rs3 with same-sign betas)
    assert matrix["values"][0][1] > 0  # A-B
    assert matrix["values"][1][0] == matrix["values"][0][1]  # symmetric
    # Diagonal should be 1.0
    assert matrix["values"][0][0] == 1.0
