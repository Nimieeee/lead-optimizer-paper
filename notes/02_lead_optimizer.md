# Lead Optimization Workbench, Factual Inventory

Source-of-truth audit of `backend/app/services/lead_optimizer/` and the
Studio frontend at `frontend/src/app/(hub)/studio/page.tsx`, current as of
commit `9ef973c` (master). Every claim cites a `path:line`. Discrepancies
between CLAUDE.md / docstrings / prompts and what the code actually does
are called out explicitly.

---

## 1. Pipeline stages

The orchestrator (`backend/app/services/lead_optimizer/orchestrator.py`)
runs a single async function `run_lead_optimization` that drives the
following stages in order. Stage numbers are the ones written in the
code's own comments; "real" means the code path is wired and unguarded.

| # | Stage (orchestrator label)   | Backing module                                      | Status |
|---|------------------------------|-----------------------------------------------------|--------|
| 1.5 | RDKit pre-scan              | `rdkit_engine.pre_scan_molecule` (`orchestrator.py:239-248`) | Real |
| 1 | Vision Agent                 | `agents/vision_agent.run_vision_agent` (`orchestrator.py:255-274`) | Real, LID-gated |
| 2 | Vision user-review pause     | `handle_vision_review` (`orchestrator.py:25-46`)    | Real, only when `task_id` and LID both present |
| 3 | SMARTS Builder               | `rdkit_engine.build_smarts_from_groups` (`orchestrator.py:309-314`) | Real |
| 4 | ADMET profile of lead        | `profiler.profile_lead_compound` (`orchestrator.py:322`) | Real |
| 5 | Context Analyzer (LLM)       | `context_analyzer.analyze_project_context` (`orchestrator.py:374`) | Real |
| 6 | Optimization Agent (LLM)     | `agents/optimization_agent.run_optimization_agent` (`orchestrator.py:396`) | Real |
| 7 | Validate strategies (Critic) | `orchestrator.validate_strategies` (`orchestrator.py:405`) | Real |
| – | Fallback strategy expansion  | `orchestrator._fallback_strategies` (`orchestrator.py:420`) | Real, ceilings 20/40 |
| 8 | Permutation (combinatorial)  | `permutation.generate_combinatorial_library` (`orchestrator.py:494-499`) | Real, hard cap 100 000 |
| 9 | Pre-filter (Lipinski + PAINS + Brenk + Glaxo) | `filtering.batch_prefilter` (`orchestrator.py:518`) | Real |
| 10 | ADMET screen                | `orchestrator.batch_admet_screen` (`orchestrator.py:538`) | Real, batched 50 |
| 10.5 | SYBA per-analog          | `simple_gasa_service.simple_gasa_predictor` (`orchestrator.py:546-584`) | Real |
| 11 | Pareto ranking + diversity   | `ranking.rank_analogs` + `diversity.select_diverse_representatives` (`orchestrator.py:610-619`) | Real |
| 12 | Report                       | `report_generator.generate_report` (`orchestrator.py:638-647`) | Real, returns PDF/HTML/SDF paths |

What CLAUDE.md called *"Pre-scan → Vision → SMARTS → ADMET → Context →
Optimization → Validate → Permutation → Pre-filter → ADMET screen →
GASA/SYBA → Ranking → Report"* matches the orchestrator one-for-one.
There is no separate "GASA" stage; SYBA is folded into stage 10.5 and
again read inside `ranking._get_synth_difficulty` (`ranking.py:24-44`).

The frontend `PipelineMonitor` (`frontend/src/components/lead/PipelineMonitor.tsx:12-34`)
displays a 10-step strip (`vision, vision_review, admet_profile,
context_analysis, optimization, permutation, filtering, admet_screen,
ranking, report`); when no LID is uploaded the first two steps are
hidden, matching the orchestrator's no-LID branch
(`orchestrator.py:275-298`).

---

## 2. Vision Agent (`backend/app/services/lead_optimizer/agents/vision_agent.py`)

### Provider chain

The advertised chain is in the module docstring at lines 14-21. Actual
runtime tier order (`vision_agent.py:459-511`):

| Tier | Provider               | Model env var / constant            | Wired? |
|------|------------------------|--------------------------------------|--------|
| 1    | Kimi K2.6 via OpenCode Go OAI-compat | `KIMI_VISION_MODEL` (default `"kimi-k2.6"`) (`vision_agent.py:34`) | **Active by default** |
| 1b   | MiniMax M3 via OpenCode Go Anthropic-compat | `MINIMAX_VISION_MODEL` (default `""`) (`vision_agent.py:29`) | **Dead by default**, disabled per comment at `vision_agent.py:23-28` because M3 emits only `thinking` blocks under normal budgets and M2.5/M2.7 are text-only |
| 2    | Pixtral Large via Mistral | `PIXTRAL_MODEL = "pixtral-large-latest"` (`vision_agent.py:35`) | **Active** |
| 3    | Groq Llama 4 Scout 17B | `GROQ_SCOUT_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"` (`vision_agent.py:36`) | **Active** |

The "Llama 4 Maverick 17B-128e" upgrade described in the 2026-06-05
CLAUDE.md row is **not present in the live code**, the constant on
`vision_agent.py:36` is still Scout 17B-16e. Maverick is mentioned
nowhere in `agents/vision_agent.py`.

Each tier retries up to `max_retries=3` (`run_vision_agent` arg, default
3 at `vision_agent.py:393`). All tiers return JSON via `_extract_json_object`
(`vision_agent.py:47-96`) which strips markdown fences and brace-scans
for the outer object, Kimi's heavy-reasoning fallback reads
`message.reasoning_content` when `message.content` is empty
(`vision_agent.py:321-329`).

### Image input flow

- Endpoint: `POST /lead-optimizer/optimize` (`api/v1/endpoints/lead_optimizer.py:192-354`)
  accepts a multipart `UploadFile` `lid_diagram` plus `lead_smiles` form
  field. The diagram is base64-encoded and stored in
  `optimization_tasks.lid_diagram_base64` (`lead_optimizer.py:213-232`).
- The orchestrator decodes back to bytes (via the worker
  `worker.py:13-17`), then `run_vision_agent` re-base64s for each
  provider (`vision_agent.py:418`).
- Provider payloads:
  - OpenCode Go Anthropic-compat: `{type: image, source: {type:
    base64, media_type: image/png, data: …}}` (`vision_agent.py:136-144`).
  - Mistral / Groq / Kimi OAI-compat: `{type: image_url, image_url:
    {url: "data:image/png;base64,…"}}` (`vision_agent.py:248-251`).

**There is no LID parser**, the diagram is passed as a raw PNG-encoded
image to a multimodal LLM. The "parser" is the LLM itself; the only
deterministic structure on the image side is the textual list of
RDKit-detected groups appended to the prompt
(`vision_agent.py:424-444`). No symbolic / vector recognition of arrows
or residue labels exists.

### Schema (multi-residue support)

`FunctionalGroupInteraction` (`schemas.py:15-46`) carries:

- `residues: list[str]`, authoritative
- `residue: Optional[str]`, legacy back-compat shim, equals `residues[0]`
- `interaction_types: list[InteractionType]`, authoritative
- `interaction_type: InteractionType`, legacy shim
- `atom_indices: list[int]`, RDKit atom indices for the matched instance
- A `model_validator(mode='after')` (`schemas.py:35-46`) cross-fills the
  two pairs of fields so old callers don't break.

`VisionAgentOutput` (`schemas.py:54-76`) also carries
`scaffold_atoms: list[int]` (vision-flagged, merged downstream with the
Murcko-derived set, see Section 4) and the (now vestigial)
`structural_core_groups`.

Round-trip and back-fill behaviour are exercised by three regression
tests (`test_lead_optimizer.py:127-194`).

### Chemistry validator

Lives in `backend/app/services/lead_optimizer/chemistry_validator.py`:

- Allowlists keyed by interaction type:
  `H_BOND_DONORS`, `H_BOND_ACCEPTORS`, `PI_STACK_GROUPS`,
  `HYDROPHOBIC_GROUPS`, `SALT_BRIDGE_GROUPS`, `CATION_PI_GROUPS`
  (`chemistry_validator.py:19-132`).
- `INTERACTION_ALLOWED` dict maps interaction string → allowlist
  (`chemistry_validator.py:134-141`).
- `normalize_group_name` (`chemistry_validator.py:147-164`) lowercases,
  underscores, strips noise suffixes (`_group`, `_moiety`, etc.).
- `is_valid_interaction(group, interaction_type)` returns `False`
  closed if either side is unknown (`chemistry_validator.py:167-178`).

Wiring: `vision_agent.py` imports `is_valid_interaction` and
`normalize_group_name` at line 11, then `_filter_restricted`
(`vision_agent.py:557-594`) loops every restricted entry, validating
multi-residue payloads index-by-index, a partial match keeps only the
valid subset (`vision_agent.py:572-586`). `_filter_target`
(`vision_agent.py:596-607`) drops only hallucinated `group_name`s; it
does **not** apply interaction-type validity (targets don't carry one).
Seven regression tests (`test_lead_optimizer.py:308-377`) exercise the
allowlists.

### Two-category vs three-category classification

Verified: **STRUCTURAL_CORE is gone at the policy level but the field
still exists for schema back-compat.**

- The prompt at `prompts.py:6-189` lists *only* `RESTRICTED` and
  `TARGET` ("classify it into EXACTLY ONE of TWO categories"
  `prompts.py:12`).
- The JSON schema example at `prompts.py:156-187` has no
  `structural_core_groups` key.
- `VisionAgentOutput.structural_core_groups` still exists in the
  schema (`schemas.py:73`) and `run_vision_agent` parses
  `parsed.get("structural_core_groups", [])` and **merges it into
  `target`** before returning (`vision_agent.py:526-530`):
  `structural_core` is set to `[]` and any legacy payload is folded
  back into TARGET.
- `build_smarts_from_groups` reads `vision_output.structural_core_groups`
  and routes every entry to `target_parts`
  (`rdkit_engine.py:503-520`).
- The frontend page at `frontend/src/app/(hub)/studio/page.tsx:61-66`
  reads any legacy `structural_core_groups` from old vision payloads,
  appends them to the target list, and never renders the third panel.

So the user's correction is in fact implemented as a runtime *merge*,
not a code deletion, the field is preserved purely so older saved
tasks keep deserialising.

---

## 3. SMIRKS transformation library

**File:** `backend/app/services/lead_optimizer/smirks_library.py` (6019 lines).

**Verified count of `SmirksEntry` records by name-pattern grep:** `167`
unique entries (`grep -cE '^\s*"[A-Z]+_[0-9]+":\s*SmirksEntry\(' …`).

**Category distribution (`grep -oE 'category="[a-z_]+"' | sort | uniq
-c`):**

| Count | Category                          |
|------:|-----------------------------------|
| 54    | `aromatic_ring_swaps`             |
| 48    | `amine_modifications`             |
| 31    | `carbonyl_modifications`          |
| 30    | `o_substitutions`                 |
| 26    | `cns_penetration`                 |
| 25    | `nitrogen_heterocycle_swaps`      |
| 20    | `steric_shielding`                |
| 20    | `polarity_adjustments`            |
| 20    | `metabolic_stability`             |
| 20    | `halogen_substitutions`           |
| 20    | `carboxylic_acid_replacements`    |
| 20    | `bioisosteric_replacements`       |
| 20    | `aromatic_substitutions`          |
| 20    | `amide_bond_replacements`         |
| 15    | `ether_modifications`             |
| 15    | `ester_modifications`             |
| 15    | `carbocyclic_replacements`        |
| 15    | `benzylic_modifications`          |
| 14    | `nitrile_modifications`           |
| 12    | `sulfonamide_modifications`       |
| 10    | `sulfonyl_modifications`          |
| 10    | `catechol_transformations`        |

22 categories total (matches the prompt's `"22+ categories"` claim).
The `category=` totals sum to 480 because most entries appear in
multiple lookup buckets, but the unique-entry count is 167.

**Discrepancy with CLAUDE.md and the live prompt:**

- The 2026-06-06 CLAUDE.md table row says "SMARTS library expanded
  50→90+ entries", that is the **FUNCTIONAL_GROUP_SMARTS dict in
  `rdkit_engine.py`** (the lookup that maps group names to detection
  SMARTS), not the SMIRKS reaction library. There are 80 distinct
  names in `FUNCTIONAL_GROUP_SMARTS` (lines 16-140 of
  `rdkit_engine.py`); CLAUDE.md's "90+" is rounded up.
- The 2026-04-24 CLAUDE.md row claims "SMIRKS library 344 → 479
  entries". The `OPTIMIZATION_AGENT_SYSTEM_PROMPT` line 199 also
  asserts the model has "access to 479 validated SMIRKS entries".
  **Both numbers are unsupported by the file**, the actual unique
  `SmirksEntry` count is 167. The discrepancy is not benign: the LLM
  is being told a count that is ~3× too high, which inflates its
  willingness to select "diverse" strategies.

**RDKit validation:** `validate_entire_library()` (`smirks_library.py:6005-6019`)
parses every SMIRKS via `AllChem.ReactionFromSmarts` and counts
template arity. It is defined but **not invoked from any production
code path** (`grep -rn validate_entire_library backend/ frontend/`
returns only the definition; no startup hook, no test). The "all
RDKit-validated" claim is a hand-curation assertion, not a runtime
gate.

**Lookup function:** `get_smirks_for_group(group_name)`
(`smirks_library.py:5950-6004`) is a hard-coded `group_to_categories`
dict mapping the 75 supported group names to 1-4 categories each.

---

## 4. SMARTS builder + scaffold gate

### `pre_scan_molecule` (`rdkit_engine.py:258-321`)
Returns:
- `all`: deduplicated functional group names matched by
  `FUNCTIONAL_GROUP_SMARTS` (84 patterns)
- `labeled`: per-instance enumeration with `{label, name, atom_indices,
  position_hint}`. Single matches keep the bare name; multiple matches
  get `_left/_right/_central/_top/_bottom` suffixes from
  `_position_hint_from_2d` (`rdkit_engine.py:184-225`).
- `core_rings` / `peripheral`: name-level partition by
  `CORE_SCAFFOLD_GROUPS` set (`rdkit_engine.py:142-147`).
- `scaffold_atoms`: RDKit atom-index set from `MurckoScaffold.GetScaffoldForMol`
  via `compute_murcko_scaffold` (`rdkit_engine.py:149-181`).
- `scaffold_smarts`: SMARTS string of the Murcko scaffold mol.

### `build_smarts_from_groups` (`rdkit_engine.py:374-608`)
- Per-instance SMARTS: when the Vision Agent emits `phenyl_left`,
  `_resolve_label` (`rdkit_engine.py:323-349`) maps the label back to
  `(base_name, atom_indices)` and `_atom_set_smarts` calls
  `Chem.MolFragmentToSmarts` to build a SMARTS that locks **only those
  specific atoms** (`rdkit_engine.py:352-371`). This produces
  per-instance labelling like `phenyl_left` vs `phenyl_right` that the
  test at `test_lead_optimizer.py:567-615` verifies.
- Safety default ("Layer 4"): if the same base group name appears in
  BOTH restricted and target without per-instance disambiguation, the
  restricted entry is dropped and the group routes to TARGET
  (`rdkit_engine.py:451-465`). Test at
  `test_lead_optimizer.py:618-663`.
- **The Murcko scaffold SMARTS is NOT appended to `restricted_smarts`**
  (see explicit comment at `rdkit_engine.py:594-598`). The 2026-06-05
  CLAUDE.md row that said "scaffold SMARTS appended to restricted_smarts"
  was reverted on 2026-06-06; the current policy is soft topology, not
  hard SMARTS.

### `enforce_pharmacophore` (`rdkit_engine.py:717-757`)
Two checks:
1. **Hard:** every entry in `restricted_smarts_parts` must still
   substructure-match the analog.
2. **Soft:** if `lead_smiles` is supplied, the analog's
   `_ring_topology_profile` (total rings, aromatic rings, fused atoms;
   `rdkit_engine.py:692-714`) must equal the lead's. This is the
   "soft Murcko ring-topology gate" CLAUDE.md describes.

Tests `test_lead_optimizer.py:453-490` cover the topology-preserving
pass case, ring-destroying reject case, and legacy-no-lead call.

---

## 5. Permutation engine

`permutation.generate_combinatorial_library`
(`backend/app/services/lead_optimizer/permutation.py:34-202`):

- Pre-tests every SMIRKS once against the lead via
  `execute_smirks_substitution`; transformations producing zero
  products are added to `_DEAD_SMIRKS_BY_TASK[task_id]` and skipped
  (`permutation.py:60-75`).
- Builds per-site option lists with an explicit "no change" option
  (`permutation.py:78-84`) and takes the full Cartesian product
  (`permutation.py:87`).
- **Combinatorial cap:** orchestrator passes `max_analogs=100000`
  (`orchestrator.py:442`); the function truncates the combination
  list above that ceiling (`permutation.py:91-93`). The orchestrator's
  `methodology_notes_list` text also references "cap: 15,000" for the
  no-LID path (`orchestrator.py:630`), which is **inconsistent** with
  the actual passed cap of 100 000, the 15 000 number is hard-coded
  prose, not a real limit.
- Per combination it applies SMIRKS sequentially, picks the topology-
  preserving product (`_pick_best_product`, `permutation.py:100-114`),
  rejects dup SMILES, then runs the soft+hard gate via
  `enforce_pharmacophore` (`permutation.py:166`).
- **In-loop synth-accessibility cut:** `simple_gasa_predictor`
  predicts SYBA on every candidate; analogs with `syba_score < -25`
  are dropped (`permutation.py:172-185`). Ertl SAScore > 6.0 is the
  Ertl-fallback cutoff when SYBA is unavailable.
- What actually constrains explosion: dead-SMIRKS pruning (commonly
  20-40 %), pharmacophore filter, ring-topology gate, the SYBA cut,
  and the 100K cap. With a typical LID-derived `n_sites ≤ 5` and
  `≤ 50` strategies / site, the raw Cartesian space rarely exceeds
  10⁵, the 100K ceiling is meant for the no-LID path where
  fallback inflates sites.

---

## 6. Pre-filter, ADMET screen, ranking

### Pre-filter (`filtering.py:79-114`)
Cascade per analog:
1. `check_lipinski`, MW < 500, logP < 5, HBD ≤ 5, HBA ≤ 10
   (`filtering.py:20-31`).
2. `check_pains`, RDKit FilterCatalog PAINS (`filtering.py:33-38`).
3. `check_brenk`, RDKit FilterCatalog BRENK (`filtering.py:40-45`).
4. `check_glaxo`, custom SMARTS list from
   `backend/data/medchem_knowledge/glaxo_structural_alerts.csv`
   (`filtering.py:48-77`); missing file → soft pass.

**No explicit valency or sanitisation re-check at this stage**, that
happens earlier inside `execute_smirks_substitution`'s `_sanitize_product`
(`rdkit_engine.py:626-650`).

### ADMET screen (`orchestrator.batch_admet_screen`, `orchestrator.py:200-219`)
Calls the registered `admet_service.predict_batch` in chunks of 50.
On failure, fills the batch with empty dicts and continues.

### Ranking (`backend/app/services/lead_optimizer/ranking.py`)
- `BASE_WEIGHTS` (`ranking.py:14-20`):
  `scaffold_preservation=0.15`, `pharmacophore_similarity=0.05`,
  `gasa_accessibility=0.05`, `diversity_bonus=0.05`,
  `drug_likeness=0.05`. ADMET takes the remaining 0.65 (`ranking.py:276`).
- ADMET sub-score is weighted by the LLM-derived
  `ContextAnalysis.endpoint_priorities`; BBB is boosted ×1.5 when
  CNS keywords appear in the user's free-text context
  (`ranking.py:179-201`); BBB < 0.5 in CNS context multiplies the
  GASA penalty by 0.5 (`ranking.py:235-238`).
- Penalty stack on top of the weighted sum:
  - 75 % normalised-score haircut for any worsening endpoint
    (`ranking.py:229`).
  - Critical-liability cap at 0.6 if a worsening endpoint had
    weight > 0.3 (`ranking.py:249-250`).
  - GASA penalty multiplier proportional to "harder than lead"
    margin (`ranking.py:167-175`).
  - **Hard cap at 0.30** if Murcko scaffold Tanimoto < 0.1
    (`ranking.py:288-289`).
- "Implausible ADMET" flag: > 4 endpoints simultaneously improving by
  > 80 % → set `_admet_implausible=True` for UI warning, does NOT
  change the score (`ranking.py:100-124`).

**Not a true Pareto front.** The function returns a scalar weighted
sum that gets sorted descending (`ranking.py:323`); `pareto_rank` is
just the position in that sorted list (`ranking.py:325-326`). Calling
it "Pareto" is convention from the API field name, not the algorithm.

### Diversity (`diversity.py`)
Morgan fingerprints (radius 2, 2048 bits) → Butina clustering at
distance 0.4 (`diversity.py:36-53`). `select_diverse_representatives`
keeps up to `max_per_cluster=10` per cluster (orchestrator passes 10,
`orchestrator.py:619`) then re-sorts by `pareto_score`
(`diversity.py:101-105`).

---

## 7. SYBA integration

Single source of truth: `simple_gasa_service.synth_accessibility_predictor`
(re-exported as `simple_gasa_predictor`,
`backend/app/services/simple_gasa_service.py:25`). The header notes SYBA
(Voršilák 2020, AUC > 0.81) is the primary classifier, Ertl SAScore the
fallback.

Read sites (`grep -n "syba_score" backend/app/services/lead_optimizer/`):

- `orchestrator.py:353`, lead-level SYBA stored on `lead_profile.admet_data["GASA"]`
  with `setdefault("syba_score", …)`.
- `orchestrator.py:646`, `lead_syba_score` passed to `generate_report`.
- `permutation.py:182-184`, in-loop reject when `syba_score < -25`
  (signed scale: positive = easier).
- `ranking.py:36-44`, `_get_synth_difficulty` reads `syba_score`
  first, maps via `1 / (1 + e^(syba/8))`, falls back to
  `hard_probability` only when SYBA is absent. Test
  `test_lead_optimizer.py:763-791` locks this behaviour in.
- `report_generator.py:36-95`, `_syba_label` / `_syba_render` /
  `_syba_block` render SYBA primary; SAScore appears only as
  parenthetical fallback.
- `api/v1/endpoints/lead_optimizer.py:704-758`, the CSV export header
  is `"SYBA Score", "SYBA Verdict", "SYBA Confidence"` first, with
  "SA Score (legacy Ertl)" and "GASA Easy/Hard Prob (legacy)" pushed
  right.

Rule 36 is honoured throughout. The `GASA` dict still carries
`hard_probability`/`easy_probability` for the audit trail.

---

## 8. Reports (PDF / HTML / SDF / CSV)

- `report_generator.generate_report`
  (`backend/app/services/lead_optimizer/report_generator.py:304-…`)
  builds one HTML string then writes it three places:
  - `report_dir/{task_id}.html` (`report_generator.py:1065`)
  - `report_dir/{task_id}.pdf` via WeasyPrint with xhtml2pdf fallback
    (`report_generator.py:1083-1106`)
  - `report_dir/{task_id}.sdf` (`report_generator.py:1067`)
- CSV is generated on-demand by
  `api/v1/endpoints/lead_optimizer.py:650-767` from
  `optimization_tasks.result.top_analogs`. It is NOT written by
  `generate_report`.
- SYBA is the headline synth metric in all four exports; the SAScore
  row labelled "fallback" is only emitted when `syba_score is None`
  (`report_generator.py:62-72`).

Download routes: GET `/lead-optimizer/{task_id}/report/pdf|sdf|html|csv`
(`api/v1/endpoints/lead_optimizer.py:504-767`). All four require
`status == 'completed'`.

---

## 9. Tests

`backend/tests/regression/test_lead_optimizer.py` has **38 test
functions** (`grep -c '^def test_'`). Some are parametrised; pytest
collects 51 cases total (5 from `branch_label`, 5 from
`pipeline_handles_diverse_scaffolds`). The five most informative:

1. `test_pipeline_handles_diverse_scaffolds` (`:683-719`), parametrised
   over aspirin, caffeine, ibuprofen, imatinib-core, compound 25014.
   Asserts each lead produces ≥ N editable groups AND ≥ M groups with
   SMIRKS coverage. This is the only test that runs the deterministic
   half of the pipeline end-to-end across multiple chemotypes.
2. `test_build_smarts_resolves_per_instance_label_to_atom_specific_smarts`
   (`:567-615`), verifies that `phenyl_left` produces an atom-specific
   SMARTS rather than the generic `c1ccccc1` that would lock both
   rings. The core regression for the 25014 dual-phenyl bug.
3. `test_ranking_uses_syba_score_not_hard_probability_when_available`
   (`:763-791`), locks Rule 36: SYBA must override `hard_probability`
   even when they disagree (e.g. SYBA +25 vs hard_prob 0.99).
4. `test_safety_default_same_basename_in_both_lists_routes_to_target`
   (`:618-663`), codifies the "Layer 4" safety default: if Vision
   Agent classifies the same base group in both restricted and target
   with no disambiguation, route to target. Encodes the chemist's
   "everything else is editable" policy.
5. `test_enforce_pharmacophore_accepts_topology_preserving_analog` and
   the matching reject test (`:453-478`), pin the soft scaffold gate
   so future changes can't silently revert to the old hard SMARTS
   append.

**What is NOT tested (verified by absence of matching test names):**

- **No end-to-end pipeline integration test.** Nothing exercises
  `run_lead_optimization` from `lead_smiles + LID bytes` to
  `OptimizationResult`, the Vision Agent, Optimization Agent, and
  ADMET service all require live API keys and are mocked nowhere.
  The module docstring at `test_lead_optimizer.py:11-15` admits this:
  *"Live LLM behaviour (seed determinism in context_analyzer /
  optimization_agent / vision_agent) is verified by manual runs"*.
- **No accuracy benchmark on real LIDs.** `vision_agent.py` has no
  fixture LIDs in `tests/`; classification recall vs. a ground-truth
  set is unmeasured.
- **No scaffold-preservation diversity benchmark.** Whether
  `enforce_pharmacophore`'s topology check actually preserves
  binding-pose-relevant features across a panel of kinase / GPCR /
  protease scaffolds is asserted only on two leads
  (`enforce_pharmacophore_*` tests use toluene-ol and
  2,3-dihydrobenzofuran).
- **No test of the LLM JSON-mode robustness path**, i.e. whether
  Kimi's reasoning-only fallback actually recovers JSON correctly.
  The `_extract_json_object` helper is uncovered.
- **No regression test exists for the SMIRKS pre-check loop** in
  `permutation.py` (dead-SMIRKS detection is exercised at the cache
  level only).
- **No test of `_admet_implausible` flag thresholds.**
- **No CSV / PDF / HTML report-content tests.**
- **No test that the prompt's SMIRKS-count claim ("479") matches the
  actual library size**, which is how the discrepancy in Section 3
  went unnoticed.

---

## 10. Validation evidence

**None found.** Concretely:

- No matched-molecular-pair recovery benchmark (no `mmpdb` import in
  `backend/`, no `matched_molecular_pair` files, nothing in
  `tests/regression/` reading MMPDB or ChEMBL pairs).
- No comparison vs. baseline analog generators (no `mmpdb`, `Chembl`,
  `JTNN`, `REINVENT`, `STONED` references in the codebase).
- The only "benchmark" mention in the entire `lead_optimizer/` tree is
  in `report_generator.py:1044, 1049`, which is the **report's own
  user-facing copy** describing SYBA's published AUC > 0.81, i.e. a
  citation to Voršilák 2020, not a Benchside-run benchmark.
- The 38-test regression suite asserts pure-Python invariants
  (schema round-trips, SMARTS construction correctness, dead-SMIRKS
  cache isolation, prompt-text presence). It does not measure
  *quality* of generated analogs.
- The 2026-06-06 CLAUDE.md row mentions "14 new regression tests"
  added in Phase 5, these are the tests above; none of them is an
  analog-quality benchmark.

For the preprint, the honest framing is: the pipeline is *correctness-
tested at the component level* (schema fidelity, scaffold-topology
preservation, SYBA wiring). It is **not** quality-benchmarked against
matched-molecular-pair recovery, MMPDB, or any other generator.

---

## 11. Known issues / TODO comments

`grep -rnEi "TODO|FIXME|XXX|HACK"
backend/app/services/lead_optimizer/` returns **no matches**. The
codebase contains no developer self-flagged issues in this module.

However, several issues are documented in inline comments rather than
TODO markers:

- **MiniMax M3 dead by default** (`vision_agent.py:23-28`), Anthropic-
  compat M3 burns the whole token budget on `thinking` blocks; M2.5/M2.7
  are text-only. The Tier 1b branch is keyed off `MINIMAX_VISION_MODEL`
  being explicitly set by env var. Deferred upgrade path.
- **No Mistral SDK detection** in `optimization_agent.py:11-15`, falls
  through to a raw `requests` HTTP call if the SDK is missing. Not a
  bug but a quietly degraded path.
- **Worker uses `users` table; endpoint uses `profiles` table**
  (`worker.py:213` vs `endpoints/lead_optimizer.py:294, 332`) for the
  same email lookup. The worker comment explains the bug: `profiles`
  raises PGRST205 and silently swallows the completion email. The
  endpoint paths were not updated. **This is a live bug**, emails
  sent from the bg pipeline path (no-LID flow that doesn't pause for
  review) will fail.
- **Methodology text references 15 000 analog cap** that isn't real
  (`orchestrator.py:630`), the actual cap is 100 000. User-facing
  prose is incorrect.
- **Prompt claims "479 validated SMIRKS entries"** while the library
  has 167 (`prompts.py:199`).

---

## What's solid / What's partial / What's missing

### Solid

- Twelve-stage pipeline is wired end-to-end; every stage in CLAUDE.md
  exists in `orchestrator.py` and is reachable.
- RDKit-deterministic substructure detection, per-instance labelling,
  and Murcko scaffold computation in `rdkit_engine.py:258-321`.
- Multi-residue Vision Agent schema (`schemas.py:15-46`) with legacy
  back-fill via `model_validator`.
- Chemistry-validity validator (`chemistry_validator.py`) with six
  interaction-type allowlists, wired into Vision Agent post-processing.
- Soft ring-topology scaffold gate in `enforce_pharmacophore`
  (`rdkit_engine.py:717-757`), locked by two regression tests.
- SYBA as primary synth-accessibility metric across orchestrator,
  permutation cut-off, ranking, report, and CSV. Rule 36 honoured.
- Pre-filter cascade (Lipinski + PAINS + Brenk + Glaxo) and Butina
  diversity clustering both work and are simple/auditable.
- Two-category Vision Agent prompt: STRUCTURAL_CORE was removed from
  the prompt and schema example; lingering field merges into target.

### Partial

- "Pareto" ranking is a weighted scalar sum with multiplicative
  penalties, not a Pareto front. The terminology is misleading; the
  algorithm is defensible but should be described accurately in the
  preprint.
- SMIRKS library count: 167 unique entries, not 344 / 479 as
  documented in CLAUDE.md and the live LLM system prompt.
- Llama 4 Maverick 17B-128e is described in the 2026-06-05 CLAUDE.md
  row as the new Vision Agent fallback; the actual constant in
  `vision_agent.py:36` is still Scout 17B-16e.
- Vision Agent provider tier 1 is Kimi K2.6 today (default-on), not
  MiniMax M3, the original Tier 1 is dead-by-default. The docstring
  at `vision_agent.py:14-21` still says "MiniMax M3 … is Tier 1".
- 100 000 analog cap vs. the 15 000 number written into user-facing
  methodology prose at `orchestrator.py:630`.
- Worker vs. endpoint email-lookup table inconsistency (`users` vs
  `profiles`), one path silently fails.
- Frontend `PipelineMonitor` exposes a `reviewStructuralCore` prop
  surface, but the page at `studio/page.tsx:65` always passes `[]` ,
  legacy UI plumbing left over after the policy change.

### Missing

- **No analog-quality benchmark** of any kind. No MMP recovery, no
  comparison to MMPDB / REINVENT / JTNN / STONED, no kinase-inhibitor
  retrospective.
- **No end-to-end pipeline integration test.** The full
  `run_lead_optimization` path is verified only by manual runs.
- **No Vision Agent accuracy measurement** on real LIDs. Recall on
  ground-truth interaction sets is unknown.
- **No SMIRKS-library validity gate at startup.**
  `validate_entire_library()` is defined but never invoked; nothing
  catches a SMIRKS-string regression.
- **No prompt-vs-library consistency check**, the SMIRKS count drift
  (479 vs. 167) is the visible symptom.
- **No clear hierarchical Pareto front computation**, if the preprint
  intends to claim Pareto-optimal ranking, the implementation needs a
  proper dominance-set construction.
- **No docking / binding-pose scoring**, acknowledged explicitly in
  `ranking.py:139-143`: scaffold preservation is used as a *proxy* for
  pose preservation, with the comment "True binding-pose evaluation
  requires a docking step that is not yet wired into the pipeline."
- **No regression test for Vision Agent JSON-recovery from
  reasoning_content**, Kimi's heavy-reasoning fallback is uncovered.
