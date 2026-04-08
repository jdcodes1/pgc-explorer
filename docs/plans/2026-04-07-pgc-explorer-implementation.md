# PGC Explorer Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a cross-disorder psychiatric genetics visualization tool with Jupyter notebooks for data processing and a Next.js frontend for interactive charts.

**Architecture:** Python pipeline loads 12 HuggingFace PGC datasets (~1B rows), processes them with Polars into aggregated JSON snapshots (correlation matrix, top SNPs, network graph). Next.js frontend renders these as interactive visualizations using D3, Plotly, and react-force-graph.

**Tech Stack:** Python (datasets, polars, scipy, numpy, jupyter), Next.js 16, D3.js, react-plotly.js, react-force-graph-2d, shadcn/ui, Tailwind CSS

---

## Dataset Reference

| Dataset | HuggingFace ID | Rows | Configs (publications) |
|---------|---------------|------|----------------------|
| ADHD | `OpenMed/pgc-adhd` | 31.2M | varies |
| Anxiety | `OpenMed/pgc-anxiety` | 27.5M | varies |
| Autism | `OpenMed/pgc-autism` | 18.6M | varies |
| Bipolar | `OpenMed/pgc-bipolar` | 74.4M | varies |
| Depression (MDD) | `OpenMed/pgc-mdd` | 179M | varies |
| Substance Use | `OpenMed/pgc-substance-use` | 214M | varies |
| Schizophrenia | `OpenMed/pgc-schizophrenia` | 91.4M | scz2011, scz2013sweden, scz2014, scz2018clozuk, scz2019asi, scz2022 |
| PTSD | `OpenMed/pgc-ptsd` | 128M | varies |
| Other | `OpenMed/pgc-other` | 40.9M | varies |
| OCD/Tourette | `OpenMed/pgc-ocd-tourette` | 36.5M | varies |
| Eating Disorders | `OpenMed/pgc-eating-disorders` | 10.6M | varies |
| Cross-Disorder | `OpenMed/pgc-cross-disorder` | 63.3M | varies |

**Column schema varies by publication but typically includes:**
`SNP/ID`, `CHR`, `BP/POS`, `A1/ALT`, `A2/REF`, `OR/BETA`, `SE`, `P/Pval`, `INFO`, `FRQ/MAF`

---

### Task 1: Project Scaffolding

**Files:**
- Create: `pgc_explorer/__init__.py`
- Create: `pgc_explorer/config.py`
- Create: `pgc_explorer/loader.py`
- Create: `tests/__init__.py`
- Create: `tests/test_loader.py`
- Create: `requirements.txt`
- Create: `.gitignore`
- Create: `context.md`

**Step 1: Create `.gitignore`**

```gitignore
# Python
__pycache__/
*.pyc
.ipynb_checkpoints/
*.egg-info/
venv/
.venv/

# Data
data/
*.parquet

# Next.js
web/node_modules/
web/.next/
web/out/

# Env
.env*.local
.env
```

**Step 2: Create `requirements.txt`**

```
datasets>=3.0
polars>=1.0
scipy>=1.14
numpy>=2.0
jupyter
matplotlib
```

**Step 3: Create `pgc_explorer/config.py`**

This defines the dataset registry — all 12 disorder groups with their HuggingFace IDs and which config to use (latest publication per disorder).

```python
"""PGC dataset configuration and column normalization."""

from dataclasses import dataclass
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"

@dataclass
class DisorderDataset:
    name: str
    hf_id: str
    config: str  # which publication config to use (latest/best)
    color: str   # for visualization

# Use the latest/largest publication per disorder for cross-disorder analysis.
# Users should verify these configs exist by running:
#   from datasets import get_dataset_config_names
#   get_dataset_config_names("OpenMed/pgc-<disorder>")
DISORDERS: list[DisorderDataset] = [
    DisorderDataset("ADHD", "OpenMed/pgc-adhd", "default", "#e74c3c"),
    DisorderDataset("Anxiety", "OpenMed/pgc-anxiety", "default", "#e67e22"),
    DisorderDataset("Autism", "OpenMed/pgc-autism", "default", "#f1c40f"),
    DisorderDataset("Bipolar", "OpenMed/pgc-bipolar", "default", "#2ecc71"),
    DisorderDataset("Depression", "OpenMed/pgc-mdd", "default", "#3498db"),
    DisorderDataset("Substance Use", "OpenMed/pgc-substance-use", "default", "#9b59b6"),
    DisorderDataset("Schizophrenia", "OpenMed/pgc-schizophrenia", "scz2022", "#1abc9c"),
    DisorderDataset("PTSD", "OpenMed/pgc-ptsd", "default", "#e91e63"),
    DisorderDataset("OCD/Tourette", "OpenMed/pgc-ocd-tourette", "default", "#00bcd4"),
    DisorderDataset("Eating Disorders", "OpenMed/pgc-eating-disorders", "default", "#ff9800"),
    DisorderDataset("Cross-Disorder", "OpenMed/pgc-cross-disorder", "default", "#607d8b"),
    DisorderDataset("Other", "OpenMed/pgc-other", "default", "#795548"),
]

# Column name normalization map.
# Different publications use different column names for the same data.
# Keys are canonical names, values are possible source column names (tried in order).
COLUMN_MAP: dict[str, list[str]] = {
    "snp": ["SNP", "ID", "SNPID", "MarkerName", "rsid", "variant_id"],
    "chr": ["CHR", "chromosome", "chr", "hm_chrom", "#CHROM"],
    "bp": ["BP", "POS", "position", "base_pair_location", "hm_pos"],
    "a1": ["A1", "ALT", "effect_allele", "allele1", "Allele1"],
    "a2": ["A2", "REF", "other_allele", "allele2", "Allele2"],
    "beta": ["BETA", "beta", "Effect", "b", "logOR"],
    "or_val": ["OR"],
    "se": ["SE", "StdErr", "se", "standard_error"],
    "p": ["P", "Pval", "p_value", "P-value", "pval", "PVALUE", "p-value"],
    "freq": ["FRQ", "MAF", "Freq1", "frequency", "EAF", "A1FREQ"],
}


def normalize_columns(columns: list[str]) -> dict[str, str]:
    """Map source column names to canonical names.

    Returns dict of {canonical_name: source_column_name} for columns found.
    """
    result = {}
    for canonical, candidates in COLUMN_MAP.items():
        for candidate in candidates:
            if candidate in columns:
                result[canonical] = candidate
                break
    return result
```

**Step 4: Create `pgc_explorer/loader.py`**

```python
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
```

**Step 5: Create `tests/test_loader.py`**

```python
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
```

**Step 6: Create `pgc_explorer/__init__.py`**

```python
"""PGC Explorer — Cross-disorder psychiatric genetics analysis."""
```

**Step 7: Create `tests/__init__.py`**

Empty file.

**Step 8: Run tests**

```bash
cd /Users/joey/Documents/programming/pgc-explorer
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install pytest
pytest tests/ -v
```

Expected: All 4 tests pass.

**Step 9: Create `context.md`**

```markdown
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
```

**Step 10: Commit**

```bash
git add -A
git commit -m "feat: project scaffolding with Python pipeline config and column normalization"
```

---

### Task 2: Data Processing — Compute Cross-Disorder Overlap

**Files:**
- Create: `pgc_explorer/analysis.py`
- Create: `tests/test_analysis.py`

**Step 1: Write failing tests for overlap computation**

```python
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
        "A": _make_disorder_df(["rs1", "rs2", "rs3"], [1, 1, 2], [100, 200, 300], [1e-8, 1e-7, 1e-6], [0.1, 0.2, 0.3]),
        "B": _make_disorder_df(["rs2", "rs3", "rs4"], [1, 2, 3], [200, 300, 400], [1e-9, 1e-5, 1e-8], [0.15, 0.25, 0.35]),
        "C": _make_disorder_df(["rs5"], [4], [500], [1e-8], [0.5]),
    }
    matrix = compute_correlation_matrix(disorders)
    assert matrix["labels"] == ["A", "B", "C"]
    # A-B should have positive correlation (shared rs2, rs3 with same-sign betas)
    assert matrix["values"][0][1] > 0  # A-B
    assert matrix["values"][1][0] == matrix["values"][0][1]  # symmetric
    # Diagonal should be 1.0
    assert matrix["values"][0][0] == 1.0
```

**Step 2: Run tests to verify they fail**

```bash
pytest tests/test_analysis.py -v
```

Expected: ImportError — `analysis` module doesn't exist yet.

**Step 3: Implement `pgc_explorer/analysis.py`**

```python
"""Cross-disorder analysis: SNP overlap and genetic correlation approximation."""

import numpy as np
import polars as pl


def compute_snp_overlap(df_a: pl.DataFrame, df_b: pl.DataFrame) -> pl.DataFrame:
    """Find SNPs present in both disorder DataFrames.

    Returns DataFrame with columns from both, suffixed _a and _b.
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
```

**Step 4: Run tests**

```bash
pytest tests/test_analysis.py -v
```

Expected: All 3 tests pass.

**Step 5: Commit**

```bash
git add pgc_explorer/analysis.py tests/test_analysis.py
git commit -m "feat: cross-disorder SNP overlap and beta correlation analysis"
```

---

### Task 3: Data Processing — Export Snapshots

**Files:**
- Create: `pgc_explorer/export.py`
- Create: `tests/test_export.py`

**Step 1: Write failing tests**

```python
"""Tests for snapshot export functions."""

import json
from pathlib import Path

import polars as pl

from pgc_explorer.export import export_manhattan_data, export_network_graph


def _make_df(snps, chroms, bps, pvals, betas):
    return pl.DataFrame({"snp": snps, "chr": chroms, "bp": bps, "p": pvals, "beta": betas})


def test_export_manhattan_data(tmp_path):
    df = _make_df(
        ["rs1", "rs2", "rs3"],
        [1, 1, 2],
        [1000, 2000, 50000],
        [1e-8, 1e-6, 1e-10],
        [0.1, 0.2, 0.3],
    )
    export_manhattan_data({"SCZ": df}, tmp_path)

    result = json.loads((tmp_path / "manhattan" / "SCZ.json").read_text())
    assert len(result["snps"]) == 3
    assert result["snps"][0]["snp"] == "rs1"
    assert result["snps"][0]["chr"] == 1
    assert result["snps"][0]["neglog10p"] > 7  # -log10(1e-8) = 8


def test_export_network_graph():
    correlation = {
        "labels": ["A", "B", "C"],
        "values": [[1.0, 0.5, 0.1], [0.5, 1.0, 0.8], [0.1, 0.8, 1.0]],
    }
    sig_counts = {"A": 100, "B": 200, "C": 50}
    colors = {"A": "#ff0000", "B": "#00ff00", "C": "#0000ff"}

    graph = export_network_graph(correlation, sig_counts, colors)

    assert len(graph["nodes"]) == 3
    assert len(graph["links"]) == 3  # 3 pairs: A-B, A-C, B-C
    # Nodes should have size based on sig_counts
    node_b = next(n for n in graph["nodes"] if n["id"] == "B")
    assert node_b["sigLoci"] == 200
```

**Step 2: Run tests to verify failure**

```bash
pytest tests/test_export.py -v
```

**Step 3: Implement `pgc_explorer/export.py`**

```python
"""Export processed data to JSON snapshots for the frontend."""

import json
import math
from pathlib import Path

import polars as pl


def export_manhattan_data(disorders: dict[str, pl.DataFrame], output_dir: Path) -> None:
    """Export per-disorder Manhattan plot data as JSON.

    Each disorder gets a file: output_dir/manhattan/<name>.json
    Contains SNPs with: snp, chr, bp, neglog10p, beta
    """
    manhattan_dir = output_dir / "manhattan"
    manhattan_dir.mkdir(parents=True, exist_ok=True)

    for name, df in disorders.items():
        records = []
        for row in df.iter_rows(named=True):
            p = row.get("p", 1.0)
            neglog10p = -math.log10(p) if p and p > 0 else 0
            records.append({
                "snp": row.get("snp", ""),
                "chr": row.get("chr"),
                "bp": row.get("bp"),
                "neglog10p": round(neglog10p, 2),
                "beta": round(row.get("beta", 0) or 0, 4),
            })

        # Sort by chromosome then position
        records.sort(key=lambda r: (r["chr"] or 0, r["bp"] or 0))

        data = {"disorder": name, "snps": records, "count": len(records)}
        (manhattan_dir / f"{name}.json").write_text(json.dumps(data))


def export_network_graph(
    correlation: dict,
    sig_counts: dict[str, int],
    colors: dict[str, str],
    min_edge_weight: float = 0.05,
) -> dict:
    """Build network graph JSON from correlation matrix.

    Args:
        correlation: Dict with "labels" and "values" (from compute_correlation_matrix).
        sig_counts: Dict mapping disorder name to number of significant loci.
        colors: Dict mapping disorder name to hex color.
        min_edge_weight: Minimum absolute correlation to include an edge.

    Returns:
        Dict with "nodes" and "links" for react-force-graph.
    """
    labels = correlation["labels"]
    values = correlation["values"]

    nodes = []
    for label in labels:
        nodes.append({
            "id": label,
            "sigLoci": sig_counts.get(label, 0),
            "color": colors.get(label, "#888888"),
        })

    links = []
    for i in range(len(labels)):
        for j in range(i + 1, len(labels)):
            weight = values[i][j]
            if abs(weight) >= min_edge_weight:
                links.append({
                    "source": labels[i],
                    "target": labels[j],
                    "weight": round(weight, 4),
                })

    return {"nodes": nodes, "links": links}


def export_correlation_matrix(correlation: dict, output_dir: Path) -> None:
    """Write correlation matrix to JSON."""
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "correlation_matrix.json").write_text(json.dumps(correlation))


def export_metadata(disorders: dict[str, pl.DataFrame], colors: dict[str, str], output_dir: Path) -> None:
    """Write metadata JSON with disorder info and counts."""
    output_dir.mkdir(parents=True, exist_ok=True)
    meta = {
        "disorders": [
            {"name": name, "snpCount": len(df), "color": colors.get(name, "#888")}
            for name, df in disorders.items()
        ],
        "totalSnps": sum(len(df) for df in disorders.values()),
    }
    (output_dir / "metadata.json").write_text(json.dumps(meta))
```

**Step 4: Run tests**

```bash
pytest tests/ -v
```

Expected: All tests pass.

**Step 5: Commit**

```bash
git add pgc_explorer/export.py tests/test_export.py
git commit -m "feat: JSON snapshot export for Manhattan, network graph, and correlation data"
```

---

### Task 4: Jupyter Notebook — Full Pipeline

**Files:**
- Create: `notebooks/01_load_and_export.ipynb`

**Step 1: Create the notebook**

This is the main pipeline notebook. It loads all 12 disorders from HuggingFace, processes them, and exports JSON snapshots.

Create `notebooks/01_load_and_export.ipynb` with these cells:

**Cell 1 (markdown):**
```markdown
# PGC Explorer — Data Pipeline
Load all 12 PGC disorder datasets from HuggingFace, compute cross-disorder correlations, and export JSON snapshots for the web frontend.

**Requirements:** `pip install -r requirements.txt`

**Runtime:** ~30-60 minutes depending on network speed (downloads ~50GB of parquet data).
```

**Cell 2 (code):**
```python
import sys
sys.path.insert(0, "..")

from pgc_explorer.config import DISORDERS, DATA_DIR
from pgc_explorer.loader import load_disorder
from pgc_explorer.analysis import compute_correlation_matrix
from pgc_explorer.export import (
    export_manhattan_data,
    export_network_graph,
    export_correlation_matrix,
    export_metadata,
)
import json
```

**Cell 3 (markdown):**
```markdown
## Step 1: Load and filter all disorders
This loads each dataset from HuggingFace, normalizes columns, and filters to SNPs with p < 1e-5.
```

**Cell 4 (code):**
```python
disorders = {}
failed = []

for d in DISORDERS:
    print(f"Loading {d.name} ({d.hf_id}, config={d.config})...")
    try:
        df = load_disorder(d, p_threshold=1e-5)
        disorders[d.name] = df
        print(f"  ✓ {len(df):,} significant SNPs")
    except Exception as e:
        failed.append((d.name, str(e)))
        print(f"  ✗ Failed: {e}")

print(f"\nLoaded {len(disorders)}/{len(DISORDERS)} disorders")
if failed:
    print(f"Failed: {failed}")
```

**Cell 5 (markdown):**
```markdown
## Step 2: Compute cross-disorder correlation matrix
Uses Pearson correlation of effect sizes (beta) on shared SNPs as a proxy for genetic correlation.
```

**Cell 6 (code):**
```python
correlation = compute_correlation_matrix(disorders)
print("Correlation matrix computed:")
for i, label in enumerate(correlation["labels"]):
    row = [f"{v:+.2f}" for v in correlation["values"][i]]
    print(f"  {label:20s} {' '.join(row)}")
```

**Cell 7 (markdown):**
```markdown
## Step 3: Export JSON snapshots
```

**Cell 8 (code):**
```python
DATA_DIR.mkdir(parents=True, exist_ok=True)
colors = {d.name: d.color for d in DISORDERS}

# Export all snapshots
export_correlation_matrix(correlation, DATA_DIR)
print("✓ Correlation matrix exported")

export_manhattan_data(disorders, DATA_DIR)
print("✓ Manhattan data exported")

sig_counts = {name: len(df) for name, df in disorders.items()}
graph = export_network_graph(correlation, sig_counts, colors)
(DATA_DIR / "network_graph.json").write_text(json.dumps(graph))
print("✓ Network graph exported")

export_metadata(disorders, colors, DATA_DIR)
print("✓ Metadata exported")

print(f"\nAll snapshots written to {DATA_DIR}")
```

**Step 2: Commit**

```bash
git add notebooks/
git commit -m "feat: Jupyter notebook for full data pipeline"
```

---

### Task 5: Next.js Scaffold with shadcn/ui

**Step 1: Create Next.js project**

```bash
cd /Users/joey/Documents/programming/pgc-explorer
npx create-next-app@latest web --typescript --tailwind --eslint --app --src-dir=false --import-alias="@/*" --turbopack
```

**Step 2: Initialize shadcn/ui**

```bash
cd web
npx shadcn@latest init -d
```

**Step 3: Add shadcn components**

```bash
npx shadcn@latest add card button select tabs badge separator tooltip navigation-menu
```

**Step 4: Set dark mode as default**

Edit `web/app/layout.tsx`:
- Add `className="dark"` to the `<html>` tag.

**Step 5: Create `web/lib/data.ts`**

```typescript
/**
 * Load pre-computed JSON snapshots from public/data/.
 * In production these are static imports. During dev, fetch from public/.
 */

export interface ManhattanSNP {
  snp: string;
  chr: number;
  bp: number;
  neglog10p: number;
  beta: number;
}

export interface ManhattanData {
  disorder: string;
  snps: ManhattanSNP[];
  count: number;
}

export interface CorrelationMatrix {
  labels: string[];
  values: number[][];
}

export interface NetworkNode {
  id: string;
  sigLoci: number;
  color: string;
}

export interface NetworkLink {
  source: string;
  target: string;
  weight: number;
}

export interface NetworkGraph {
  nodes: NetworkNode[];
  links: NetworkLink[];
}

export interface DisorderMeta {
  name: string;
  snpCount: number;
  color: string;
}

export interface Metadata {
  disorders: DisorderMeta[];
  totalSnps: number;
}

export async function loadCorrelationMatrix(): Promise<CorrelationMatrix> {
  const res = await fetch("/data/correlation_matrix.json");
  return res.json();
}

export async function loadManhattanData(disorder: string): Promise<ManhattanData> {
  const res = await fetch(`/data/manhattan/${disorder}.json`);
  return res.json();
}

export async function loadNetworkGraph(): Promise<NetworkGraph> {
  const res = await fetch("/data/network_graph.json");
  return res.json();
}

export async function loadMetadata(): Promise<Metadata> {
  const res = await fetch("/data/metadata.json");
  return res.json();
}
```

**Step 6: Create placeholder data for development**

Create `web/public/data/metadata.json`:
```json
{
  "disorders": [
    {"name": "Schizophrenia", "snpCount": 50000, "color": "#1abc9c"},
    {"name": "Bipolar", "snpCount": 35000, "color": "#2ecc71"},
    {"name": "Depression", "snpCount": 80000, "color": "#3498db"},
    {"name": "ADHD", "snpCount": 20000, "color": "#e74c3c"},
    {"name": "Autism", "snpCount": 15000, "color": "#f1c40f"},
    {"name": "PTSD", "snpCount": 45000, "color": "#e91e63"},
    {"name": "Anxiety", "snpCount": 25000, "color": "#e67e22"},
    {"name": "OCD/Tourette", "snpCount": 12000, "color": "#00bcd4"},
    {"name": "Eating Disorders", "snpCount": 8000, "color": "#ff9800"},
    {"name": "Substance Use", "snpCount": 60000, "color": "#9b59b6"},
    {"name": "Cross-Disorder", "snpCount": 40000, "color": "#607d8b"},
    {"name": "Other", "snpCount": 10000, "color": "#795548"}
  ],
  "totalSnps": 400000
}
```

**Step 7: Run dev server to verify**

```bash
cd web && npm run dev
```

Verify: http://localhost:3000 loads the default Next.js page.

**Step 8: Commit**

```bash
cd /Users/joey/Documents/programming/pgc-explorer
git add web/ context.md
git commit -m "feat: Next.js scaffold with shadcn/ui and dark mode"
```

---

### Task 6: Landing Page

**Files:**
- Modify: `web/app/page.tsx`
- Modify: `web/app/layout.tsx`
- Create: `web/app/globals.css` (update)
- Create: `web/components/stat-card.tsx`
- Create: `web/components/nav.tsx`

**Step 1: Create `web/components/nav.tsx`**

```tsx
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const links = [
  { href: "/", label: "Overview" },
  { href: "/correlations", label: "Correlations" },
  { href: "/manhattan", label: "Manhattan" },
  { href: "/network", label: "Network" },
];

export function Nav() {
  const pathname = usePathname();

  return (
    <nav className="border-b border-zinc-800 bg-zinc-950">
      <div className="mx-auto flex h-14 max-w-7xl items-center gap-6 px-6">
        <Link href="/" className="font-mono text-sm font-bold tracking-tight text-zinc-100">
          PGC Explorer
        </Link>
        <div className="flex gap-1">
          {links.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={cn(
                "rounded-md px-3 py-1.5 text-sm transition-colors",
                pathname === link.href
                  ? "bg-zinc-800 text-zinc-100"
                  : "text-zinc-400 hover:text-zinc-100"
              )}
            >
              {link.label}
            </Link>
          ))}
        </div>
      </div>
    </nav>
  );
}
```

**Step 2: Create `web/components/stat-card.tsx`**

```tsx
import { Card, CardContent } from "@/components/ui/card";

interface StatCardProps {
  label: string;
  value: string;
  sub?: string;
}

export function StatCard({ label, value, sub }: StatCardProps) {
  return (
    <Card className="bg-zinc-900 border-zinc-800">
      <CardContent className="pt-6">
        <p className="text-sm text-zinc-400">{label}</p>
        <p className="mt-1 font-mono text-3xl font-bold text-zinc-100">{value}</p>
        {sub && <p className="mt-1 text-xs text-zinc-500">{sub}</p>}
      </CardContent>
    </Card>
  );
}
```

**Step 3: Update `web/app/layout.tsx`**

```tsx
import type { Metadata } from "next";
import { GeistSans } from "geist/font/sans";
import { GeistMono } from "geist/font/mono";
import { Nav } from "@/components/nav";
import "./globals.css";

export const metadata: Metadata = {
  title: "PGC Explorer — Psychiatric Genetics Cross-Disorder Analysis",
  description: "Interactive visualization of genetic overlaps across 12 psychiatric disorders using PGC GWAS summary statistics.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className={`${GeistSans.variable} ${GeistMono.variable} font-sans bg-zinc-950 text-zinc-100 antialiased`}>
        <Nav />
        <main className="mx-auto max-w-7xl px-6 py-8">
          {children}
        </main>
      </body>
    </html>
  );
}
```

Note: Install Geist fonts: `npm install geist`

**Step 4: Update `web/app/page.tsx`**

```tsx
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { StatCard } from "@/components/stat-card";

const vizCards = [
  {
    title: "Genetic Correlations",
    description: "12×12 heatmap of cross-disorder genetic correlations. Which disorders share the most genetic architecture?",
    href: "/correlations",
    badge: "Heatmap",
  },
  {
    title: "Manhattan Overlay",
    description: "Multi-disorder Manhattan plots. Overlay up to 3 disorders to spot shared genomic peaks.",
    href: "/manhattan",
    badge: "GWAS",
  },
  {
    title: "Disorder Network",
    description: "Force-directed network graph. Disorders cluster by genetic similarity, revealing hidden families.",
    href: "/network",
    badge: "Network",
  },
];

export default function Home() {
  return (
    <div className="space-y-12">
      {/* Hero */}
      <div className="space-y-4">
        <h1 className="font-mono text-4xl font-bold tracking-tight">
          Psychiatric Genomics<br />
          <span className="text-zinc-400">Cross-Disorder Explorer</span>
        </h1>
        <p className="max-w-2xl text-lg text-zinc-400">
          Interactive visualization of genetic overlaps across psychiatric disorders.
          Built on{" "}
          <span className="text-zinc-200">1 billion+ rows</span> of GWAS summary
          statistics from the{" "}
          <span className="text-zinc-200">Psychiatric Genomics Consortium</span>.
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatCard label="Disorder Groups" value="12" sub="ADHD, SCZ, MDD, BIP..." />
        <StatCard label="Publications" value="52" sub="PGC GWAS studies" />
        <StatCard label="Total Variants" value="1B+" sub="Summary statistics" />
        <StatCard label="Data Source" value="HF" sub="OpenMed/pgc-*" />
      </div>

      {/* Viz cards */}
      <div className="grid gap-4 sm:grid-cols-3">
        {vizCards.map((card) => (
          <Link key={card.href} href={card.href}>
            <Card className="h-full bg-zinc-900 border-zinc-800 transition-colors hover:border-zinc-600">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="text-lg">{card.title}</CardTitle>
                  <Badge variant="secondary">{card.badge}</Badge>
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-zinc-400">{card.description}</p>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
```

**Step 5: Run dev server and verify**

```bash
cd web && npm run dev
```

Verify: Landing page renders with hero, stat cards, and 3 visualization cards.

**Step 6: Commit**

```bash
git add -A
git commit -m "feat: landing page with nav, stat cards, and viz card links"
```

---

### Task 7: Correlation Heatmap Page

**Files:**
- Create: `web/app/correlations/page.tsx`
- Create: `web/components/correlation-heatmap.tsx`

**Step 1: Create `web/public/data/correlation_matrix.json` (placeholder)**

```json
{
  "labels": ["SCZ", "BIP", "MDD", "ADHD", "ASD", "PTSD", "ANX", "OCD", "ED", "SU", "XD", "OTH"],
  "values": [
    [1.0, 0.68, 0.35, 0.12, 0.16, 0.25, 0.30, 0.15, 0.10, 0.20, 0.45, 0.08],
    [0.68, 1.0, 0.40, 0.15, 0.10, 0.20, 0.28, 0.12, 0.08, 0.18, 0.42, 0.06],
    [0.35, 0.40, 1.0, 0.30, 0.08, 0.45, 0.55, 0.20, 0.25, 0.30, 0.50, 0.10],
    [0.12, 0.15, 0.30, 1.0, 0.20, 0.15, 0.25, 0.10, 0.05, 0.35, 0.25, 0.12],
    [0.16, 0.10, 0.08, 0.20, 1.0, 0.05, 0.10, 0.18, 0.03, 0.08, 0.15, 0.20],
    [0.25, 0.20, 0.45, 0.15, 0.05, 1.0, 0.50, 0.15, 0.12, 0.28, 0.35, 0.08],
    [0.30, 0.28, 0.55, 0.25, 0.10, 0.50, 1.0, 0.30, 0.20, 0.25, 0.40, 0.10],
    [0.15, 0.12, 0.20, 0.10, 0.18, 0.15, 0.30, 1.0, 0.15, 0.10, 0.20, 0.25],
    [0.10, 0.08, 0.25, 0.05, 0.03, 0.12, 0.20, 0.15, 1.0, 0.15, 0.18, 0.05],
    [0.20, 0.18, 0.30, 0.35, 0.08, 0.28, 0.25, 0.10, 0.15, 1.0, 0.30, 0.10],
    [0.45, 0.42, 0.50, 0.25, 0.15, 0.35, 0.40, 0.20, 0.18, 0.30, 1.0, 0.12],
    [0.08, 0.06, 0.10, 0.12, 0.20, 0.08, 0.10, 0.25, 0.05, 0.10, 0.12, 1.0]
  ]
}
```

**Step 2: Create `web/components/correlation-heatmap.tsx`**

```tsx
"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import type { CorrelationMatrix } from "@/lib/data";
import { loadCorrelationMatrix } from "@/lib/data";

const Plot = dynamic(() => import("react-plotly.js"), { ssr: false });

export function CorrelationHeatmap() {
  const [data, setData] = useState<CorrelationMatrix | null>(null);

  useEffect(() => {
    loadCorrelationMatrix().then(setData);
  }, []);

  if (!data) {
    return <div className="flex h-96 items-center justify-center text-zinc-500">Loading correlation data...</div>;
  }

  return (
    <Plot
      data={[
        {
          z: data.values,
          x: data.labels,
          y: data.labels,
          type: "heatmap",
          colorscale: [
            [0, "#2563eb"],    // negative: blue
            [0.5, "#18181b"],  // zero: dark
            [1, "#dc2626"],    // positive: red
          ],
          zmin: -1,
          zmax: 1,
          hovertemplate: "%{x} ↔ %{y}<br>rg = %{z:.3f}<extra></extra>",
          showscale: true,
          colorbar: {
            title: { text: "Genetic Correlation (rg)", side: "right" },
            tickfont: { color: "#a1a1aa" },
            titlefont: { color: "#a1a1aa" },
          },
        },
      ]}
      layout={{
        width: 700,
        height: 700,
        paper_bgcolor: "transparent",
        plot_bgcolor: "transparent",
        font: { color: "#a1a1aa", family: "monospace" },
        xaxis: { side: "bottom", tickangle: -45 },
        yaxis: { autorange: "reversed" },
        margin: { l: 100, r: 40, t: 20, b: 100 },
      }}
      config={{ responsive: true, displayModeBar: false }}
    />
  );
}
```

**Step 3: Create `web/app/correlations/page.tsx`**

```tsx
import { CorrelationHeatmap } from "@/components/correlation-heatmap";

export default function CorrelationsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-mono text-2xl font-bold">Genetic Correlations</h1>
        <p className="mt-2 text-sm text-zinc-400">
          Pairwise genetic correlation (rg) across psychiatric disorders.
          Red = positive correlation (shared genetic risk). Blue = negative.
          Based on effect size concordance of shared genome-wide significant SNPs.
        </p>
      </div>
      <CorrelationHeatmap />
    </div>
  );
}
```

**Step 4: Install plotly**

```bash
cd web && npm install react-plotly.js plotly.js
```

**Step 5: Run dev server and verify heatmap renders**

**Step 6: Commit**

```bash
git add -A
git commit -m "feat: correlation heatmap page with Plotly"
```

---

### Task 8: Manhattan Overlay Page

**Files:**
- Create: `web/app/manhattan/page.tsx`
- Create: `web/components/manhattan-plot.tsx`

**Step 1: Create placeholder Manhattan data**

Create `web/public/data/manhattan/Schizophrenia.json` with ~100 sample SNPs:

```json
{
  "disorder": "Schizophrenia",
  "snps": [
    {"snp": "rs1", "chr": 1, "bp": 1000000, "neglog10p": 12.5, "beta": 0.15},
    {"snp": "rs2", "chr": 1, "bp": 5000000, "neglog10p": 8.2, "beta": -0.10}
  ],
  "count": 2
}
```

(Create similar files for `Bipolar.json` and `Depression.json` with different sample data.)

**Step 2: Create `web/components/manhattan-plot.tsx`**

```tsx
"use client";

import { useEffect, useRef, useState } from "react";
import * as d3 from "d3";
import { loadManhattanData, loadMetadata } from "@/lib/data";
import type { ManhattanData, ManhattanSNP, DisorderMeta } from "@/lib/data";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";

const CHR_LENGTHS: Record<number, number> = {
  1: 249e6, 2: 243e6, 3: 198e6, 4: 191e6, 5: 182e6, 6: 171e6,
  7: 159e6, 8: 146e6, 9: 141e6, 10: 136e6, 11: 135e6, 12: 134e6,
  13: 115e6, 14: 107e6, 15: 103e6, 16: 90e6, 17: 84e6, 18: 80e6,
  19: 59e6, 20: 64e6, 21: 47e6, 22: 51e6,
};

function getCumulativePosition(chr: number, bp: number): number {
  let offset = 0;
  for (let c = 1; c < chr; c++) {
    offset += CHR_LENGTHS[c] || 0;
  }
  return offset + bp;
}

interface Props {
  disorders: DisorderMeta[];
}

export function ManhattanPlot({ disorders }: Props) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [selected, setSelected] = useState<string[]>([]);
  const [datasets, setDatasets] = useState<ManhattanData[]>([]);

  const addDisorder = (name: string) => {
    if (selected.length < 3 && !selected.includes(name)) {
      setSelected([...selected, name]);
    }
  };

  const removeDisorder = (name: string) => {
    setSelected(selected.filter((s) => s !== name));
  };

  useEffect(() => {
    Promise.all(selected.map((name) => loadManhattanData(name))).then(setDatasets);
  }, [selected]);

  useEffect(() => {
    if (!svgRef.current || datasets.length === 0) return;

    const width = 1100;
    const height = 450;
    const margin = { top: 20, right: 30, bottom: 50, left: 60 };

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();
    svg.attr("viewBox", `0 0 ${width} ${height}`);

    const totalGenome = Object.values(CHR_LENGTHS).reduce((a, b) => a + b, 0);

    const x = d3.scaleLinear()
      .domain([0, totalGenome])
      .range([margin.left, width - margin.right]);

    const allNeglog = datasets.flatMap((d) => d.snps.map((s) => s.neglog10p));
    const maxY = Math.max(15, d3.max(allNeglog) || 15);

    const y = d3.scaleLinear()
      .domain([0, maxY])
      .range([height - margin.bottom, margin.top]);

    // Chromosome boundaries
    let chrOffset = 0;
    for (let chr = 1; chr <= 22; chr++) {
      const len = CHR_LENGTHS[chr] || 0;
      const mid = chrOffset + len / 2;
      svg.append("text")
        .attr("x", x(mid))
        .attr("y", height - margin.bottom + 30)
        .attr("text-anchor", "middle")
        .attr("fill", "#71717a")
        .attr("font-size", "10px")
        .attr("font-family", "monospace")
        .text(chr);

      if (chr % 2 === 0) {
        svg.append("rect")
          .attr("x", x(chrOffset))
          .attr("y", margin.top)
          .attr("width", x(chrOffset + len) - x(chrOffset))
          .attr("height", height - margin.top - margin.bottom)
          .attr("fill", "#27272a")
          .attr("opacity", 0.5);
      }
      chrOffset += len;
    }

    // Genome-wide significance line
    svg.append("line")
      .attr("x1", margin.left)
      .attr("x2", width - margin.right)
      .attr("y1", y(-Math.log10(5e-8)))
      .attr("y2", y(-Math.log10(5e-8)))
      .attr("stroke", "#ef4444")
      .attr("stroke-dasharray", "4,4")
      .attr("opacity", 0.6);

    // Y axis
    svg.append("g")
      .attr("transform", `translate(${margin.left},0)`)
      .call(d3.axisLeft(y).ticks(5))
      .call((g) => g.select(".domain").attr("stroke", "#3f3f46"))
      .call((g) => g.selectAll(".tick line").attr("stroke", "#3f3f46"))
      .call((g) => g.selectAll(".tick text").attr("fill", "#a1a1aa").attr("font-family", "monospace"));

    // Y label
    svg.append("text")
      .attr("transform", `rotate(-90)`)
      .attr("x", -(height / 2))
      .attr("y", 15)
      .attr("text-anchor", "middle")
      .attr("fill", "#a1a1aa")
      .attr("font-size", "12px")
      .attr("font-family", "monospace")
      .text("-log₁₀(p)");

    // Plot points for each disorder
    datasets.forEach((dataset) => {
      const meta = disorders.find((d) => d.name === dataset.disorder);
      const color = meta?.color || "#888";

      svg.selectAll(`.dot-${dataset.disorder}`)
        .data(dataset.snps)
        .join("circle")
        .attr("cx", (d) => x(getCumulativePosition(d.chr, d.bp)))
        .attr("cy", (d) => y(d.neglog10p))
        .attr("r", 2)
        .attr("fill", color)
        .attr("opacity", 0.6);
    });
  }, [datasets, disorders]);

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4">
        <Select onValueChange={addDisorder}>
          <SelectTrigger className="w-64 bg-zinc-900 border-zinc-700">
            <SelectValue placeholder="Add disorder (max 3)" />
          </SelectTrigger>
          <SelectContent>
            {disorders.map((d) => (
              <SelectItem key={d.name} value={d.name} disabled={selected.includes(d.name)}>
                {d.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <div className="flex gap-2">
          {selected.map((name) => {
            const meta = disorders.find((d) => d.name === name);
            return (
              <Badge
                key={name}
                variant="outline"
                className="cursor-pointer border-zinc-600"
                style={{ color: meta?.color }}
                onClick={() => removeDisorder(name)}
              >
                {name} ✕
              </Badge>
            );
          })}
        </div>
      </div>
      <svg ref={svgRef} className="w-full" />
      {selected.length === 0 && (
        <p className="text-center text-sm text-zinc-500">Select up to 3 disorders to overlay</p>
      )}
    </div>
  );
}
```

**Step 3: Create `web/app/manhattan/page.tsx`**

```tsx
"use client";

import { useEffect, useState } from "react";
import { ManhattanPlot } from "@/components/manhattan-plot";
import { loadMetadata } from "@/lib/data";
import type { DisorderMeta } from "@/lib/data";

export default function ManhattanPage() {
  const [disorders, setDisorders] = useState<DisorderMeta[]>([]);

  useEffect(() => {
    loadMetadata().then((m) => setDisorders(m.disorders));
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-mono text-2xl font-bold">Manhattan Overlay</h1>
        <p className="mt-2 text-sm text-zinc-400">
          Multi-disorder Manhattan plot. Select up to 3 disorders to overlay.
          Each color represents a different disorder. Red dashed line = genome-wide significance (5×10⁻⁸).
        </p>
      </div>
      {disorders.length > 0 && <ManhattanPlot disorders={disorders} />}
    </div>
  );
}
```

**Step 4: Install D3**

```bash
cd web && npm install d3 @types/d3
```

**Step 5: Run dev server and verify**

**Step 6: Commit**

```bash
git add -A
git commit -m "feat: Manhattan overlay page with D3, multi-disorder selection"
```

---

### Task 9: Network Graph Page

**Files:**
- Create: `web/app/network/page.tsx`
- Create: `web/components/disorder-network.tsx`

**Step 1: Create placeholder network data**

Create `web/public/data/network_graph.json`:

```json
{
  "nodes": [
    {"id": "SCZ", "sigLoci": 300, "color": "#1abc9c"},
    {"id": "BIP", "sigLoci": 200, "color": "#2ecc71"},
    {"id": "MDD", "sigLoci": 400, "color": "#3498db"},
    {"id": "ADHD", "sigLoci": 100, "color": "#e74c3c"},
    {"id": "ASD", "sigLoci": 80, "color": "#f1c40f"},
    {"id": "PTSD", "sigLoci": 250, "color": "#e91e63"},
    {"id": "ANX", "sigLoci": 150, "color": "#e67e22"},
    {"id": "OCD", "sigLoci": 60, "color": "#00bcd4"},
    {"id": "ED", "sigLoci": 40, "color": "#ff9800"},
    {"id": "SU", "sigLoci": 300, "color": "#9b59b6"},
    {"id": "XD", "sigLoci": 200, "color": "#607d8b"},
    {"id": "OTH", "sigLoci": 50, "color": "#795548"}
  ],
  "links": [
    {"source": "SCZ", "target": "BIP", "weight": 0.68},
    {"source": "SCZ", "target": "MDD", "weight": 0.35},
    {"source": "BIP", "target": "MDD", "weight": 0.40},
    {"source": "MDD", "target": "ANX", "weight": 0.55},
    {"source": "MDD", "target": "PTSD", "weight": 0.45},
    {"source": "PTSD", "target": "ANX", "weight": 0.50},
    {"source": "ADHD", "target": "SU", "weight": 0.35},
    {"source": "ADHD", "target": "MDD", "weight": 0.30},
    {"source": "SCZ", "target": "XD", "weight": 0.45},
    {"source": "BIP", "target": "XD", "weight": 0.42},
    {"source": "OCD", "target": "ANX", "weight": 0.30},
    {"source": "MDD", "target": "ED", "weight": 0.25}
  ]
}
```

**Step 2: Create `web/components/disorder-network.tsx`**

```tsx
"use client";

import { useEffect, useState, useCallback } from "react";
import dynamic from "next/dynamic";
import { loadNetworkGraph } from "@/lib/data";
import type { NetworkGraph, NetworkNode } from "@/lib/data";

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), { ssr: false });

export function DisorderNetwork() {
  const [graph, setGraph] = useState<NetworkGraph | null>(null);
  const [hovered, setHovered] = useState<string | null>(null);

  useEffect(() => {
    loadNetworkGraph().then(setGraph);
  }, []);

  const nodeCanvasObject = useCallback(
    (node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const { id, sigLoci, color } = node as NetworkNode & { x: number; y: number };
      const size = Math.sqrt(sigLoci || 50) * 0.5;
      const isHighlighted = hovered === null || hovered === id ||
        graph?.links.some(
          (l) =>
            (typeof l.source === "string" ? l.source : (l.source as any).id) === hovered &&
            (typeof l.target === "string" ? l.target : (l.target as any).id) === id ||
            (typeof l.target === "string" ? l.target : (l.target as any).id) === hovered &&
            (typeof l.source === "string" ? l.source : (l.source as any).id) === id
        );

      ctx.globalAlpha = isHighlighted ? 1 : 0.2;

      // Node circle
      ctx.beginPath();
      ctx.arc(node.x, node.y, size, 0, 2 * Math.PI);
      ctx.fillStyle = color;
      ctx.fill();

      // Label
      ctx.font = `${12 / globalScale}px monospace`;
      ctx.textAlign = "center";
      ctx.textBaseline = "top";
      ctx.fillStyle = "#e4e4e7";
      ctx.fillText(id, node.x, node.y + size + 2);

      ctx.globalAlpha = 1;
    },
    [hovered, graph]
  );

  const linkCanvasObject = useCallback(
    (link: any, ctx: CanvasRenderingContext2D) => {
      const sourceId = typeof link.source === "string" ? link.source : link.source.id;
      const targetId = typeof link.target === "string" ? link.target : link.target.id;
      const isHighlighted = hovered === null || hovered === sourceId || hovered === targetId;

      ctx.globalAlpha = isHighlighted ? 0.6 : 0.05;
      ctx.beginPath();
      ctx.moveTo(link.source.x, link.source.y);
      ctx.lineTo(link.target.x, link.target.y);
      ctx.strokeStyle = link.weight > 0 ? "#ef4444" : "#3b82f6";
      ctx.lineWidth = Math.abs(link.weight) * 5;
      ctx.stroke();
      ctx.globalAlpha = 1;
    },
    [hovered]
  );

  if (!graph) {
    return <div className="flex h-96 items-center justify-center text-zinc-500">Loading network data...</div>;
  }

  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-900 overflow-hidden">
      <ForceGraph2D
        graphData={graph}
        width={1100}
        height={600}
        backgroundColor="transparent"
        nodeCanvasObject={nodeCanvasObject}
        linkCanvasObject={linkCanvasObject}
        onNodeHover={(node: any) => setHovered(node?.id || null)}
        cooldownTicks={100}
        linkDirectionalParticles={0}
      />
    </div>
  );
}
```

**Step 3: Create `web/app/network/page.tsx`**

```tsx
import { DisorderNetwork } from "@/components/disorder-network";

export default function NetworkPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-mono text-2xl font-bold">Disorder Network</h1>
        <p className="mt-2 text-sm text-zinc-400">
          Force-directed network of psychiatric disorders. Node size = number of significant loci.
          Edge thickness = genetic correlation strength. Red edges = positive correlation.
          Hover a node to highlight its connections.
        </p>
      </div>
      <DisorderNetwork />
    </div>
  );
}
```

**Step 4: Install react-force-graph**

```bash
cd web && npm install react-force-graph-2d
```

**Step 5: Run dev server and verify**

**Step 6: Commit**

```bash
git add -A
git commit -m "feat: network graph page with force-directed layout and hover highlights"
```

---

### Task 10: Copy Script — Data Pipeline to Frontend

**Files:**
- Create: `scripts/copy-data.sh`

**Step 1: Create the script**

```bash
#!/bin/bash
# Copy processed data snapshots from data/ to web/public/data/
set -e

SRC="$(dirname "$0")/../data"
DEST="$(dirname "$0")/../web/public/data"

if [ ! -d "$SRC" ]; then
  echo "Error: data/ directory not found. Run the notebook first."
  exit 1
fi

mkdir -p "$DEST/manhattan"

cp "$SRC/correlation_matrix.json" "$DEST/"
cp "$SRC/network_graph.json" "$DEST/"
cp "$SRC/metadata.json" "$DEST/"
cp "$SRC/manhattan/"*.json "$DEST/manhattan/"

echo "✓ Data copied to $DEST"
ls -lh "$DEST"
```

**Step 2: Make executable**

```bash
chmod +x scripts/copy-data.sh
```

**Step 3: Commit**

```bash
git add scripts/
git commit -m "feat: data copy script for pipeline → frontend"
```

---

### Task 11: Final Polish and README

**Files:**
- Create: `README.md`

**Step 1: Write README**

```markdown
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

- **Genetic Correlations** — 12×12 heatmap of cross-disorder genetic correlations
- **Manhattan Overlay** — Multi-disorder Manhattan plots, overlay up to 3 disorders
- **Disorder Network** — Force-directed graph showing disorder families by genetic similarity

## Data Source

12 disorder groups from `OpenMed/pgc-*` on HuggingFace:
ADHD, Anxiety, Autism, Bipolar, Depression, Eating Disorders,
OCD/Tourette, Other, PTSD, Schizophrenia, Substance Use, Cross-Disorder.

## Architecture

```
Python pipeline (Polars) → JSON snapshots → Next.js (D3 + Plotly + force-graph)
```
```

**Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add README with quick start guide"
```
