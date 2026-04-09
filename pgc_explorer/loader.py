"""Load and normalize PGC datasets from HuggingFace using DuckDB."""

import os
import time
import duckdb
import polars as pl

from pgc_explorer.config import DisorderDataset, normalize_columns

def get_connection() -> duckdb.DuckDBPyConnection:
    """Create a fresh DuckDB connection with HuggingFace auth."""
    con = duckdb.connect()
    con.execute("INSTALL httpfs; LOAD httpfs;")
    token = os.environ.get("HF_TOKEN", "")
    if token:
        con.execute(f"CREATE SECRET (TYPE HUGGINGFACE, TOKEN '{token}')")
    return con


def build_hf_path(disorder: DisorderDataset) -> str:
    """Build the HuggingFace parquet URL for a disorder dataset."""
    return f"hf://datasets/{disorder.hf_id}/data/{disorder.config}/*.parquet"


def load_disorder(disorder: DisorderDataset, p_threshold: float = 1e-5, max_retries: int = 3) -> pl.DataFrame:
    """Load significant SNPs from a HuggingFace dataset using DuckDB.

    Uses predicate pushdown to only download rows matching the p-value
    threshold, avoiding full dataset downloads.

    Args:
        disorder: Dataset config for this disorder.
        p_threshold: Only keep SNPs with p-value below this threshold.

    Returns:
        Polars DataFrame with canonical column names.
    """
    con = get_connection()

    # Build the HF parquet URL
    hf_path = build_hf_path(disorder)

    for attempt in range(1, max_retries + 1):
        try:
            # First, discover column names
            schema_df = con.execute(f"SELECT * FROM '{hf_path}' LIMIT 1").fetchdf()
            columns = list(schema_df.columns)
            col_map = normalize_columns(columns)

            if "p" not in col_map:
                raise ValueError(f"No p-value column found in {disorder.name}. Columns: {columns}")

            p_col = col_map["p"]

            # Build SELECT with only the columns we need
            select_cols = []
            for canonical, source in col_map.items():
                if canonical in ("snp", "chr", "bp", "p", "beta", "or_val", "se", "freq"):
                    select_cols.append(f'"{source}" AS {canonical}')

            if not select_cols:
                raise ValueError(f"No usable columns found in {disorder.name}")

            select_str = ", ".join(select_cols)

            # Query with predicate pushdown
            query = f"""
                SELECT {select_str}
                FROM '{hf_path}'
                WHERE "{p_col}" < {p_threshold}
                AND "{p_col}" IS NOT NULL
            """

            result = con.execute(query).fetchdf()
            df = pl.from_pandas(result)
            break
        except ValueError:
            raise
        except Exception as e:
            if "429" in str(e) and attempt < max_retries:
                wait = 60 * attempt
                print(f"    Rate limited, waiting {wait}s (attempt {attempt}/{max_retries})...")
                time.sleep(wait)
            else:
                raise

    # Convert OR to beta if needed
    if "or_val" in df.columns and "beta" not in df.columns:
        df = df.with_columns(pl.col("or_val").log().alias("beta"))

    # Cast chr to Int32, bp to Int64
    if "chr" in df.columns:
        df = df.with_columns(pl.col("chr").cast(pl.Int32, strict=False))
    if "bp" in df.columns:
        df = df.with_columns(pl.col("bp").cast(pl.Int64, strict=False))

    con.close()
    return df
