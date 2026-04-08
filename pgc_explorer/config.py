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
    DisorderDataset("ADHD", "OpenMed/pgc-adhd", "adhd2022", "#e74c3c"),
    DisorderDataset("Anxiety", "OpenMed/pgc-anxiety", "anx2026", "#e67e22"),
    DisorderDataset("Autism", "OpenMed/pgc-autism", "asd2019", "#f1c40f"),
    DisorderDataset("Bipolar", "OpenMed/pgc-bipolar", "bip2024", "#2ecc71"),
    DisorderDataset("Depression", "OpenMed/pgc-mdd", "mdd2018", "#3498db"),
    DisorderDataset("Substance Use", "OpenMed/pgc-substance-use", "SUD2023", "#9b59b6"),
    DisorderDataset("Schizophrenia", "OpenMed/pgc-schizophrenia", "scz2022", "#1abc9c"),
    DisorderDataset("PTSD", "OpenMed/pgc-ptsd", "ptsd2019", "#e91e63"),
    DisorderDataset("OCD/Tourette", "OpenMed/pgc-ocd-tourette", "ocd2025", "#00bcd4"),
    DisorderDataset("Eating Disorders", "OpenMed/pgc-eating-disorders", "an2017", "#ff9800"),
    DisorderDataset("Cross-Disorder", "OpenMed/pgc-cross-disorder", "cdg2019", "#607d8b"),
    DisorderDataset("Other", "OpenMed/pgc-other", "bpd2025", "#795548"),
]

# Column name normalization map.
# Different publications use different column names for the same data.
# Keys are canonical names, values are possible source column names (tried in order).
COLUMN_MAP: dict[str, list[str]] = {
    "snp": ["SNP", "ID", "SNPID", "MarkerName", "rsid", "variant_id", "snpid"],
    "chr": ["CHR", "CHROM", "Chromosome", "chromosome", "chr", "hm_chrom", "#CHROM", "hg18chr"],
    "bp": ["BP", "POS", "Position", "position", "pos", "base_pair_location", "hm_pos"],
    "a1": ["A1", "ALT", "effect_allele", "allele1", "Allele1"],
    "a2": ["A2", "REF", "other_allele", "allele2", "Allele2"],
    "beta": ["BETA", "beta", "Effect", "b", "logOR", "EFFECT"],
    "or_val": ["OR", "or"],
    "se": ["SE", "StdErr", "se", "standard_error"],
    "p": ["P", "Pval", "PVAL", "p_value", "P-value", "pval", "PVALUE", "p-value"],
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
