# Experiment 1, MMP recovery rate

**Question:** Given a matched molecular pair `(A, B)` where `B` is a documented improving analog of `A`, does the platform's 479-entry SMIRKS library applied to `A` recover `B` among the generated analogs, and at what rank?

**Method:** Pure RDKit. No LLM in the loop. The Vision Agent and Optimization Agent are stubbed to "every group is TARGET" so this experiment isolates the SMIRKS engine and the structural deduplication. The chemistry validator and soft Murcko gate are not exercised here (they sit *after* the SMIRKS step and act on the generated analogs, see Experiment 2 for their effect).

**Metric:** Recall@K for K ∈ {1, 5, 10, 50, 100, 500}, by Tanimoto-to-B rank (Morgan/ECFP4, radius 2, 2048 bits). Exact canonical-SMILES match required for "recovery."

## Reproduce

```bash
# from repo root, with paper/.venv/ already set up (see paper/PHASE3_PLAN.md §Environment)
paper/.venv/bin/python paper/experiments/exp1_mmp_recovery/run.py \
    --pairs paper/experiments/exp1_mmp_recovery/data/pilot_pairs.csv \
    --output paper/experiments/exp1_mmp_recovery/results/pilot
```

## Outputs

Under `results/<run-name>/`:
- `per_pair.csv`, one row per MMP, with B-recovered flag, B's rank by Tanimoto, top-10 Tanimoto mean, and the SMIRKS IDs (if any) that produced B exactly.
- `summary.json`, aggregate metrics: n_pairs, n_B_recovered_exact, recall@K, mean analogs, mean best Tanimoto, top-20 SMIRKS recovery counts, total runtime.
- `manifest.json`, git SHA, dirty flag, RDKit version, Python version, platform, SMIRKS library SHA-256 and entry count, pairs-input SHA-256.

## Data sources

- **Pilot set** (`data/pilot_pairs.csv`, 30 pairs): hand-curated documented bioisosteric or single-edit MMPs from the medicinal chemistry literature (acid→tetrazole, OMe→OCF3, halogen swaps, ring isomer swaps, etc.). Chosen to span the library's category prefixes (ACID, AMINE, RING, HALO, SLFA, NIT). Intentionally biased toward transformations the library is designed to perform, this is the upper-bound test for the library's coverage on its native domain.
- **Full set** (planned): MMPDB-derived ChEMBL-32 pairs (~2000 pairs after filtering for ΔLogP / Δactivity threshold and 1–2 edit distance). Reproducible with `mmpdb fragment` + `mmpdb index` (see Phase 3 plan).

## What the pilot does and does not tell us

**Does tell:** whether the SMIRKS engine mechanically reproduces documented single-edit transformations when the transformation type is in the library.
**Does not tell:** how the engine performs on the long tail of MMPs the library was not designed for. That is what the ChEMBL-derived full set is for.

Both numbers go in the paper. A high pilot recovery is necessary; a non-trivial ChEMBL-set recovery is what makes the contribution stand on its own.

## Negative-result protocol

If pilot recovery@100 < 30%, the result is honestly reported and triggers a SMIRKS-library audit (which entries fail to fire on their target substrates? RDKit reaction syntax issues? sanitation failures?). Not a fix-the-numbers exercise. The paper survives a negative pilot; it does not survive an over-claimed pilot.
