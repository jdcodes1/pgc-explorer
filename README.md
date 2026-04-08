# PGC Explorer

Interactive cross-disorder psychiatric genetics visualization.
Built on **1 billion+ rows** of GWAS summary statistics from the
[Psychiatric Genomics Consortium](https://pgc.unc.edu/) via
[HuggingFace](https://huggingface.co/OpenMed).

**Live demo:** [web-iota-coral-12.vercel.app](https://web-iota-coral-12.vercel.app)

## Visualizations

- **Genetic Correlations** — 9x9 heatmap showing which disorders share genetic risk factors
- **Manhattan Overlay** — Multi-disorder Manhattan plots, overlay up to 3 disorders to spot shared genomic peaks
- **Disorder Network** — Force-directed graph where disorders cluster by genetic similarity

## How the data pipeline works

### The problem

The Psychiatric Genomics Consortium (PGC) publishes GWAS summary statistics across 52 publications and 12 disorder groups. These were historically scattered across Figshare as gzipped TSVs with inconsistent column names, delimiters, and formats. Loading a single dataset meant `wget`, `gunzip`, and 20 minutes debugging separators.

### The solution: HuggingFace + DuckDB

The [OpenMed project](https://huggingface.co/OpenMed) converted all 52 PGC publications into clean Apache Parquet on HuggingFace. We query these directly using **DuckDB with predicate pushdown** — instead of downloading entire datasets (50GB+), DuckDB sends SQL queries to the remote parquet files and only downloads the rows we need.

```python
# What DuckDB does under the hood:
SELECT SNP, CHR, BP, P, "OR" AS or_val, SE
FROM 'hf://datasets/OpenMed/pgc-schizophrenia/data/scz2022/*.parquet'
WHERE P < 1e-5 AND P IS NOT NULL
```

This turns a 37-million-row dataset into ~112K significant SNPs in about 60 seconds, downloading only a few MB instead of the full 8GB.

### Pipeline steps

**1. Query HuggingFace parquet files** (`pgc_explorer/loader.py`)

For each of the 12 disorder groups, DuckDB queries the HuggingFace-hosted parquet files with a p-value filter (`p < 1e-5`). Only genome-wide suggestive/significant SNPs are returned. Each dataset uses the latest available PGC publication config (e.g., `adhd2022`, `scz2022`, `mdd2018`).

Rate limiting is handled with exponential backoff (60s, 120s, 180s retries). A HuggingFace token in `.env` increases rate limits.

**2. Normalize column names** (`pgc_explorer/config.py`)

Different publications use different column names for the same data. For example, a SNP identifier might be called `SNP`, `ID`, `SNPID`, `rsid`, or `variant_id` depending on the study. The `COLUMN_MAP` dictionary maps ~50 known column name variants to canonical names (`snp`, `chr`, `bp`, `p`, `beta`, etc.).

Odds ratios (`OR`) are converted to log-odds (`beta`) for consistency. Chromosome and position columns are cast to integers.

**3. Compute cross-disorder correlations** (`pgc_explorer/analysis.py`)

For every pair of disorders, we find SNPs that appear in both datasets (by rsID), then compute the Pearson correlation of their effect sizes (beta values). This is a simplified proxy for genetic correlation — true rg requires LD score regression, but beta correlation on significant SNPs gives a useful measure of directional concordance.

The output is a 9x9 correlation matrix (9 disorders loaded successfully out of 12).

**4. Export JSON snapshots** (`pgc_explorer/export.py`)

The processed data is exported as static JSON files:

- `correlation_matrix.json` — 9x9 matrix of pairwise correlations
- `manhattan/<Disorder>.json` — per-disorder SNP lists with `-log10(p)` for Manhattan plots
- `network_graph.json` — nodes (disorders) and edges (correlations) for the force graph
- `metadata.json` — disorder names, colors, SNP counts

**5. Serve via Next.js** (`web/`)

The JSON snapshots are copied to `web/public/data/` and served as static files. The Next.js frontend renders them with D3.js (Manhattan plots), Plotly (heatmap), and react-force-graph (network). No backend needed — everything is pre-computed.

### What we loaded

| Disorder | Publication | Significant SNPs |
|----------|------------|-----------------|
| ADHD | adhd2022 | 7,033 |
| Anxiety | anx2026 | 12,815 |
| Autism | asd2019 | 4,027 |
| Bipolar | bip2019 | 5,346 |
| Depression | mdd2018 | 7,014 |
| Schizophrenia | scz2022 | 112,770 |
| PTSD | ptsd2019 | 618 |
| Eating Disorders | an2017 | 348 |
| Cross-Disorder | cdg2019 | 10,234 |

3 disorders failed: Substance Use (data quality issue in BP column), OCD/Tourette (schema mismatch across parquet files), and Other (rate limited). These can be retried with alternative publication configs.

### Caveats

- **Correlations are beta correlations**, not LD score regression (LDSC) estimates. Directions (positive/negative) are reliable, but magnitudes are inflated when few SNPs overlap.
- **Extreme values** (rg near 1.0 or -1.0) happen when only 3-10 SNPs overlap between disorders. True LDSC values are typically more moderate.
- **PTSD shows zero correlation** with everything because it only has 618 significant SNPs with almost no overlap with other disorders.

## Quick start

### 1. Set up Python environment

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Set your HuggingFace token (optional but recommended)

```bash
echo "HF_TOKEN=hf_your_token_here" > .env
```

Get a free token at [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens). Without it, you'll hit rate limits on large datasets.

### 3. Run the pipeline

```bash
python scripts/run_pipeline.py
```

This queries HuggingFace, processes all disorders, and exports JSON snapshots to `data/`. Takes ~30 minutes with a token (mostly waiting on rate limit cooldowns).

### 4. Copy data to frontend

```bash
./scripts/copy-data.sh
```

### 5. Run the frontend

```bash
cd web && npm install && npm run dev
```

Open http://localhost:3000.

## Architecture

```
HuggingFace Parquet ──→ DuckDB (predicate pushdown) ──→ Polars DataFrames
                                                              │
                                                    column normalization
                                                    p-value filtering
                                                    beta correlation
                                                              │
                                                      JSON snapshots
                                                              │
                                              Next.js 16 + Tailwind + shadcn/ui
                                              D3.js (Manhattan) + Plotly (Heatmap)
                                              react-force-graph (Network)
                                                              │
                                                    Vercel (static deploy)
```

## Project structure

```
pgc-explorer/
├── pgc_explorer/           # Python package
│   ├── config.py           # Dataset registry, column normalization
│   ├── loader.py           # DuckDB-based HuggingFace loader
│   ├── analysis.py         # Cross-disorder correlation
│   └── export.py           # JSON snapshot export
├── tests/                  # Python tests (9 tests)
├── notebooks/              # Jupyter notebook (alternative to script)
├── scripts/
│   ├── run_pipeline.py     # Main pipeline script
│   ├── copy-data.sh        # Copy snapshots to frontend
│   └── deploy-after-pipeline.sh
├── web/                    # Next.js frontend
│   ├── app/                # Pages (/, /correlations, /manhattan, /network)
│   ├── components/         # Nav, charts, cards
│   ├── lib/data.ts         # TypeScript data loaders
│   └── public/data/        # JSON snapshots served statically
└── data/                   # Pipeline output (gitignored)
```

## Data source

12 disorder groups from [`OpenMed/pgc-*`](https://huggingface.co/OpenMed) on HuggingFace, representing GWAS summary statistics from the Psychiatric Genomics Consortium.
