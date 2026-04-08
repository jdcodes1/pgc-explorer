"""Load and normalize PGC datasets from HuggingFace."""

import polars as pl
from datasets import load_dataset

from pgc_explorer.config import DisorderDataset, normalize_columns


def load_disorder(disorder: DisorderDataset, p_threshold: float = 1e-5) -> pl.DataFrame:
    """Load a disorder dataset from HuggingFace, normalize columns, filter to top SNPs.

    Args:
        disorder: Dataset config for this disorder.
        p_threshold: Only keep SNPs with p-value below this threshold.

    Returns:
        Polars DataFrame with canonical column names: snp, chr, bp, p, beta/or_val, se, freq.
    """
    ds = load_dataset(disorder.hf_id, disorder.config, split="train")
    df = pl.from_arrow(ds.data.table)

    col_map = normalize_columns(df.columns)

    if "p" not in col_map:
        raise ValueError(f"No p-value column found in {disorder.name}. Columns: {df.columns}")

    # Rename found columns to canonical names
    rename_map = {source: canonical for canonical, source in col_map.items()}
    df = df.rename(rename_map)

    # Filter to significant SNPs
    df = df.filter(pl.col("p") < p_threshold)

    # Keep only canonical columns that exist
    keep_cols = [c for c in ["snp", "chr", "bp", "p", "beta", "or_val", "se", "freq"] if c in df.columns]
    df = df.select(keep_cols)

    # Convert OR to beta if needed
    if "or_val" in df.columns and "beta" not in df.columns:
        df = df.with_columns(pl.col("or_val").log().alias("beta"))

    # Cast chr to Int32, bp to Int64
    if "chr" in df.columns:
        df = df.with_columns(pl.col("chr").cast(pl.Int32, strict=False))
    if "bp" in df.columns:
        df = df.with_columns(pl.col("bp").cast(pl.Int64, strict=False))

    return df
