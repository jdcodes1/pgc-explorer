"""Load and normalize PGC datasets from HuggingFace."""

import signal
import polars as pl
from datasets import load_dataset

from pgc_explorer.config import DisorderDataset, normalize_columns


class _Timeout(Exception):
    pass


def _timeout_handler(signum, frame):
    raise _Timeout()


def load_disorder(disorder: DisorderDataset, p_threshold: float = 1e-5, download_timeout: int = 600) -> pl.DataFrame:
    """Load a disorder dataset from HuggingFace, normalize columns, filter to top SNPs.

    Tries full download first (fast filtering with Polars). Falls back to
    streaming if the download hangs or fails.

    Args:
        disorder: Dataset config for this disorder.
        p_threshold: Only keep SNPs with p-value below this threshold.
        download_timeout: Max seconds to wait for full download before falling back to streaming.

    Returns:
        Polars DataFrame with canonical column names: snp, chr, bp, p, beta/or_val, se, freq.
    """
    try:
        # Try full download with timeout
        old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
        signal.alarm(download_timeout)
        try:
            ds = load_dataset(disorder.hf_id, disorder.config, split="train")
            df = pl.from_arrow(ds.data.table)
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)
    except (_Timeout, Exception) as e:
        if isinstance(e, _Timeout):
            print(f"    Download timed out after {download_timeout}s, falling back to streaming...")
        else:
            print(f"    Download failed ({e}), falling back to streaming...")
        return _load_streaming(disorder, p_threshold)

    return _process_dataframe(df, disorder, p_threshold)


def _load_streaming(disorder: DisorderDataset, p_threshold: float) -> pl.DataFrame:
    """Streaming fallback for large datasets."""
    ds = load_dataset(disorder.hf_id, disorder.config, split="train", streaming=True)

    first_iter = iter(ds)
    first_row = next(first_iter)
    col_map = normalize_columns(list(first_row.keys()))

    if "p" not in col_map:
        raise ValueError(f"No p-value column found in {disorder.name}. Columns: {list(first_row.keys())}")

    p_col = col_map["p"]
    rows = []
    count = 0

    # Process all rows including first
    for row in [first_row, *[]]:
        try:
            p_val = float(row[p_col]) if row[p_col] is not None else 1.0
        except (ValueError, TypeError):
            continue
        if p_val < p_threshold:
            rows.append(row)

    for row in first_iter:
        count += 1
        if count % 1_000_000 == 0:
            print(f"      Streamed {count:,} rows, found {len(rows):,} significant...")
        try:
            p_val = float(row[p_col]) if row[p_col] is not None else 1.0
        except (ValueError, TypeError):
            continue
        if p_val < p_threshold:
            rows.append(row)

    if not rows:
        return pl.DataFrame({"snp": [], "chr": [], "bp": [], "p": [], "beta": []})

    df = pl.DataFrame(rows)
    return _process_dataframe(df, disorder, p_threshold, already_filtered=True)


def _process_dataframe(df: pl.DataFrame, disorder: DisorderDataset, p_threshold: float, already_filtered: bool = False) -> pl.DataFrame:
    """Normalize columns, filter, and clean a loaded DataFrame."""

    col_map = normalize_columns(df.columns)

    if "p" not in col_map:
        raise ValueError(f"No p-value column found in {disorder.name}. Columns: {df.columns}")

    # Rename found columns to canonical names
    rename_map = {source: canonical for canonical, source in col_map.items()}
    df = df.rename(rename_map)

    # Cast p-value to Float64 (some datasets have string or other types)
    df = df.with_columns(pl.col("p").cast(pl.Float64, strict=False))
    df = df.filter(pl.col("p").is_not_null())

    # Filter to significant SNPs (skip if already filtered during streaming)
    if not already_filtered:
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
