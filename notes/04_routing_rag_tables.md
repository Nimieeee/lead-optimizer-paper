# 04 — Routing, RAG, Table Intelligence (factual inventory)

Notes compiled from a top-to-bottom read of three subsystems on commit
`9ef973c` (master). Every claim is anchored by a file:line citation;
gaps and stale code are flagged inline rather than papered over.

---

## (a) LLM multi-provider routing

The router lives in a single module of ~885 lines and orchestrates five
HTTP providers behind one `generate` / `generate_streaming` interface
(`backend/app/services/multi_provider.py:54-885`). Selection is
priority-by-mode with health-aware failover; there is no real
load-balancer beyond a weighted random pick when every priority list is
exhausted.

### 1. Provider classes

All providers are HTTP clients spoken through `httpx.AsyncClient` with
shared connection pooling (`multi_provider.py:127-128`). There is one
single `MultiProviderService` class — each provider is a `ProviderConfig`
dataclass row in `self.providers`, not a separate class. The `Provider`
enum holds the canonical identifiers
(`multi_provider.py:27-32`).

| Provider | Enum | Status in code | Initialised when | Base URL |
|---|---|---|---|---|
| Pollinations | `Provider.POLLINATIONS` | **Active fallback tier** | `POLLINATIONS_API_KEY` set (`multi_provider.py:181-201`) | `https://gen.pollinations.ai/v1` |
| OpenCode Go (OAI-compat) | `Provider.OPENCODE_GO` | **Active primary** | `OPENCODE_GO_API_KEY` set (`multi_provider.py:233-268`) | `https://opencode.ai/zen/go/v1` |
| OpenCode Go (Anthropic-compat) | — | **Not wired into multi_provider** (see §7) | n/a | `https://opencode.ai/zen/go/v1/messages` (used only by the Vision Agent, `lead_optimizer/agents/vision_agent.py:43`) |
| Groq | `Provider.GROQ` | **Active — fast-mode lead** | `GROQ_API_KEY` set (`multi_provider.py:159-178`) | `https://api.groq.com/openai/v1` |
| Mistral | `Provider.MISTRAL` | **Active fallback** | `MISTRAL_API_KEY` set (`multi_provider.py:204-223`) | `https://api.mistral.ai/v1` |
| NVIDIA NIM | `Provider.NVIDIA` | **Registered, never selected** | `NVIDIA_API_KEY` set (`multi_provider.py:131-153`) | `https://integrate.api.nvidia.com/v1` |

NVIDIA NIM is initialised when the key is present, but the
`MODE_PRIORITIES` dict (`multi_provider.py:86-101`) does not include
`Provider.NVIDIA` in any priority list any more. So the provider object
exists, weight=0.80 (`multi_provider.py:150`), startup print says
"Primary – 80% weight" — but it can only be reached through the
weighted-random "absolute last resort" branch at
`multi_provider.py:357-370`. **Documentation reality check:** the
docstring at lines 5-9 still advertises "Best provider for each mode
(Fast→Groq, Detailed→NVIDIA, Research→NVIDIA)" and "Weighted distribution:
NVIDIA (80%), Groq (15%), Mistral (5%)". That's stale — the actual code
no longer wires NVIDIA into any mode and the weights aren't used for
distribution, only for the dead-letter fallback.

### 2. Model list per provider (verbatim from code)

```
NVIDIA  (multi_provider.py:139-145)
  fast / detailed / deep_research_elite : openai/gpt-oss-120b
  deep_research / deep_research_single_pass : meta/llama-3.3-70b-instruct

Groq  (multi_provider.py:164-170)
  fast                          : llama-3.1-8b-instant
  detailed / deep_research / deep_research_elite : openai/gpt-oss-120b
  deep_research_single_pass     : meta/llama-3.3-70b-instruct

Pollinations  (multi_provider.py:187-193)
  fast                          : deepseek      (DeepSeek V4 Flash, comment says 1M ctx)
  detailed / deep_research / deep_research_elite / deep_research_single_pass : qwen-large

Mistral  (multi_provider.py:209-215)
  fast      : mistral-small-latest
  *others*  : mistral-large-latest

OpenCode Go (multi_provider.py:252-258)
  fast                          : mimo-v2.5
  detailed / research           : mimo-v2.5-pro
  deep_research                 : mimo-v2.5            (planner/researcher/reviewer JSON)
  deep_research_elite           : deepseek-v4-pro      (writer — long-form)
  deep_research_single_pass     : mimo-v2.5
```

Pollinations key candidates documented in CLAUDE.md (`gemini-fast`,
`claude-airforce`) are NOT in the live model dict — they exist only as
prose warnings, the code only sends `deepseek` and `qwen-large`.

### 3. MODE_PRIORITIES

Verbatim from `multi_provider.py:86-101`:

```python
"fast":               [GROQ, POLLINATIONS, OPENCODE_GO, MISTRAL]
"detailed":           [OPENCODE_GO, POLLINATIONS, MISTRAL]
"research":           [OPENCODE_GO, POLLINATIONS, GROQ, MISTRAL]
"deep_research":      [GROQ, OPENCODE_GO, POLLINATIONS, MISTRAL]
"deep_research_elite":[OPENCODE_GO, POLLINATIONS, MISTRAL]
"deep_research_single_pass":[OPENCODE_GO, POLLINATIONS, GROQ, MISTRAL]
```

Note the CLAUDE.md rule table claims `deep_research_planner/researcher/
reviewer` are separate modes routed primarily to Groq `gpt-oss-120b`.
**In code there is only one `deep_research` key** — the planner /
researcher / reviewer nodes call `generate(mode="deep_research")` and
get whatever model the chosen provider has registered under that mode
(Groq → `gpt-oss-120b`, OpenCode Go → `mimo-v2.5`). The naming in
CLAUDE.md is aspirational; the dict is one key.

### 4. Eager-skip ceiling (Groq 7,500 tokens)

Confirmed in two places:

- `config.py:97` — `MULTI_PROVIDER_GROQ_CONTEXT_LIMIT_TOKENS = 7500`,
  override via env.
- Applied at `multi_provider.py:512-522` (streaming) and `716-725`
  (non-streaming). For every provider, the dict
  `PROVIDER_CONTEXT_WINDOWS` is consulted; Groq's nominal 128k is
  overridden with the settings value before the `required_tokens *
  1.2 > window` check. If the prompt won't fit, the provider name
  is added to `attempted_providers` and skipped *before* its
  priority position is even considered.

### 5. PROVIDER_CONTEXT_WINDOWS

`multi_provider.py:113-119`:

```python
PROVIDER_CONTEXT_WINDOWS = {
    Provider.GROQ:         7_500,        # TPM-rate-limit cap (overridden by settings)
    Provider.POLLINATIONS: 1_000_000,
    Provider.OPENCODE_GO:  256_000,
    Provider.MISTRAL:      32_000,
    Provider.NVIDIA:       128_000,
}
```

The 1.2 safety multiplier (`multi_provider.py:511, 715`) means a 27k
char Pollinations payload, a 213k char OpenCode Go payload, and a 26k
char Mistral payload are the practical ceilings. No tokeniser is
called — character count is divided by 4 (`multi_provider.py:503-504,
711-712`), which underestimates non-English text.

### 6. SSE streaming and `reasoning_content` drop

The streaming path opens a long-lived `httpx.AsyncClient.stream("POST",
…)` and iterates lines (`multi_provider.py:558-612`). Per chunk it does:

```python
chunk = json.loads(data)                      # line 600
choice = chunk.get("choices", [{}])[0]
content = choice.get("delta", {}).get("content", "")   # line 602
if content:
    yield content                              # line 604
```

That's it. The parser reads only `delta.content`. The OpenAI/Groq SSE
shape also carries `delta.reasoning_content` on heavy-reasoning models
(MiMo, DeepSeek V4, Kimi K2.6). **This field is never read in
`multi_provider.py`** — so it is silently dropped at the consumer, which
is exactly Rule 30's failure mode: models that emit only
`reasoning_content` before any `content` chunk appear as empty
responses to the router. The Vision Agent has its own salvage path that
reads `message.reasoning_content` and re-extracts JSON from the
reasoning trace (`lead_optimizer/agents/vision_agent.py:323-327`), but
the main chat path does not.

Finish-reason capture is wired (`multi_provider.py:607-610`) and a
truncation warning is logged when `finish_reason == "length"`. Empty
streams trigger a non-streaming fallback to a different provider with
the current one excluded (`multi_provider.py:643-660`).

### 7. Anthropic-compat endpoint status

Rule 30 ("Anthropic-compat endpoint not yet wired into multi_provider")
is **accurate**. `multi_provider.py` only ever POSTs to
`{base_url}/chat/completions` (`multi_provider.py:560, 765, 822`). The
OpenCode Go base URL it uses (`https://opencode.ai/zen/go/v1`,
`multi_provider.py:238`) is the OAI-compat shape.

The Anthropic-compat endpoint **is** called, but only from the Lead
Optimizer Vision Agent in a separate module
(`lead_optimizer/agents/vision_agent.py:43`):

```python
OPENCODE_GO_MESSAGES_URL = "https://opencode.ai/zen/go/v1/messages"
```

with headers `x-api-key` (not `Authorization: Bearer`) and
`anthropic-version: 2023-06-01` (`vision_agent.py:154-159`). The
salvage logic for `reasoning_content` lives at `vision_agent.py:316-327`
for Kimi K2.6 (OAI-compat fallback in the same file) and at
`vision_agent.py:170-220` for MiniMax M3 (Anthropic-compat reasoning
JSON extraction). None of this is callable from chat — only from the
Lead Optimizer worker.

### Section (a) — what's solid / partial / missing

- **Solid:** per-provider context-window filtering with adaptive
  timeouts; permanent 401/403 circuit breaker
  (`multi_provider.py:388-394`); exponential backoff on 429
  (`multi_provider.py:375-386`); fire-and-forget health and usage
  logging to Supabase (`multi_provider.py:431-482`); empty-content
  coercion defense for Pollinations qwen-large
  (`multi_provider.py:851-856`).
- **Partial:** the `MODE_PRIORITIES` dict has no sub-keys for
  planner/researcher/reviewer/writer — CLAUDE.md's nuanced routing
  table is only honoured by what the *callers* in `deep_research.py`
  decide to pass as `mode=`. The router treats them all as one mode.
- **Missing:** no integrated Anthropic-compat streaming path (Vision
  Agent has its own); no token-accurate tokeniser (chars/4 underestimates
  CJK/symbol-heavy payloads); NVIDIA NIM provider object is dead
  weight — initialised but never reachable through the priority list,
  and the startup banner still claims "Primary – 80% weight" which is
  false. Cost mapping at `multi_provider.py:461-467` still includes
  NVIDIA, so a stale revival would log non-zero costs.

---

## (b) RAG

Two parallel implementations exist: the older `rag.py` (959 lines,
hash-fallback embeddings, simple per-conversation SimpleTextSplitter) and
the live production path through `enhanced_rag.py` (1,108 lines, Mistral
embeddings + pgvector RPC). Constants are consolidated under
`rag_config.py` per Rule 37, but `rag.py` still hard-codes some of its
own.

### 1. Embedding model and version stamping

Default provider is `mistral` (`config.py:63`), 1024 dimensions
(`config.py:64`). The factory in `embeddings.py:11-26` selects between
`mistral_embeddings.MistralEmbeddingsService` (default) and
`sentence_transformer_embeddings.SentenceTransformerEmbeddingsService`
(local override). Mistral model name is `mistral-embed`
(`mistral_embeddings.py:38-39`).

There is a `CohereEmbeddingsService` (`cohere_embeddings.py:35-403`)
with a constructor, embed methods, and a global getter
(`cohere_embeddings.py:395-402`), but the factory in `embeddings.py`
never references it. **Cohere embeddings are dead code** — present,
working, callable from a script, but no production code path imports
them.

Version stamping is centralised under
`RAGConfig.EMBEDDING_VERSION = "v1-mistral-embed-1024"`
(`rag_config.py:59`). On insert, `enhanced_rag.py:321` writes that
literal into chunk metadata. **Inconsistency:** the legacy `rag.py` at
line 314 stamps `"mistral-v1"` (or `"hash-v1"` on fallback), not
`"v1-mistral-embed-1024"`. So conversations loaded through the legacy
path produce chunks that the `RAGConfig.validate_embedding_version()`
check at `rag_config.py:73-80` would mark stale. The validator is
defined but I found no caller in the production query path — the
"fail-loud on mismatch" promise in the rule docstring isn't enforced
yet.

### 2. Chunk size, overlap, mode budgets

Two competing chunk-size configs coexist:

- `RAGConfig.CHUNK_SIZE = 1500`, `CHUNK_OVERLAP = 300`
  (`rag_config.py:41-42`) — the registry value.
- `settings.LANGCHAIN_CHUNK_SIZE = 1000`, `LANGCHAIN_CHUNK_OVERLAP = 200`
  (`config.py:74-75`) — the env-var-driven value used by
  `EnhancedTextSplitter` (`text_splitter.py:33-34`) and reported in
  `enhanced_rag.py:1079-1080`.

So the live production chunk size is **1000 / 200**, not the registry's
1500 / 300. The registry hasn't propagated to `text_splitter.py` yet
(Rule 37 promises this consolidation; the work is half done).

Mode budgets (`rag_config.py:31-38`):

| Mode | max_chunks | max_chars |
|---|---|---|
| fast | 3 | 8,000 |
| detailed | 10 | 25,000 |
| research | 15 | 150,000 |
| deep_research | 20 | 200,000 |
| (default fallback) | 5 | 25,000 |

These are pulled via `RAGConfig.budget_for(mode)` and applied in
`ai.py:2224-2236` (one of three retrieval sites; the other two at
ai.py:463 and ai.py:891 follow the same pattern).

### 3. In-context bypass

Triggered at `ai.py:2132-2206`. The path:

1. Look for `/tmp/raw_docs/{conversation_id}.txt` — written by
   `enhanced_rag.py:399-407` on every upload, appended with a
   `===== FILE: {filename} =====` header so multiple uploads share one
   conversation file.
2. If the file exists and is not older than 7 days
   (`ai.py:2135-2138`), read it.
3. Compare its character length against
   `RAGConfig.IN_CONTEXT_MAX_CHARS = 100_000` (`rag_config.py:51`).
   Above that, the bypass is skipped via a raised `FileNotFoundError`
   sentinel and the normal RAG path runs (`ai.py:2151-2156`).
4. Below the cap, hand the raw text to TableIntelligence first
   (`ai.py:2169-2179`); if TI fires, return its dossier. Otherwise
   return the raw text as the "context" string and emit
   `'reason': 'in_context_full_document'`.

The bypass NEVER truncates the document below the cap. The router's
context-window filter (§a.5) handles per-provider exclusion — the bug
fix from 2026-05-30 ("two-tier defense fighting itself") removed the
old per-mode pre-trim deliberately.

### 4. Document loaders

`EnhancedDocumentLoader` (`document_loaders.py:155-1862`) registers ten
extensions in its `supported_extensions` map
(`document_loaders.py:159-175`): `.pdf, .txt, .md, .docx, .pptx, .xlsx,
.csv, .png, .jpg, .jpeg, .gif, .bmp, .webp, .sdf, .mol`.

Loaders are called only after `smart_loader.process_file` (`smart_loader.py:57-109`) routes
PDFs to `process_pdf_hybrid`, PPTX to `process_pptx_hybrid`, standalone
images to `process_visual_document`, DOCX/MD/TXT to
`process_text_document`, and explicitly *re-raises* for CSV / XLSX /
SDF so the legacy LangChain loader's full data extraction runs
(`smart_loader.py:92-98`). This is intentional — the VLM-routing
shortcut would otherwise mangle a 1,000-row CSV through summarisation.

The empty-content guard from the 2026-06-06 audit fires at
`document_loaders.py:248-256`: if `smart_loader` returns content shorter
than `RAGConfig.MIN_DOC_CONTENT_CHARS = 50` (`rag_config.py:65`), the
call falls through to the legacy LangChain loader instead of silently
producing a zero-chunk Document. CSV branch is at `_load_csv`
(`document_loaders.py:927-1059`); SDF branch at `_load_sdf`
(`document_loaders.py:1141-1422`).

### 5. Reranking

`rag.py:788-801` implements `rerank_chunks` as a **lexical-overlap
re-scorer**: it blends each chunk's vector similarity (60%) with a
Jaccard-style query-word overlap and a 0.5 phrase-match boost (40%).
Hybrid retrieval (`rag.py:803-879`) does vector search + ILIKE keyword
search + Reciprocal Rank Fusion (k=60, `rag.py:860-866`).

**No external reranker.** No Cohere `/rerank` endpoint call anywhere in
`backend/app/services/`. The Cohere SDK is wired only for embeddings,
and even that path is dead (see §1).

### 6. Vector store

Supabase pgvector via the RPC function
`match_documents_with_user_isolation`
(`enhanced_rag.py:633-642`). Storage is the `document_chunks` table
written by `enhanced_rag.py:354` (`db.table("document_chunks").insert(batch)`).
The schema is not in the codebase as a migration I located, but the
RPC's signature (`query_embedding`, `query_conversation_id`,
`query_user_id`, `match_threshold`, `match_count`) implies a vector
column and per-user/per-conversation row-level filters. Recovery
ladder: threshold drops from caller's value to 0.05
(`enhanced_rag.py:690-694`), then to "return all conversation chunks"
(`enhanced_rag.py:696-699`).

A pre-check at `enhanced_rag.py:610-617` skips embedding generation
entirely when the conversation has no `document_chunks` rows — saves
the Mistral round-trip on every "new chat" turn.

### 7. Citation / source attribution

Chunk metadata carries `filename`, `page`, `source`, `file_type`,
`user_id`, `conversation_id`, plus `embedding_model`,
`embedding_dimensions`, `embedding_version`, `processing_timestamp`,
`chunk_length`, `langchain_processed`
(`enhanced_rag.py:311-325`). When chunks are merged into a context
string for the LLM (`rag.py:907-936`), filenames are surfaced as a
`📄 {filename} – N sections` overview block, and per-file `=== {filename}
===` separators are inserted into the prompt. Page numbers are stored
but I did not find them rendered into the prompt — the LLM sees the
filename but cannot cite a specific page.

### Section (b) — what's solid / partial / missing

- **Solid:** Mistral embeddings (1024d) + Supabase pgvector + RPC
  with user/conversation row-isolation; in-context bypass with a hard
  100k char cap; markdown-header-aware splitter with recursive
  fallback (`text_splitter.py:40-52`); empty-content guard wired into
  the production upload path.
- **Partial:** `RAGConfig` is the registry but not every consumer
  honours it. `text_splitter.py` reads `settings.LANGCHAIN_CHUNK_SIZE`
  (1000, not the registry's 1500); `rag.py` stamps a different
  embedding-version literal than the registry; `validate_embedding_version`
  is defined but I found no production caller. Reranking is purely
  lexical (Jaccard + RRF) — not learning-based.
- **Missing:** Cohere embeddings + Cohere rerank scaffolding exists
  but is unreachable. No page-number surfacing in retrieved context.
  No batched embedding-version migration path — flipping
  `EMBEDDING_VERSION` would silently invalidate all existing chunks
  with no automatic re-embedding.

---

## (c) Table Intelligence

A dedicated subsystem (~30 Python files across 6 packages) that
intercepts drug-candidate CSV uploads, applies indication-specific
deterministic gates, and emits a Markdown dossier with a persistent
audit ID. Lives entirely under
`backend/app/services/table_intelligence/`.

### 1. Module layout

```
table_intelligence/
├── __init__.py                          # exports orchestrator + audit + replay
├── orchestrator.py                       # 213 lines — pipeline driver
├── schema/
│   ├── column_registry.py                # canonical drug-discovery columns + fingerprints
│   ├── detector.py                       # header sniff + value-range sanity
│   └── multi_file_merger.py              # join multi-file uploads by compound_id
├── intent/
│   └── classifier.py                     # regex-based rank/summarize classifier
├── indication/
│   └── extractor.py                      # CNS / topical / oncology / … patterns
├── gates/
│   ├── gate.py                           # Gate, GateSet, CompoundAudit dataclasses
│   ├── library.py                        # 7 published GateSets
│   └── applier.py                        # per-compound evaluation
├── output/
│   ├── dossier.py                        # Markdown brief builder
│   ├── optimization.py                   # ranked SAR candidates table
│   ├── sensitivity.py                    # per-compound / per-gate what-if
│   └── structural_sar.py                 # RDKit-gated SAR levers
└── audit/
    ├── log.py                            # fire-and-forget Supabase insert
    └── replay.py                         # snapshot replay loader
```

Orchestrator pipeline at `orchestrator.py:71-209`: merge → detect →
classify intent → extract indication → look up GateSet → apply gates →
sensitivity → optimization-candidate analysis → dossier build → audit
write. Three confidence thresholds (`orchestrator.py:66-68`) gate
activation: `SCHEMA_CONFIDENCE_THRESHOLD = 0.5`,
`INTENT_CONFIDENCE_THRESHOLD = 0.5`,
`INDICATION_CONFIDENCE_THRESHOLD = 0.3`. Any failure returns
`applied=False` and the caller falls through to plain LLM narration.

### 2. Gate sets (verbatim from `library.py`)

Seven GateSets are exported, registered by indication code at
`library.py:392-400`. The CLAUDE.md naming `cns_vulnerable_v2` is one
gate set; everything else stops at v1.

**CNS_v2_chronic_vulnerable** (`library.py:44-107`, indication
`cns_vulnerable`, v2.0.0). 14 gates:

| Canonical | Op | Threshold | Kind | Margin |
|---|---|---|---|---|
| docking_score | control_relaxed | 0.0 | hard, required | 0.3 |
| mmgbsa | control_relaxed | 0.0 | hard, required | 2.0 |
| bbb | gt | 0.5 | hard, required | 0.05 |
| tpsa | lt | 90.0 | hard, required | 5.0 |
| logp | between | (1.0, 3.5) | soft, w=0.7 | 0.2 |
| herg | lt | 0.5 | hard, required | 0.05 |
| pains_alerts | eq | 0.0 | hard, required | – |
| dili | lt | 0.75 | hard, required | 0.05 |
| ames | lt | 0.5 | hard, required | 0.05 |
| clintox | lt | 0.2 | hard, required | 0.05 |
| qed | ge | 0.5 | soft, w=0.6 | 0.05 |
| bioavailability | ge | 0.5 | soft, w=0.5 | 0.05 |
| molecular_weight | between | (150,600) | informational | – |
| brenk_alerts | le | 100 | informational | – |

**CNS_v1_chronic_vulnerable** is retained for replay
(`library.py:112-165`, archived). The headline v1→v2 changes:
BBB threshold 0.2 → 0.5 (more-likely-than-not penetration), MMGBSA
promoted from soft `<-45` to hard `control_relaxed`, TPSA 100 → 90.

**CNS_v1_adult** (`library.py:168-208`, indication `cns`). 11 gates.
Looser variant: BBB > 0.2, TPSA < 100, LogP 1-4, hERG < 0.6, PAINS ≤ 1.

**oral_systemic_v1** (`library.py:211-251`). 11 gates. No BBB; adds
`bioavailability ≥ 0.4` as a hard required gate; LogP 0-5.

**topical_v1** (`library.py:254-276`). 5 gates. No BBB or oral-bioavailability
requirement; adds `skin_reaction < 0.5` hard required; LogP 1-5.

**antibacterial_v1** (`library.py:281-318`). 9 gates. PAINS = 0
required (assay-artifact strict); BRENK ≤ 1; hERG < 0.6.

**oncology_v1** (`library.py:321-356`). 8 gates. The strictest binding
(`docking_score control_strict` — must beat ALL 4 controls; MMGBSA
hard ≤ -50). Lenient hERG < 0.7 and DILI < 0.85 for survival-benefit
indications; AMES still strict at < 0.4.

**ophthalmic_v1** (`library.py:359-387`). 6 gates. Strict LogP 1-3
hard required; PAINS = 0; hERG < 0.4 (strictest of any set);
solubility logS ≥ -4 soft.

Per-axis uncertainty margins come from module-level constants
(`library.py:35-41`): probability outputs ±0.05, TPSA ±5, LogP ±0.2,
docking ±0.3, MMGBSA ±2.0, QED ±0.05. Values landing within ±margin of
the threshold are marked `ambiguous` rather than pass/fail
(`gate.py:36-45`).

Every published GateSet sits in the version archive
(`library.py:407-418`), and `get_gate_set_by_version(name, version)`
(`library.py:426-428`) is the replay loader's lookup path.

### 3. Detector confidence floor with binding columns

Schema detector at `schema/detector.py:145-189`. Confidence is computed
as `min(1.0, drug_hits / 10.0)` over the canonicalised header set —
i.e. ten drug-discovery columns saturates at 1.0. But there's an
override: if at least one binding column (docking_score or mmgbsa) is
canonicalised AND the computed confidence is below 0.7, it is **floored
at 0.7** (`detector.py:185-186`). Rationale: binding columns are
unambiguous drug-discovery signals no other domain has. This is the
0.7 floor referenced in the audit note.

The is_drug_candidate property at `detector.py:51-53` then requires
confidence ≥ 0.6, *plus* a presence check for at least one identity
column (smiles or compound_id, `detector.py:166`). The orchestrator's
own activation threshold is 0.5 (`orchestrator.py:66`), so the
detector's per-class threshold (0.6) is the tighter gate in practice.

### 4. Audit and replay

Supabase migration `025_table_intelligence_audit.sql:5-36` defines the
`public.table_intelligence_audit` table with columns: `id (uuid)`,
`user_id`, `conversation_id`, `created_at`, `schema_name`,
`schema_confidence`, `intent`, `indication`, `modifiers (jsonb)`,
`gate_set_name`, `gate_set_version`, `survivors (jsonb)`,
`ambiguous (jsonb)`, `boundary_failures (jsonb)`, `eliminated_count`,
`controls (jsonb)`, `elapsed_ms`, `raw_text_hash (sha256 hex)`,
`dossier_text`.

RLS is enabled (`migration:51-57`); the policy restricts SELECT and
INSERT to rows where `user_id = auth.uid()` or `user_id IS NULL` (system
runs). Three indexes are created — by `(user_id, created_at DESC)`,
by `id`, and by `raw_text_hash` (cache-hit detection on resubmission).

The fire-and-forget writer is `AuditLogger.write_async`
(`audit/log.py:116-126`) which schedules `asyncio.ensure_future`;
on no event loop the write is dropped with a debug log (the dossier
still carries the audit_id, so users can cite it). The replay path
(`audit/replay.py:37-62`) only does a "snapshot replay" — returns the
persisted `dossier_text`. The docstring at `replay.py:8-10` advertises
a `mode='live'` re-run mode, but **it is not implemented** — the
function takes no `mode` parameter. Live replay is aspirational.

REST endpoint `/api/v1/table-intelligence/replay/{audit_id}` at
`backend/app/api/v1/endpoints/table_intelligence.py:37-82`. It validates
the UUID, looks up the row, double-checks ownership against the
authenticated user even though RLS already restricts (belt-and-braces),
and returns the dossier plus structured fields. A companion endpoint
`/indications` (`endpoints/table_intelligence.py:85-88`) lists what
indication codes the orchestrator can apply gate sets to.

### 5. Structural SAR levers

Lives in `output/structural_sar.py:46-525`. Each `SARLever`
(`structural_sar.py:46-65`) carries `requires_present` (SMARTS that
must match), `requires_absent` (SMARTS that must not match), and
`requires_property` (callable on RDKit Mol). The advisor
(`advise(smiles, axis)` at line 492) builds an RDKit Mol from the
SMILES, then filters the per-axis registry down to levers whose
preconditions all hold (`_matches` helper at line 453).

Registries:

- HERG_LEVERS (5+1 levers, line 104) — amine-pKa lever requires
  `_has_basic_amine` (SMARTS-driven sp3 amine detector at line 76),
  pyridine→pyrimidine lever requires SMARTS `c1ccncc1`, etc.
- AMES_LEVERS (8 levers, line 168) — aromatic amine SMARTS
  `[c][NX3;H2,H1]`, nitro `[N+](=O)[O-]`, epoxide
  `[OX2r3]1[CX4r3][CX4r3]1`, azide `[N-]=[N+]=N`, hydroxylamine
  `[NX3]-[OX2H]`, planar-polyaromatic predicate.
- DILI_LEVERS (6 levers, line 220) — catechol, para-hydroxyphenyl,
  Michael acceptor, hydrazine, LogP > 3.5.
- BBB_LEVERS (5 levers, line 267) — TPSA > 70, HBD > 3, phenol SMARTS,
  basic-amine-for-LAT1 transporter.
- TPSA_LEVERS, LOGP_LEVERS, PAINS_LEVERS, DOCKING_LEVERS,
  MMGBSA_LEVERS, CLINTOX_LEVERS — lines 304-436.

If RDKit is unavailable (`_RDKIT_AVAILABLE = False`) the advisor
returns only the always-applicable `confidence="low"` fallbacks
(`structural_sar.py:455-462`). If RDKit is present but NO lever's
preconditions match, the advisor emits a single honest-fallback line
naming lipophilicity / planarity as likely non-canonical drivers
(`structural_sar.py:516-525`) — directly addressing the 2026-06-04 bug
where the dossier prescribed amine-pKa edits to a nitrogen-free
isochroman.

### 6. Tests

Regression suite at
`backend/tests/regression/test_table_intelligence.py`. Forty-five
distinct `def test_*` functions (`grep -cE "^def test_"` = 45). With
parametrisation (`@pytest.mark.parametrize` on intent, indication,
all-indications-have-gate-sets, ophthalmic, expanded-keywords) the
collected-test count is higher (estimated 60-70 by inspection of the
parametrize blocks; the platform CLAUDE.md table reports 293 total
across the project as of 2026-06-06).

Most informative tests (load-bearing for the inventory above):

- `test_drug_csv_shortlist_cns_fires_pipeline` (line 71) — happy path
  end-to-end activation.
- `test_schema_detector_range_check_drops_adversarial_column`
  (line 177) — proves the value-range guard kills a column labelled
  `hERG` with values in [0, 200].
- `test_uncertainty_margin_promotes_close_pass_to_ambiguous`
  (line 515) — the ±margin band behaviour.
- `test_required_gate_with_missing_column_disqualifies` (line 587) —
  Phase B safety-gate honest-DQ behaviour.
- `test_v2_eliminates_compounds_v1_called_ambiguous` (lines 408, 423,
  duplicated by name) — the 2026-06-04 BBB-tightening regression.
- `test_pipeline_empty_result_does_not_silently_relax` (line 453) —
  the "0 survivors is the truth" guarantee.
- `test_structural_sar_no_basic_amine_omits_amine_lever` (line 322)
  + `test_structural_sar_no_canonical_lever_emits_honest_fallback`
  (line 352) — the structural-precondition fix.
- `test_markdown_table_format_is_parsed_as_drug_csv` (line 783)
  + `test_compound_dossier_format_is_parsed_as_drug_csv` (line 801)
  + `test_combined_markdown_and_dossier_upload_merges_correctly`
  (line 837) — the multi-format normaliser the production raw_docs/
  pipeline depends on.
- `test_orchestrator_emits_audit_id_when_applied` (line 708) +
  `test_audit_entry_serialises_to_db_row` (line 740) +
  `test_hash_raw_text_is_stable` (line 769) — audit-trail invariants.

### Section (c) — what's solid / partial / missing

- **Solid:** seven versioned, immutable GateSets with explicit
  uncertainty bands; deterministic pipeline activation guarded by
  three independent confidence thresholds; per-compound CompoundAudit
  retains every gate result even past first failure (`gate.py:82-95`),
  giving the dossier full provenance; structural SAR levers are
  precondition-gated by RDKit SMARTS, with honest-fallback emission
  when no canonical lever applies; Supabase audit log with RLS and
  three indexes; replay-from-snapshot endpoint with belt-and-braces
  ownership check.
- **Partial:** `replay.py` docstring promises a `mode='live'`
  re-execution path against the cached raw text — the function only
  exposes the snapshot path, no `mode` parameter. The orchestrator's
  `SCHEMA_CONFIDENCE_THRESHOLD = 0.5` (`orchestrator.py:66`) is
  superseded in practice by the detector's stricter `≥0.6` rule
  (`detector.py:51-53`) — the 0.5 constant is misleading dead-letter.
- **Missing:** no LLM fallback for ambiguous prompts in either intent
  or indication classifier — `intent/classifier.py:18-21` and
  `indication/extractor.py:14-16` both list this as "Phase B". As of
  this commit it is still keyword-only. No per-axis sensitivity
  visualisation in the dossier beyond the textual `SensitivityAnalyzer`
  output. No CLI / programmatic re-run hook for refusing to ship a
  GateSet that hasn't been version-bumped (the rule that "once
  published, never edit in place" is enforced by convention only).

---

## Cross-section observations

- The "registry" pattern (Rule 37) is real in TableIntelligence
  (`library.py` archive + `_REGISTRY`) but only half-applied in RAG
  (`text_splitter.py` still reads `settings.LANGCHAIN_CHUNK_SIZE`, and
  `rag.py` still hardcodes an older embedding-version string).
- Two failure modes from the rules table — heavy-reasoning models
  silently dropping content, and provider-window-mismatch 413s — are
  both addressed for the chat path. The Lead Optimizer Vision Agent
  duplicates the reasoning-content salvage logic because it talks to a
  different endpoint shape; this is justifiable today but is duplicated
  code that will drift.
- "Dead but initialised" stragglers — NVIDIA NIM provider object;
  Cohere embedding service; `RAGConfig.validate_embedding_version`
  helper — are all callable from a Python REPL but unreachable from
  production code paths. Cleaning these up would be honest;
  documenting them is the minimum.

Sources cited above are the load-bearing files for each subsystem;
everything not cited (notes, summaries, README prose) was deliberately
ignored in favour of code as ground truth.
