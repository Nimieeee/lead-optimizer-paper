# Benchside Lead-Optimization Workbench — Reproducibility

This directory contains everything needed to reproduce the figures and tables
in the paper:

```
paper/
├── CODEBASE_NOTES.md          # Master codebase inventory (audit of what's in code)
├── SCOPE_RECOMMENDATION.md    # Phase 2 paper-scope reasoning
├── PHASE3_PLAN.md             # Experiment design (sources, methods, hardware)
├── manuscript.md              # The preprint itself (Phase 5)
├── references.bib             # BibTeX (Phase 5)
├── CLAIMS_EVIDENCE.md         # Each claim mapped to a figure/table/script
├── notes/0[1-5]_*.md          # Component-level Phase 1 detail notes
├── experiments/
│   ├── exp1_mmp_recovery/     # Matched-molecular-pair recovery (pilot + ChEMBL)
│   ├── exp2_scaffold_alerts/  # Scaffold preservation + structural-alert audit
│   ├── exp3_vision_consistency/# Vision Agent self-consistency on a fixed LID
│   └── exp4_case_study/       # DYRK1A + Linezolid end-to-end pipeline runs
└── figures/
    ├── fig1_lead_optimizer_pipeline.html  # System architecture (hand-coded)
    ├── fig2_mmp_recovery.py               # Renders Figure 2 from Exp 1 results
    ├── fig3_scaffold_alerts.py            # Renders Figure 3 from Exp 2 results
    ├── fig5_case_study.py                 # Renders Figure 4 from Exp 4 results
    ├── fig4_vision_consistency.py         # Renders Figure 5 from Exp 3 results
    ├── _style.py                          # Shared matplotlib style
    └── out/                               # Generated PDFs + PNGs
```

## Software environment

### Local Mac (Experiments 1, 2; figures)
```bash
cd paper
uv venv .venv --python 3.11
uv pip install --python .venv/bin/python rdkit pandas numpy matplotlib seaborn tqdm requests mmpdb
```
RDKit version pinned by the lockfile; recommended `rdkit>=2024.03`.

### VPS (Experiments 3, 4)
Production deploy under `/var/www/benchside-backend/backend/` with its own venv at
`backend/.venv/`. The drivers import directly from the production code path
(`PYTHONPATH=/var/www/benchside-backend/backend`) and reuse the production
`ServiceContainer` initialised against the production Supabase. No HTTP layer.

## Reproducing each result

### Figure 2 — MMP recovery (Experiment 1)

**Pilot, hand-curated 30 pairs (1 minute):**
```bash
paper/.venv/bin/python paper/experiments/exp1_mmp_recovery/run.py \
    --pairs paper/experiments/exp1_mmp_recovery/data/pilot_pairs.csv \
    --output paper/experiments/exp1_mmp_recovery/results/pilot
paper/.venv/bin/python paper/figures/fig2_mmp_recovery.py
```

**Full set, ChEMBL-derived MMPs via mmpdb (2-4 hours):**
```bash
# Download ChEMBL release SMI subset
cd paper/experiments/exp1_mmp_recovery/data/chembl
curl -O https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/latest/chembl_37_chemreps.txt.gz
gunzip chembl_37_chemreps.txt.gz

# Build MMP set
mmpdb fragment chembl_37_chemreps.txt --output chembl37.fragments
mmpdb index chembl37.fragments --output chembl37.mmpdb

# Filter to single-edit, drug-like pairs
paper/.venv/bin/python paper/experiments/exp1_mmp_recovery/build_chembl_pairs.py \
    --mmpdb chembl37.mmpdb --output paper/experiments/exp1_mmp_recovery/data/chembl_pairs.csv \
    --max-pairs 2000

# Run recovery
paper/.venv/bin/python paper/experiments/exp1_mmp_recovery/run.py \
    --pairs paper/experiments/exp1_mmp_recovery/data/chembl_pairs.csv \
    --output paper/experiments/exp1_mmp_recovery/results/chembl_full
```

### Figure 3 — Scaffold preservation + structural alerts (Experiment 2)
```bash
paper/.venv/bin/python paper/experiments/exp2_scaffold_alerts/extract_seeds.py
paper/.venv/bin/python paper/experiments/exp2_scaffold_alerts/run.py \
    --seeds paper/experiments/exp2_scaffold_alerts/data/seed_leads.csv \
    --output paper/experiments/exp2_scaffold_alerts/results/drugpool_129
paper/.venv/bin/python paper/figures/fig3_scaffold_alerts.py
```
Runtime: ~1 minute on a modern laptop (7-way multiprocessing).

### Figure 5 — Case study (Experiment 4) — VPS-bound

Requires production credentials (Supabase + provider API keys via the VPS
`.env`) — cannot be reproduced from local source alone.

```bash
# Sync driver and inputs to VPS
rsync -avz -e "ssh -i ~/.ssh/id_deploy_contabo" \
    paper/experiments/exp4_case_study/ ubuntu@<vps>:/tmp/exp4_case_study/

# Run end-to-end (≈10-30 minutes total for 2 cases)
ssh -i ~/.ssh/id_deploy_contabo ubuntu@<vps> '
    cd /var/www/benchside-backend/backend && source .venv/bin/activate &&
    PYTHONPATH=/var/www/benchside-backend/backend python3 \
        /tmp/exp4_case_study/run_on_vps.py \
        --cases /tmp/exp4_case_study/data/cases.csv \
        --output /tmp/exp4_case_study/results'

# Pull results
rsync -avz -e "ssh -i ~/.ssh/id_deploy_contabo" \
    ubuntu@<vps>:/tmp/exp4_case_study/results/ \
    paper/experiments/exp4_case_study/results/
paper/.venv/bin/python paper/figures/fig5_case_study.py
```

### Figure 4 — Vision Agent self-consistency (Experiment 3) — VPS-bound

Eight independent Vision Agent runs on the same DYRK1A LID. Reports pairwise
Jaccard similarity of restricted-atom sets, consensus, and validator-drop rates.

```bash
rsync -avz -e "ssh -i ~/.ssh/id_deploy_contabo" \
    paper/experiments/exp3_vision_consistency/ ubuntu@<vps>:/tmp/exp3_vision_consistency/
ssh -i ~/.ssh/id_deploy_contabo ubuntu@<vps> '
    cd /var/www/benchside-backend/backend && source .venv/bin/activate &&
    PYTHONPATH=/var/www/benchside-backend/backend python3 \
        /tmp/exp3_vision_consistency/run_on_vps.py \
        --lid /tmp/exp3_vision_consistency/data/dyrk1a_25014_LID.png \
        --smiles "COc1ccc2c(c1)-c1cc(CO)ccc1C(C)(C)O2" \
        --n-runs 8 \
        --output /tmp/exp3_vision_consistency/results'
rsync -avz -e "ssh -i ~/.ssh/id_deploy_contabo" \
    ubuntu@<vps>:/tmp/exp3_vision_consistency/results/ \
    paper/experiments/exp3_vision_consistency/results/
paper/.venv/bin/python paper/figures/fig4_vision_consistency.py
```

## Manifest files

Every results directory contains a `manifest.json` recording the git SHA, RDKit
version, Python version, platform, SMIRKS library SHA-256 + entry count, and
input file SHA-256. Reproducing a figure with a different manifest is not the
same result — the manifest is what makes a number citable.

## The claims/evidence map

`CLAIMS_EVIDENCE.md` maps every quantitative claim in the manuscript to the
exact figure, table, or `summary.json` field that supports it. Reviewers and
authors should treat that document as the index of provenance.

## Citation

When citing data products from this paper, please cite both the preprint and
the archived code release (Zenodo DOI to be assigned at submission time).
