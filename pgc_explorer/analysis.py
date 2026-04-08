"""Cross-disorder analysis: SNP overlap and genetic correlation approximation."""

import numpy as np
import polars as pl


def compute_snp_overlap(df_a: pl.DataFrame, df_b: pl.DataFrame) -> pl.DataFrame:
    """Find SNPs present in both disorder DataFrames.

    Returns DataFrame with columns from both, suffixed _b for the second.
    """
    if "snp" not in df_a.columns or "snp" not in df_b.columns:
        return pl.DataFrame()

    return df_a.join(df_b, on="snp", how="inner", suffix="_b")


def _beta_correlation(df_a: pl.DataFrame, df_b: pl.DataFrame) -> float:
    """Compute Pearson correlation of effect sizes (beta) for shared SNPs.

    This is a simplified proxy for genetic correlation (rg).
    True rg requires LD score regression, but beta correlation on
    genome-wide significant SNPs gives directional concordance.
    """
    overlap = compute_snp_overlap(df_a, df_b)

    if len(overlap) < 3:
        return 0.0

    beta_a = overlap["beta"].to_numpy()
    beta_b_col = "beta_b" if "beta_b" in overlap.columns else "beta"
    beta_b = overlap[beta_b_col].to_numpy()

    # Remove NaN pairs
    mask = np.isfinite(beta_a) & np.isfinite(beta_b)
    if mask.sum() < 3:
        return 0.0

    corr = np.corrcoef(beta_a[mask], beta_b[mask])[0, 1]
    return float(corr) if np.isfinite(corr) else 0.0


def compute_correlation_matrix(disorders: dict[str, pl.DataFrame]) -> dict:
    """Compute pairwise beta correlation matrix across disorders.

    Args:
        disorders: Dict mapping disorder name to its filtered DataFrame.

    Returns:
        Dict with "labels" (list of names) and "values" (2D list of correlations).
    """
    labels = list(disorders.keys())
    n = len(labels)
    matrix = np.eye(n)

    for i in range(n):
        for j in range(i + 1, n):
            corr = _beta_correlation(disorders[labels[i]], disorders[labels[j]])
            matrix[i, j] = corr
            matrix[j, i] = corr

    return {
        "labels": labels,
        "values": matrix.tolist(),
    }
