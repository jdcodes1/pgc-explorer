"""Tests for column normalization logic (no HuggingFace download required)."""

from pgc_explorer.config import normalize_columns


def test_normalize_standard_columns():
    cols = ["SNP", "CHR", "BP", "A1", "A2", "OR", "SE", "P"]
    result = normalize_columns(cols)
    assert result["snp"] == "SNP"
    assert result["chr"] == "CHR"
    assert result["bp"] == "BP"
    assert result["p"] == "P"
    assert result["or_val"] == "OR"


def test_normalize_alternate_columns():
    cols = ["ID", "chromosome", "position", "effect_allele", "other_allele", "BETA", "StdErr", "Pval"]
    result = normalize_columns(cols)
    assert result["snp"] == "ID"
    assert result["chr"] == "chromosome"
    assert result["bp"] == "position"
    assert result["p"] == "Pval"
    assert result["beta"] == "BETA"


def test_normalize_missing_columns():
    cols = ["FOO", "BAR"]
    result = normalize_columns(cols)
    assert result == {}


def test_normalize_first_match_wins():
    """When multiple candidates match, the first in the candidate list wins."""
    cols = ["SNP", "ID"]  # both match "snp" canonical
    result = normalize_columns(cols)
    assert result["snp"] == "SNP"  # SNP is listed first in COLUMN_MAP
