"""Tests for cross-disorder analysis functions."""

import polars as pl

from pgc_explorer.analysis import (
    compute_snp_overlap,
    compute_correlation_matrix,
    _beta_correlation,
    _build_beta_expr,
)


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


def test_beta_correlation_returns_tuple():
    """_beta_correlation now returns (correlation, overlap_count)."""
    df_a = _make_disorder_df(
        ["rs1", "rs2", "rs3", "rs4"],
        [1, 1, 2, 2], [100, 200, 300, 400],
        [1e-8] * 4, [0.1, 0.2, 0.3, 0.4],
    )
    df_b = _make_disorder_df(
        ["rs1", "rs2", "rs3", "rs4"],
        [1, 1, 2, 2], [100, 200, 300, 400],
        [1e-8] * 4, [0.05, 0.15, 0.25, 0.35],
    )
    corr, count = _beta_correlation(df_a, df_b)
    assert count == 4
    assert corr > 0.99  # nearly perfect — same direction, linear relationship


def test_beta_correlation_insufficient_overlap():
    """With fewer than 3 shared SNPs, correlation should be 0.0."""
    df_a = _make_disorder_df(["rs1", "rs2"], [1, 1], [100, 200], [1e-8, 1e-8], [0.1, 0.2])
    df_b = _make_disorder_df(["rs1", "rs2"], [1, 1], [100, 200], [1e-8, 1e-8], [0.1, 0.2])
    corr, count = _beta_correlation(df_a, df_b)
    assert corr == 0.0
    assert count == 2


def test_correlation_matrix():
    disorders = {
        "A": _make_disorder_df(["rs1", "rs2", "rs3", "rs6"], [1, 1, 2, 3], [100, 200, 300, 600], [1e-8, 1e-7, 1e-6, 1e-9], [0.1, 0.2, 0.3, 0.4]),
        "B": _make_disorder_df(["rs2", "rs3", "rs4", "rs6"], [1, 2, 3, 3], [200, 300, 400, 600], [1e-9, 1e-5, 1e-8, 1e-7], [0.15, 0.25, 0.35, 0.45]),
        "C": _make_disorder_df(["rs5"], [4], [500], [1e-8], [0.5]),
    }
    matrix = compute_correlation_matrix(disorders)
    assert matrix["labels"] == ["A", "B", "C"]
    # A-B should have positive correlation (shared rs2, rs3, rs6 with same-sign betas)
    assert matrix["values"][0][1] > 0  # A-B
    assert matrix["values"][1][0] == matrix["values"][0][1]  # symmetric
    # Diagonal should be 1.0
    assert matrix["values"][0][0] == 1.0


def test_correlation_matrix_has_overlap_counts():
    """compute_correlation_matrix should include overlap_counts."""
    disorders = {
        "A": _make_disorder_df(["rs1", "rs2", "rs3", "rs4"], [1, 1, 2, 2], [100, 200, 300, 400], [1e-8] * 4, [0.1, 0.2, 0.3, 0.4]),
        "B": _make_disorder_df(["rs2", "rs3", "rs4", "rs5"], [1, 2, 2, 3], [200, 300, 400, 500], [1e-8] * 4, [0.15, 0.25, 0.35, 0.45]),
    }
    matrix = compute_correlation_matrix(disorders)
    assert "overlap_counts" in matrix
    # A-B share rs2, rs3, rs4 = 3 SNPs
    assert matrix["overlap_counts"][0][1] == 3
    assert matrix["overlap_counts"][1][0] == 3  # symmetric


def test_build_beta_expr_with_beta():
    col_map = {"snp": "SNP", "beta": "BETA"}
    assert _build_beta_expr(col_map, "a") == 'a."BETA"'


def test_build_beta_expr_with_or():
    col_map = {"snp": "SNP", "or_val": "OR"}
    assert _build_beta_expr(col_map, "a") == 'LN(a."OR")'


def test_build_beta_expr_missing():
    col_map = {"snp": "SNP"}
    assert _build_beta_expr(col_map, "a") is None
