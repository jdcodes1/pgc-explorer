# PGC Explorer

Cross-disorder psychiatric genetics visualization tool.

## Architecture
- **Python pipeline** (`pgc_explorer/` + `notebooks/`): Loads 12 PGC GWAS datasets from HuggingFace (~1B rows), processes with Polars, exports JSON snapshots
- **Next.js frontend** (`web/`): Interactive visualizations (correlation heatmap, Manhattan overlay, network graph)
- **Data flow**: HuggingFace → Python → JSON snapshots → Next.js static imports

## Key Datasets
12 disorder groups from `OpenMed/pgc-*` on HuggingFace. Column schemas vary by publication — `pgc_explorer/config.py` handles normalization.

## Data Scale
~1B rows total. Only top SNPs (p < 1e-5) are exported for the frontend (~100K-500K per disorder). Correlation matrix is 12x12. Network graph is 12 nodes.
