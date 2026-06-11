# ADMET Engine — Factual Inventory

Source-of-truth audit for the Benchside ADMET prediction subsystem, written
against the actual code at `/Users/mac/Desktop/phhh` (commit-time snapshot
2026-06-10). Where a docstring / comment claims a capability that the code
does not back, that mismatch is flagged explicitly. Underclaim chosen over
overclaim throughout.

---

## 1. What the engine actually does

ADMET prediction is a **two-process** architecture inside the Benchside
monorepo:

| Process | File | Role |
|---|---|---|
| Main API (`pharmgpt-api`, port 7860) | `backend/app/services/admet_service.py` | HTTP client + RDKit fallback + report assembly |
| ADMET microservice (`admet-engine`, port 7861) | `backend/admet_engine.py` | FastAPI wrapper around `admet_ai.ADMETModel()` |

The microservice is a thin wrapper. At
`backend/admet_engine.py:24-32` it does
`from admet_ai import ADMETModel; _model = ADMETModel()` and at line 102 calls
`predictions_df = model.predict(request.smiles)`. The actual ML lives inside
the upstream **ADMET-AI package** (Swanson et al. 2024, Bioinformatics),
which under the hood is a **Chemprop v2** directed-message-passing GNN
ensemble trained on Therapeutics Data Commons ADMET datasets. The
microservice itself does no training and adds no models.

The microservice imposes a hard cap of 25 SMILES per call
(`backend/admet_engine.py:97-98`) and self-reports `endpoints: 104` in every
response. **That 104 figure is hard-coded as a pydantic default**
(`PredictResponse.endpoints: int = 104` at line 66) — the engine does not
count the columns it actually returned. Treat 104 as the claimed number of
columns in the upstream ADMET-AI tabular output, not a verified property of
each response.

`ADMETService.predict_admet()` in `backend/app/services/admet_service.py`
implements a **two-tier** fallback chain:

1. **Local engine** (`http://localhost:7861/predict` with
   `include_percentiles=True`) — `admet_service.py:308-338`. Tagged
   `_engine: "admet-ai (Chemprop v2)"`.
2. **RDKit fallback** (`_predict_rdkit_fallback`,
   `admet_service.py:347-435`) — only 14 deterministic descriptors
   (MolWt, logP/Crippen, HBD, HBA, TPSA, rotatable bonds, ring count, heavy
   atoms, QED, stereo centers, num_aromatic_rings, fraction_sp3,
   num_spiro_atoms, num_bridgehead_atoms) plus the Lipinski violation
   counter. `PAINS_alert` and `BRENK_alert` are returned as **hard-coded 0**
   in this branch (`admet_service.py:417-419`) — there is no toxicophore
   SMARTS library in the fallback path. The fallback is documented as such
   and explicitly disclosed in the response (`error: "ADMET-AI engine
   unavailable"`).

There is **no ADMETlab API tier in the working fallback chain.** The only
place an ADMETlab endpoint is hit is the `wash_molecule()` helper
(`admet_service.py:195-226`), which POSTs to
`https://admetmesh.scbdd.com/api/wash` purely for SMILES canonicalisation
and falls back to RDKit canonicalisation. The module docstring still
mentions ADMETlab (`admet_service.py:7-8` says "RDKit physicochemical
fallback" — accurate; older comments referencing ADMETlab as a fallback for
predictions are no longer wired up). The CLAUDE.md claim of a
"local → ADMETlab 3.0 API → RDKit" chain is **partially obsolete** — only
local and RDKit are actually wired in `predict_admet`. The "ADMETlab (API)"
engine label at `admet_service.py:332` is a defensive branch that fires
when the local engine returns the ADMETlab-shaped `data: [...]` envelope —
this is for test-mock compatibility, not real ADMETlab traffic.

### Per-endpoint confidence — what it is and isn't

`_build_confidence_map()` (`admet_service.py:67-83`) reads
`{endpoint}_drugbank_approved_percentile` keys from the upstream prediction
and labels each endpoint `high` (percentile 20-80), `medium` (5-20 or
80-95), or `low` (≤5 or ≥95). The implementation is **explicitly honest**
in its own docstring (line 18): "*honest as a training-data-proximity
confidence proxy — not full Bayesian uncertainty*". This is a position-in-
distribution heuristic, not predictive uncertainty. The deeper per-model
stdev path (Chemprop v2's 5-model internal ensemble) is **not wired in**
either the microservice or the main API. The microservice calls
`ADMETModel().predict()` once and returns a single point estimate.

### Repository hygiene flag

There is a duplicate, **stale** copy of the service at
`backend/app/admet_service.py` (and a sibling `admet_processor.py`). No
import path uses it — every consumer including
`backend/app/core/container.py:91` and
`backend/app/api/v1/endpoints/admet.py:33` imports from
`app.services.admet_service`. The stale copy mentions "46 endpoints" in its
class docstring and should be deleted to prevent confusion. Flagged but not
load-bearing.

### VPS-only parts

The user request mentions `/home/ubuntu/admet_research/` and
`/home/ubuntu/.pm2/...admet-engine` paths on the VPS. **Nothing in the
local repo lets me verify the VPS state** beyond the deploy paths in
`CLAUDE.md` (port 7861, venv `venv_admet`). The local
`backend/admet_engine.py` file IS the source that gets rsynced, so the VPS
process runs the code described above. I cannot confirm or refute
ADMETlab 3.0 fallback existence on the VPS-only side.

---

## 2. Exact endpoint inventory

The platform's *displayed* surface is defined by
`ADMETProcessor.property_groups` at
`backend/app/services/postprocessing/admet_processor.py:99-117`. Counting
the keys deterministically gives **54 endpoints surfaced**, distributed:

| Group | Count | Endpoints |
|---|---|---|
| Physicochemical (neutral) | 9 | `molecular_weight`, `logP`, `hydrogen_bond_donors`, `hydrogen_bond_acceptors`, `tpsa`, `num_rotatable_bonds`, `num_rings`, `num_heavy_atoms`, `stereo_centers` |
| Drug Likeness | 5 | `Lipinski` (benefit), `QED` (benefit), `PAINS_alert`, `BRENK_alert`, `NIH_alert` (alerts) |
| Absorption | 8 | `HIA_Hou` (benefit), `Caco2_Wang` (log; higher=better), `PAMPA_NCATS` (benefit), `Pgp_Broccatelli` (risk), `Solubility_AqSolDB` (log; neutral), `HydrationFreeEnergy_FreeSolv` (neutral), `Lipophilicity_AstraZeneca` (neutral), `Bioavailability_Ma` (benefit) |
| Distribution | 3 | `BBB_Martins` (benefit), `PPBR_AZ` (neutral), `VDss_Lombardo` (neutral) |
| Metabolism | 8 | `CYP1A2/2C9/2C19/2D6/3A4_Veith` inhibition (5 × risk), `CYP2C9/2D6/3A4_Substrate_CarbonMangels` (3 × risk) |
| Excretion | 3 | `Clearance_Hepatocyte_AZ`, `Clearance_Microsome_AZ`, `Half_Life_Obach` (3 × neutral) |
| Toxicity | 18 | `AMES`, `Carcinogens_Lagunin`, `ClinTox`, `DILI`, `hERG`, `Skin_Reaction` (6 × risk) + 12 Tox21 panel (`NR-AR`, `NR-AR-LBD`, `NR-AhR`, `NR-Aromatase`, `NR-ER`, `NR-ER-LBD`, `NR-PPAR-gamma`, `SR-ARE`, `SR-ATAD5`, `SR-HSE`, `SR-MMP`, `SR-p53` — all risk) |
| **Total displayed** | **54** | — |

**The microservice claims 104 endpoints; the UI exposes 54.** The remaining
~50 columns from `admet_ai.ADMETModel.predict()` are either DrugBank
percentile siblings of the above keys (one `_drugbank_approved_percentile`
column per prediction column), `LD50_Zhu`, or non-surfaced supplementary
fields. `LD50_Zhu` does appear in `NEUTRAL_ENDPOINTS`
(`admet_processor.py:550`) but is not in any `property_groups` list, so it
is computed and confidence-mapped but **not shown in the report tables**.
This is a verified inconsistency.

The 12 Tox21 panel members **do not exist as a separate "Tox21" group in
the UI**; they live in the Toxicity group. The `_generate_ai_interpretation`
function at `admet_service.py:754-762` looks for `Tox21_*` prefixed keys,
**but the property_groups list uses `NR-*` / `SR-*` plain prefixes** (no
`Tox21_` prefix). This means the AI interpretation's Tox21 alerts branch
**never fires for live ADMET-AI output** — it would only trigger if the
microservice were to emit `Tox21_NR-AR`-style keys, which it does not.
**Latent bug**, flagged for the paper or for a fix patch.

### Source / direction / value-type matrix

All 54 endpoints below are returned by the **local ADMET-AI microservice**
(Chemprop v2 GNN trained on Therapeutics Data Commons splits) when
available, with **RDKit fallback** providing only the 14 deterministic
physicochemical/QED/structural-count endpoints (no toxicity / Tox21 /
CYP / ADME ML predictions in the fallback path).

| Endpoint(s) | Source | Direction | Value type |
|---|---|---|---|
| 9 physicochemical | ADMET-AI (also RDKit fallback) | neutral | raw scalar |
| `Lipinski` | ADMET-AI / RDKit fallback | benefit (pass count 0-4) | integer 0-4 |
| `QED` | ADMET-AI / RDKit fallback | benefit | [0,1] |
| `PAINS_alert`, `BRENK_alert`, `NIH_alert` | ADMET-AI only (RDKit returns 0) | risk (count) | non-negative integer |
| `HIA_Hou`, `Bioavailability_Ma`, `PAMPA_NCATS`, `BBB_Martins` | ADMET-AI only | benefit | probability [0,1] |
| `Caco2_Wang` | ADMET-AI only | log-scale; higher = better | log cm/s (negative typical) |
| `Solubility_AqSolDB` | ADMET-AI only | neutral (special threshold in interpreter) | log mol/L |
| `Lipophilicity_AstraZeneca`, `HydrationFreeEnergy_FreeSolv` | ADMET-AI only | neutral | continuous |
| `Pgp_Broccatelli` | ADMET-AI only | risk | probability [0,1] |
| `PPBR_AZ` | ADMET-AI only | neutral | % bound |
| `VDss_Lombardo` | ADMET-AI only | neutral | log L/kg |
| `CYP*_Veith` (5) | ADMET-AI only | risk | probability [0,1] |
| `CYP*_Substrate_CarbonMangels` (3) | ADMET-AI only | risk | probability [0,1] |
| `Clearance_Hepatocyte_AZ`, `Clearance_Microsome_AZ` | ADMET-AI only | neutral | log mL/min/kg |
| `Half_Life_Obach` | ADMET-AI only | neutral | hours |
| `AMES`, `DILI`, `ClinTox`, `Carcinogens_Lagunin`, `Skin_Reaction`, `hERG` | ADMET-AI only | risk | probability [0,1] |
| `LD50_Zhu` | ADMET-AI only (not surfaced in UI) | neutral | log(mol/kg) |
| Tox21 panel (12 keys) | ADMET-AI only | risk | probability [0,1] |

CLAUDE.md claims (the rules table) that `Ototoxicity`, `Nephrotoxicity`,
`Neurotoxicity`, `Hematotoxicity` are "ADMETlab 3.0-only" — this is
**accurate in spirit**: a grep across `backend/` shows no code that
predicts or even mentions these endpoints (only one stray reference in
`lead_optimizer/ingest_medchem.py:36` as a keyword for literature
classification). The disclaimer "do not fabricate values" is already
respected — nothing returns these keys.

---

## 3. Synthesis-accessibility metrics

Three names appear in the code; the actual reality is **two scorers behind
a multi-named facade**.

### Real scorers

`backend/app/services/synth_accessibility_service.py` is the live module.
It runs:

- **SYBA** (Voršilák et al. 2020, J. Cheminform.) via the `syba` PyPI
  package (`from syba.syba import SybaClassifier`, line 75). Signed
  continuous score (rough range −50 to +50; positive = easy). Lazy-loaded
  with a `threading.Lock` because the model load is ~60 s. If the import
  fails, `_syba_unavailable` is set and the service silently falls back to
  SAScore only.
- **Ertl SAScore** (Ertl & Schuffenhauer 2009) via `RDConfig.RDContribDir /
  SA_Score / sascorer.py` (line 91). 1-10 continuous. If `sascorer.py` is
  missing it falls back further to a descriptor-based heuristic
  (`_descriptor_based_sa`, line 177) that returns a 1-10 score derived from
  ring count, spiro/bridgehead atoms, stereo centers, MW, and rotatable
  bonds. This descriptor heuristic is **a Benchside-local approximation**,
  not Ertl's published method.

Output schema (line 249-258): `{prediction:0|1, easy_probability,
hard_probability, interpretation, sa_score, syba_score, primary_method,
confidence}`. `confidence` is `high` when SYBA and SAScore both vote the
same direction with clear thresholds; `low` when they actively disagree;
`medium` otherwise.

The `SyntheticAccessibilityService` singleton is exposed under **four
backwards-compat aliases**: `synth_accessibility_predictor`,
`sa_score_predictor`, `simple_gasa_predictor` (`simple_gasa_service.py:24`)
and any historical `SAScorePredictor` usage (line 23). Old callsites
continue to work.

### What about GASA (the graph neural net)?

`backend/app/services/gasa.py` is the original GASA training script
(Yu et al. 2022, J. Chem. Inf. Model.) — a DGL-based graph attention
classifier. It is **a script, not a wired service**. It defines
`def parse()`/`def GASA()` requiring CLI args and is not imported anywhere
in the running service.

`backend/app/services/gasa_service.py` is the Python wrapper. It tries to
import `dgl` (line 53-58) and falls through to the simple service if DGL is
missing. **`dgl` is not installed in the runtime venv** — the wrapper's
own docstring (line 41-46) says "DGL (Deep Graph Library) is required for
the GASA GNN model but is NOT installed on this VPS. Without DGL, the ML
model cannot run."

### Is `gasa_model/` a real checkpoint?

`backend/app/services/gasa_model/gasa.pth` is a real PyTorch checkpoint
file (~1.5 MB, `file` reports it as `data`). The accompanying
`gasa.json` contains the architecture config (`{"num_heads": 6,
"hidden_dim1": 128, "hidden_dim2": 64, "hidden_dim3": 32}`) which matches
the loader at `gasa_service.py:83-90`. So **the checkpoint is real and
loadable** — but only if `dgl` is installed. In production it is dead
weight because DGL isn't there, and the platform uses SYBA + SAScore via
`synth_accessibility_service`.

The honest position for the preprint: GASA is **shipped but not active**;
SYBA is the primary classifier; Ertl SAScore is a continuous co-display
and an automatic fallback. This is consistent with Rule 36 and Rule 37 in
CLAUDE.md, which explicitly designate SYBA as the platform-ratified
synth-accessibility metric and forbid introducing additional metrics
without a corresponding ranking-pipeline rewrite.

### Where surfaced

- **PDF/DOCX report** (`admet_service.py:902-1031`): SYBA-only when
  available; SAScore explicitly labelled "fallback" when SYBA is missing.
- **Frontend `LabDashboard.tsx`** (`GASADisplay` component lines 40-120):
  SYBA bar mapped onto the −50..+50 range with verdict (Easy/Borderline/
  Hard); SAScore shown only as fallback text.
- **Lead-optimizer CSV export** (`backend/app/api/v1/endpoints/
  lead_optimizer.py:700-746`): columns ordered SYBA first, SAScore second,
  GASA last, in line with Rule 36.

---

## 4. Exports (PDF / DOCX / CSV)

### PDF — `xhtml2pdf` (pisa)

Implementation: `admet_service.py:1033-1282`. Uses `xhtml2pdf.pisa` to
render a hand-built HTML template (no Jinja). Layout:

- Header table with `Benchside.png` logo (base64-embedded; falls through
  three filesystem paths including the macOS dev path `/Users/mac/...` —
  fine for dev but a red flag in production hardening).
- Engine banner showing `_engine_version` + `_engine` + confidence-method
  label.
- "Medicinal Chemistry Insights" — `ai_interpretation` rendered inside
  `<div class="insight-box">` after `_convert_unicode_to_html` substitutes
  Unicode sub/superscripts (`₀-₉`, `⁰-⁹`, `⁺`, `⁻`) for `<sub>/<sup>`
  tags (because xhtml2pdf renders those badly).
- Synthetic Accessibility section (SYBA-first per Rule 36).
- Confidence legend.
- 4-column property tables per category (Parameter / Value / Status /
  Confidence).

Bug detected by reading: line 1262 calls `_generate_gasa_html()` *again*
when `synthetic_accessibility` is truthy, after it already rendered the
section into `gasa_html` on line 1078. The rendered template doesn't
interpolate `{gasa_html}` (it's bound but unused) and instead inlines a
second call. Result is functionally correct (the section appears once) but
the variable is dead. Minor; flagged.

### DOCX — `python-docx`

Implementation: `admet_service.py:1284-1425`. Standard `Document()` layout
matching the PDF: header logo, engine banner, AI insights paragraph,
synthetic accessibility section, confidence legend, per-category table with
4 columns. Colour-coded confidence runs using `RGBColor`. No detected
bugs.

### CSV

Two paths:

1. `format_csv_export()` (`admet_processor.py:160-192`) — single-molecule
   vertical CSV: header `Property,Value,Percentile`. Excludes the metadata
   keys (`_engine`, `_source`, `error`, `svg_raw`) and skips percentile
   sibling columns to avoid duplication.
2. `format_batch_csv()` (`admet_processor.py:697-741`) — wide CSV: one row
   per molecule, columns are the union of property keys across the batch.
   Failed molecules get `"FAILED"` in the Engine column with empty
   values. Header uses the `header_labels` map for human-readable column
   names.

Bug detected: `format_csv_export` writes column values with
`str(value).replace(',', ';')` (line 188) to avoid CSV-breaking commas, but
**does not quote fields that already contain commas, semicolons, or
newlines**. Edge case for malformed input (SMILES generally don't contain
commas, so risk is low). Flag for completeness.

---

## 5. Tests

`backend/tests/regression/test_admet_service.py`: 39 test methods (counted
exactly with `grep -c "def test_\|async def test_"`), organised into 8
test classes (length: 706 lines).

**Coverage breakdown:**

- `TestADMETProcessor` (6 tests): import, singleton existence, SVG
  sanitisation (script/XML stripping, responsive class), CSV header,
  red-flag summary (nested format), report markdown structure.
- `TestADMETService` (9 tests): import, lazy init, container DI,
  `wash_molecule` (old + new ADMETlab response shapes + exception
  fallback), `get_svg` (mocked RDKit), `predict_admet` (mocked engine),
  `generate_report`, `export_as_csv`.
- `TestADMETEndpoint` (2 tests): smoke tests confirming `/analyze` and
  `/svg` routes exist on the FastAPI app (`assert response.status_code in
  [200, 401, 422, 400]` — passing on auth-required 401 counts as
  "registered").
- `TestServiceContainerIntegration` (2 tests): `assert ... or True`
  patterns — always pass; effectively dead.
- `TestADMETLocalEngine` (3 tests): `_check_local_engine`,
  `_predict_local`, `_predict_rdkit_fallback`. All HTTP mocked.
- `TestADMETProcessorFlatFormat` (3 tests): flat-shape `summarize_findings`,
  `format_report`, `format_csv_export`.
- `TestDirectionalScoring` (9 tests): the Rule 6 directional-scoring
  matrix. Asserts hERG=0.1 → ✅, Skin_Reaction=0.96 → ❌, HIA=0.99 → ✅,
  Pgp=0.0002 → ✅, mol_weight=130 → empty (neutral), QED=0.51 → ⚠️,
  AMES=0.8 → ❌, AMES=0.1 → ✅, Bioavailability=0.99 → ✅.
- `TestStructuredAndBatchADMET` (3 tests): structured-categories builder,
  batch CSV, batch structured analysis.

**Notable gaps:**

- **No tests for the real ADMET-AI engine.** Every `_predict_local` /
  `predict_admet` test mocks the HTTP layer. There is no integration test
  that exercises the upstream Chemprop v2 model on a real molecule.
- **No tests for SYBA / SAScore / synth_accessibility_service.**
  `gasa_service.py` and `synth_accessibility_service.py` are uncovered
  here (they may have separate suites — verified: a `grep` shows no
  `test_synth*` or `test_gasa*` file in `tests/regression`).
- **No tests for PDF / DOCX export** — the report-generation paths
  (`generate_pdf`, `generate_docx`, ~390 lines combined) are entirely
  uncovered.
- **No tests for the DrugBank-percentile → confidence mapping**
  (`_build_confidence_map`, `_derive_confidence_from_percentile`). Easy to
  add deterministic unit tests; currently uncovered.
- **No test for the Tox21 prefix mismatch** flagged in §2 above.
- **No test for batch SMILES canonicalisation** (`_canonicalize_smiles`)
  or for the "engine drops some canonical SMILES" defence at
  `admet_service.py:542-544`.
- **Two tests in `TestServiceContainerIntegration` are inert** (`assert
  ... or True` always passes); they contribute nothing.

---

## 6. Validation gaps — TDC benchmarking

**None found in the repo.** I searched for `tdc.benchmark`, `admet_group`,
`admet_benchmark`, `tdc_benchmark`, `TDC` (case-insensitive in code, not
docstrings), and `leaderboard` across `backend/` excluding `.venv`. The
only matches are:

- A docstring claim (`admet_service.py:7`) calling ADMET-AI "SOTA on TDC
  leaderboard average". This is a citation to the upstream ADMET-AI paper's
  published claim; **not a Benchside-run benchmark**.
- One unrelated grep hit for "benchmark" in `multi_provider.py` re LLM TTFT
  benchmarks.
- `download_benchmark_reports.py` under `scripts/` — unrelated, it's about
  literature reports.

There is no `evaluate.py`, no held-out set, no comparison vs. ADMETlab 3.0
or ADMETboost or Deep Purpose, no PR curve script, no test against TDC's
`group.get('benchmark')` API. The platform inherits whatever benchmark
performance ADMET-AI claims upstream (Swanson et al. 2024). For the paper,
the honest framing is: **"Benchside surfaces upstream ADMET-AI predictions;
upstream model accuracy is taken as published. No in-house TDC benchmark
re-run was performed."**

---

## 7. Tox21 panel + DrugBank percentile — real or hardcoded?

**Tox21:** The 12 panel members are real predictions emitted by the
ADMET-AI Chemprop v2 ensemble (the upstream package ships pre-trained
heads for the Tox21 challenge dataset). Benchside does not retrain them;
the per-endpoint predictions are passed through, and the directional
scorer at `admet_processor.py:530-537` puts them in `RISK_ENDPOINTS`. No
hardcoded values.

**DrugBank percentile:** Computed inside the upstream `admet_ai` package,
not in Benchside. The microservice passes `include_percentiles=True` and
extracts whatever `{endpoint}_drugbank_approved_percentile` columns
ADMET-AI emits. **Benchside does not compute the percentile reference
distribution itself** — it consumes the upstream's bundled DrugBank-
approved-drugs reference set (which ADMET-AI ships internally; this is
how the published ADMET-AI app surfaces "percentile vs. approved drugs"
columns). The Benchside confidence-label mapping (`high` 20-80, `medium`
5-20 or 80-95, `low` ≤5 or ≥95) IS Benchside code
(`admet_service.py:54-64`) and is honest about being a heuristic, not a
calibrated probability.

So: percentiles are real but **inherited**, not Benchside-derived;
percentile-to-confidence label is Benchside's heuristic; no calibration
against a held-out set has been done.

---

## 8. Lab UI integration

Three frontend files drive the experience:

- `frontend/src/components/lab/LabDashboard.tsx` (851 lines). Owns input
  modes (single SMILES / batch / SDF), pagination (page size 50, max 100
  per backend cap), drug-suggestion refresh from `drugPool.ts`, and result
  rendering. Calls:
  - `POST /api/v1/admet/analyze` for single molecule.
  - `POST /api/v1/admet/batch` (form-data with `smiles_list` JSON or
    `file` SDF) for batch + SDF.
  - Hits 4 export endpoints (`/export`, `/export/pdf`, `/export/docx`,
    `/export/batch` POST).
  Renders `GASADisplay` (SYBA-only with SAScore-fallback panel; see §3) and
  paginated grids of `ADMETPropertyCard`.
- `frontend/src/components/lab/ADMETPropertyCard.tsx` (102 lines).
  Consumes the `categories` array from the backend; renders one card per
  category. Each property row shows `value{unit}`, `ConfidenceBadge`
  (high/medium/low → ✓ / ~ / ⚠ with tooltip explaining "training-data
  proximity"), and a `StatusBadge` (success/warning/danger/neutral).
- `frontend/src/constants/drugPool.ts` (182 lines, **130 drug entries**).
  Each entry is `{name, smiles, year?, class}`. Used by
  `getRandomDrugs(4)` to populate the "Try one of these" cards. The list
  is FDA-approved drugs + common investigational compounds. The CLAUDE.md
  claim of "500+ drug suggestions" is **overstated** — actual count is
  130. The file's own header docstring also says "500+" but `grep -c "{
  name"` returns 130. The "SMILES only, no peptides" discipline is
  documented (line 11) and several entries have valid SMILES strings (I
  did not validate every one with RDKit, but the architectural choice is
  clear).

The UI does not display the raw `_engine` / `_engine_version` /
`_confidence_method` metadata to users; it surfaces the per-endpoint
confidence badge with a hover tooltip explaining the proximity heuristic.
The export buttons download the heavyweight reports (PDF / DOCX) which DO
include the engine banner and the confidence legend.

---

## 9. Rules 6, 25, 28 — verification

### Rule 6 — ADMET directional scoring

**Implemented.** `ADMETProcessor.get_interpretation()`
(`admet_processor.py:502-618`) partitions endpoints into `RISK_ENDPOINTS`
(low=green, high=red), `BENEFIT_ENDPOINTS` (high=green, low=red),
`NEUTRAL_ENDPOINTS` (returns ""), `ALERT_ENDPOINTS` (count-based), and two
special cases (`Caco2_Wang` log-scale, `Solubility_AqSolDB` log-scale,
`Lipinski` pass-count). 9 unit tests in `TestDirectionalScoring` lock in
the correct direction for hERG, Skin_Reaction, HIA, Pgp, MW, QED, AMES
(low and high), Bioavailability. **Rule 6 is real, tested, and lives in
exactly the single file CLAUDE.md says it does.**

### Rule 25 — PDF URL validation before display

Not applicable to ADMET — Rule 25 is about Semantic Scholar PDF URLs in
the literature/RAG path, not ADMET. ADMET service does not validate any
external PDFs. (Note: the PDF generated **by** ADMET via xhtml2pdf is a
separate concern — it's a server-rendered output, not a fetched external
PDF.)

### Rule 28 — ADMET engine specifics

CLAUDE.md says: "`admet-engine` lives at `/home/ubuntu/admet_research/`
with venv `venv_admet`. Verify `venv_admet/bin/activate` exists before
restarting." This is a **VPS-side runbook claim**. I cannot verify it from
the local repo. The local `backend/admet_engine.py` is consistent with
the claim (it's the file rsynced to the VPS to run as PM2 `admet-engine`,
port 7861). The microservice's PM2 launch command per Rule 27 would need
to be `pm2 start "uvicorn admet_engine:app --host 0.0.0.0 --port 7861"`
or similar; nothing in the local repo confirms the exact PM2 ecosystem
file. Flag: VPS-side, unverifiable here.

---

## What's solid / What's partial / What's missing

### Solid

- **Two-process architecture:** main API + `admet-engine` microservice on
  port 7861, both code-resident and consistent.
- **ADMET-AI / Chemprop v2 integration via thin FastAPI wrapper** —
  faithful pass-through, no shadow predictions.
- **RDKit fallback path** for the 14 deterministic physicochemical /
  drug-likeness descriptors, with honest disclosure when the ML engine is
  down.
- **Rule 6 directional scoring** — implemented exactly where claimed,
  with 9 locked-in unit tests.
- **SYBA primary + Ertl SAScore fallback** synth-accessibility scoring,
  with a real confidence ladder driven by SYBA/SAScore agreement.
- **Per-endpoint confidence map** that is honest in its own docstring
  about being a training-data-proximity proxy, not Bayesian uncertainty.
- **PDF + DOCX + CSV exports** all wired through, with consistent SYBA-
  first surfacing of synth accessibility.
- **Frontend confidence-badge UX** with a tooltip that explains the
  proximity-based meaning.

### Partial

- **104 endpoints microservice vs. 54 surfaced UI endpoints.** The 50-
  endpoint gap is mostly `_drugbank_approved_percentile` siblings, but
  `LD50_Zhu` is computed and confidence-mapped yet never displayed —
  inconsistency, not a critical bug.
- **CLAUDE.md "ADMETlab 3.0 API fallback" claim** is only true for the
  `wash_molecule()` helper; the `predict_admet()` chain does **not** call
  ADMETlab. Doc-vs-code drift; should be fixed in the rules table.
- **drugPool.ts claims "500+" but holds 130 entries.** Docstring + header
  comment both overstate. Cosmetic but worth correcting.
- **Tox21 prefix mismatch in the AI-interpretation branch** — the code
  looks for `Tox21_*` keys that ADMET-AI doesn't emit (it emits `NR-*` /
  `SR-*` directly). The AI interpretation's "Tox21 pathway alerts" branch
  is therefore dead code with current upstream output. Latent bug.
- **GASA GNN (`gasa_model/gasa.pth`) is a real checkpoint but inert in
  production** because `dgl` is not installed. The DGL-based service
  silently falls through to SYBA+SAScore. Not a bug — Rule 36 makes SYBA
  the canonical metric — but the dead checkpoint inflates the repo and
  should either be removed or accompanied by a `DGL_OPTIONAL.md`
  explaining the situation.
- **Repository hygiene:** stale duplicate `backend/app/admet_service.py`
  and `backend/app/admet_processor.py` are not imported anywhere but still
  exist; they reference an outdated "46 endpoints" claim and should be
  deleted.
- **Test coverage gaps:** no end-to-end test against the real engine, no
  test for the synth-accessibility service, no test for PDF/DOCX export,
  no test for batch canonicalisation defence, two effectively-inert tests
  in `TestServiceContainerIntegration`.

### Missing

- **No TDC benchmark harness.** The platform inherits upstream ADMET-AI's
  published accuracy and does not re-validate against TDC's ADMET
  Benchmark Group. No evaluation script, no leaderboard JSON, no
  comparison vs. competitor tools.
- **No predictive uncertainty.** Chemprop v2's 5-model ensemble stdev is
  not surfaced; the platform exposes single-point predictions plus a
  position-in-distribution heuristic labelled "confidence". The
  docstring explicitly flags this as v2.1 future work
  (`admet_service.py:18-21`).
- **No calibration against a held-out set** for the percentile-to-
  confidence labels (the 20/80 and 5/95 thresholds were chosen by
  convention, not optimised).
- **No ototoxicity / nephrotoxicity / neurotoxicity / hematotoxicity
  predictions** anywhere in code. The CLAUDE.md rules table correctly
  lists these as "ADMETlab 3.0-only — do not fabricate"; the code
  respects that and does not output them. Flag only because the rules
  table does mention them — they appear nowhere in the real engine.
- **No PAINS/BRENK detection in RDKit fallback path.** When the ML engine
  is down, structural alerts are hard-coded to 0 — a reasonable
  schema-preservation choice, but the user should know the fallback is
  silent on substructure alerts.
- **No VPS-side state I can verify from the local repo** — Rule 28's
  `/home/ubuntu/admet_research/venv_admet` claim and the PM2 launch
  command are runbook documentation only.

---

## Key source files

- `/Users/mac/Desktop/phhh/backend/app/services/admet_service.py` (1625 lines)
- `/Users/mac/Desktop/phhh/backend/app/services/postprocessing/admet_processor.py` (745 lines)
- `/Users/mac/Desktop/phhh/backend/app/api/v1/endpoints/admet.py` (418 lines)
- `/Users/mac/Desktop/phhh/backend/admet_engine.py` (172 lines — microservice)
- `/Users/mac/Desktop/phhh/backend/app/services/synth_accessibility_service.py` (268 lines — SYBA + SAScore)
- `/Users/mac/Desktop/phhh/backend/app/services/gasa_service.py` (195 lines — DGL/GASA wrapper, currently inert)
- `/Users/mac/Desktop/phhh/backend/app/services/simple_gasa_service.py` (31 lines — alias shim)
- `/Users/mac/Desktop/phhh/backend/app/services/gasa_model/gasa.pth` + `gasa.json` (1.5 MB checkpoint, unused in production)
- `/Users/mac/Desktop/phhh/backend/tests/regression/test_admet_service.py` (706 lines, 39 tests)
- `/Users/mac/Desktop/phhh/frontend/src/components/lab/LabDashboard.tsx` (851 lines)
- `/Users/mac/Desktop/phhh/frontend/src/components/lab/ADMETPropertyCard.tsx` (102 lines)
- `/Users/mac/Desktop/phhh/frontend/src/constants/drugPool.ts` (182 lines, 130 entries)

Stale duplicates flagged for deletion:
- `/Users/mac/Desktop/phhh/backend/app/admet_service.py`
- `/Users/mac/Desktop/phhh/backend/app/admet_processor.py`
