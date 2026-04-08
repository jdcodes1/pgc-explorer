# PGC Explorer

Interactive cross-disorder psychiatric genetics visualization.
Built on **1 billion+ rows** of GWAS summary statistics from the
[Psychiatric Genomics Consortium](https://pgc.unc.edu/) via
[HuggingFace](https://huggingface.co/OpenMed).

## Quick Start

### 1. Python pipeline

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
jupyter notebook notebooks/01_load_and_export.ipynb
```

Run all cells. This downloads ~50GB from HuggingFace and exports JSON snapshots to `data/`.

### 2. Copy data to frontend

```bash
./scripts/copy-data.sh
```

### 3. Run the frontend

```bash
cd web && npm install && npm run dev
```

Open http://localhost:3000.

## Visualizations

- **Genetic Correlations** — 12x12 heatmap of cross-disorder genetic correlations
- **Manhattan Overlay** — Multi-disorder Manhattan plots, overlay up to 3 disorders
- **Disorder Network** — Force-directed graph showing disorder families by genetic similarity

## Data Source

12 disorder groups from `OpenMed/pgc-*` on HuggingFace:
ADHD, Anxiety, Autism, Bipolar, Depression, Eating Disorders,
OCD/Tourette, Other, PTSD, Schizophrenia, Substance Use, Cross-Disorder.

## Architecture

```
Python pipeline (Polars) --> JSON snapshots --> Next.js (D3 + Plotly + force-graph)
```
