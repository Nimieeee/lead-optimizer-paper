import asyncio
import base64
import json
import logging
from typing import Optional, List, Dict
from groq import AsyncGroq
import httpx
from app.core.config import settings
from ..schemas import VisionAgentOutput
from ..prompts import VISION_AGENT_SYSTEM_PROMPT
from ..chemistry_validator import is_valid_interaction, normalize_group_name

logger = logging.getLogger(__name__)

# Vision model chain (primary → fallback). MiniMax M3 via OpenCode Go's
# Anthropic-compat endpoint is Tier 1, user-requested upgrade for stronger
# perception on Ligand Interaction Diagrams (multi-residue arrow counting,
# scaffold vs decoration discrimination). Pixtral Large stays as Tier 2
# because Mistral API is independent of OpenCode Go (so a key/quota issue
# on one doesn't take both out). Scout stays as the broadly-accessible
# Tier 3 baseline.
import os
# OpenCode Go MiniMax wiring is intentionally DISABLED by default.
# - M3 is vision-capable but reasoning-only, burns the entire token budget
#   on `thinking` blocks and never emits final JSON, even with prefill.
# - M2.5 / M2.7 are text-only (confirmed 2026-06-06), would 4xx on image input.
# Set MINIMAX_VISION_MODEL explicitly to opt back in once a non-reasoning,
# vision-capable model lands on the Anthropic-compat endpoint.
MINIMAX_VISION_MODEL = os.getenv("MINIMAX_VISION_MODEL", "")
# Kimi K2.6 via OpenCode Go's OAI-compat endpoint (2026-06-09 experiment).
# Set to "" to disable. CLAUDE.md flags Kimi as heavy-reasoning, we handle
# the case where the model returns `reasoning_content` but empty `content`
# by extracting JSON from the reasoning trace.
KIMI_VISION_MODEL = os.getenv("KIMI_VISION_MODEL", "kimi-k2.6")
PIXTRAL_MODEL = "pixtral-large-latest"
GROQ_SCOUT_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
OPENCODE_GO_CHAT_URL = "https://opencode.ai/zen/go/v1/chat/completions"

# OpenCode Go ships an Anthropic-compatible endpoint for MiniMax/Qwen at
# /v1/messages, payload shape and response structure match Anthropic's,
# not OAI's. Vision support uses {"type": "image", "source": {...}} content
# blocks, not OAI's image_url. Mistral keeps the OAI-shaped path.
OPENCODE_GO_MESSAGES_URL = "https://opencode.ai/zen/go/v1/messages"
MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"


def _extract_json_object(text: str) -> Optional[dict]:
    """Robust JSON extractor, finds the first { and scans for matching }.

    MiniMax via Anthropic-compat does NOT honour response_format={"type":
    "json_object"} (the OAI knob); it returns text that may have markdown
    fences, leading prose, or trailing notes. We strip those and recover the
    outer JSON object. Same pattern used in deep_research.py / multi_provider
    parsers (Rule 22).
    """
    if not text:
        return None
    s = text.strip()
    # Strip ``` fences if present
    if s.startswith("```"):
        nl = s.find("\n")
        if nl != -1:
            s = s[nl + 1 :]
        if s.endswith("```"):
            s = s[:-3]
        s = s.strip()
    # Find first { and matching close
    start = s.find("{")
    if start == -1:
        return None
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(s)):
        ch = s[i]
        if esc:
            esc = False
            continue
        if ch == "\\":
            esc = True
            continue
        if ch == '"':
            in_str = not in_str
            continue
        if in_str:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(s[start : i + 1])
                except json.JSONDecodeError:
                    return None
    return None


async def _call_minimax_m3(formatted_prompt: str, b64_image: str) -> Optional[dict]:
    """MiniMax M3 via OpenCode Go's Anthropic-compat endpoint (/v1/messages).

    User-requested PRIMARY for Vision Agent. Anthropic message shape:
      messages: [{role: user, content: [
        {type: "image", source: {type: "base64", media_type: "image/png", data: <b64>}},
        {type: "text", text: <prompt>}
      ]}]
    Response shape:
      {content: [{type: "text", text: "..."}, ...], stop_reason: ...}

    No response_format JSON mode, we rely on the prompt's "JSON ONLY" rule
    + _extract_json_object() to recover the object even if the model wraps
    it in prose or ``` fences.
    """
    api_key = settings.OPENCODE_GO_API_KEY
    if not api_key:
        logger.debug("VisionAgent.MiniMax: OPENCODE_GO_API_KEY not set; skipping")
        return None
    if not MINIMAX_VISION_MODEL:
        # Explicitly disabled, see the comment on MINIMAX_VISION_MODEL above.
        return None

    # Anthropic prefill trick: add a final assistant message containing just
    # `{` so the model continues from there with raw JSON instead of
    # reasoning prose. Without this, MiniMax M3 spends its entire max_tokens
    # budget in `thinking` blocks and never emits the final JSON. With it,
    # the model jumps straight to the structured output we asked for.
    # max_tokens bumped to 4096 so even verbose reasoning + JSON fits.
    payload = {
        "model": MINIMAX_VISION_MODEL,
        "max_tokens": 4096,
        "temperature": 0.0,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": b64_image,
                        },
                    },
                    {"type": "text", "text": formatted_prompt},
                ],
            },
            {
                "role": "assistant",
                "content": "{",
            },
        ],
    }
    # OpenCode Go's Anthropic-compat endpoint follows Anthropic's auth scheme:
    # `x-api-key` header, not `Authorization: Bearer`. Verified 2026-06-06 after
    # the initial Bearer-token attempt returned 401 "Missing API key".
    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01",
    }
    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.post(OPENCODE_GO_MESSAGES_URL, headers=headers, json=payload)
            if resp.status_code != 200:
                logger.warning(f"VisionAgent.MiniMax: HTTP {resp.status_code}, {resp.text[:300]}")
                return None
            data = resp.json()
            # MiniMax M3 on OpenCode Go returns content blocks with a `thinking`
            # field instead of (or alongside) the standard `text` field, the
            # model is reasoning-first and its final answer is embedded in the
            # reasoning prose. Our _extract_json_object helper finds the outer
            # { ... } regardless of surrounding prose, so we treat `thinking`
            # content as a usable text source.
            text = ""
            content_blocks = data.get("content") or []
            if isinstance(content_blocks, list):
                # Prefer typed text blocks (canonical Anthropic shape)
                text_blocks = [b for b in content_blocks if isinstance(b, dict) and b.get("type") == "text"]
                if text_blocks:
                    text = "".join(b.get("text", "") for b in text_blocks)
                # Then any block carrying a `text` field
                if not text:
                    text = "".join(
                        b.get("text", "") for b in content_blocks
                        if isinstance(b, dict) and b.get("text")
                    )
                # Then `thinking` blocks (MiniMax M3 shape)
                if not text:
                    text = "".join(
                        b.get("thinking", "") for b in content_blocks
                        if isinstance(b, dict) and b.get("thinking")
                    )
            elif isinstance(content_blocks, str):
                text = content_blocks
            # Last-resort root-level fallbacks
            if not text:
                text = data.get("text") or data.get("completion") or ""

            if not text:
                # Log the response keys + a snippet so we can see what's actually returned
                keys = list(data.keys()) if isinstance(data, dict) else type(data).__name__
                snippet = json.dumps(data)[:500] if isinstance(data, dict) else str(data)[:500]
                logger.warning(
                    f"VisionAgent.MiniMax: response had no text content blocks. "
                    f"keys={keys} snippet={snippet}"
                )
                return None

            # Prefill recovery: since we prefilled the assistant turn with `{`,
            # the model's response continues from inside the JSON object, the
            # first `{` is missing from the response text. Prepend it before
            # extraction so _extract_json_object can find the outer braces.
            if not text.lstrip().startswith("{"):
                text = "{" + text

            parsed = _extract_json_object(text)
            if parsed is None:
                # We got text but couldn't find a JSON object. M3's reasoning
                # may have stopped before emitting JSON. Log the tail of the
                # text so we can see whether to retry, switch model, or
                # prefill the assistant turn with `{` to force JSON.
                logger.warning(
                    f"VisionAgent.MiniMax: text extracted but no JSON object found. "
                    f"text_len={len(text)} tail={text[-400:]!r}"
                )
            return parsed
    except Exception as e:
        logger.warning(f"VisionAgent.MiniMax call failed: {e}")
        return None


async def _call_pixtral(formatted_prompt: str, b64_image: str) -> Optional[dict]:
    """Pixtral Large via Mistral. Returns parsed JSON dict or None on error.

    Used as PRIMARY because Pixtral has stronger fine-grained perception on
    Ligand Interaction Diagrams (counts secondary H-bonds, distinguishes
    scaffold methyls from decorations). 128K context, JSON mode supported.
    """
    if not settings.MISTRAL_API_KEY:
        logger.debug("VisionAgent.Pixtral: MISTRAL_API_KEY not set; skipping")
        return None

    payload = {
        "model": PIXTRAL_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": formatted_prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_image}"}},
                ],
            }
        ],
        "temperature": 0.0,
        "random_seed": 42,
        "max_tokens": 2048,
        "response_format": {"type": "json_object"},
    }
    headers = {
        "Authorization": f"Bearer {settings.MISTRAL_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(MISTRAL_API_URL, headers=headers, json=payload)
            if resp.status_code != 200:
                logger.warning(f"VisionAgent.Pixtral: HTTP {resp.status_code}, {resp.text[:200]}")
                return None
            content = resp.json()["choices"][0]["message"]["content"]
            return json.loads(content)
    except Exception as e:
        logger.warning(f"VisionAgent.Pixtral call failed: {e}")
        return None


async def _call_kimi_k2(formatted_prompt: str, b64_image: str) -> Optional[dict]:
    """Kimi K2.6 via OpenCode Go's OAI-compat /v1/chat/completions endpoint.

    CLAUDE.md flags Kimi as heavy-reasoning: it may emit thousands of chars
    of `reasoning_content` before any user-visible `content`. We extract
    from `content` first; on empty content, fall back to `reasoning_content`
    + _extract_json_object to recover JSON embedded in the reasoning trace.
    """
    api_key = settings.OPENCODE_GO_API_KEY
    if not api_key or not KIMI_VISION_MODEL:
        return None

    payload = {
        "model": KIMI_VISION_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": formatted_prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_image}"}},
                ],
            }
        ],
        "temperature": 0.0,
        "max_tokens": 4096,
        "response_format": {"type": "json_object"},
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(OPENCODE_GO_CHAT_URL, headers=headers, json=payload)
            if resp.status_code != 200:
                logger.warning(f"VisionAgent.Kimi: HTTP {resp.status_code}, {resp.text[:300]}")
                return None
            data = resp.json()

            # OAI shape: choices[0].message.{content, reasoning_content}
            choice = data.get("choices", [{}])[0] if data.get("choices") else {}
            msg = choice.get("message", {}) if isinstance(choice, dict) else {}
            text = (msg.get("content") or "") if isinstance(msg, dict) else ""

            # Heavy-reasoning fallback: extract from reasoning_content if main content is empty
            if not text and isinstance(msg, dict):
                text = msg.get("reasoning_content") or ""
                if text:
                    logger.warning(
                        f"VisionAgent.Kimi: only reasoning_content present "
                        f"(len={len(text)}); extracting JSON from reasoning trace"
                    )

            if not text:
                keys = list(data.keys())
                msg_keys = list(msg.keys()) if isinstance(msg, dict) else "n/a"
                logger.warning(
                    f"VisionAgent.Kimi: empty response. data keys={keys} message keys={msg_keys} "
                    f"snippet={json.dumps(data)[:300]}"
                )
                return None
            return _extract_json_object(text)
    except Exception as e:
        logger.warning(f"VisionAgent.Kimi call failed: {e}")
        return None


async def _call_groq_scout(formatted_prompt: str, b64_image: str) -> Optional[dict]:
    """Groq Llama 4 Scout 17B fallback. Returns parsed JSON dict or None on error.

    Used when Pixtral is unavailable or returns an empty payload. Fast (TTFT ~200ms)
    and broadly accessible, but weaker perception than Pixtral on diagrams with
    multiple overlapping interaction arrows.
    """
    if not settings.GROQ_API_KEY:
        return None
    try:
        client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        response = await client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": formatted_prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_image}"}},
                    ],
                }
            ],
            model=GROQ_SCOUT_MODEL,
            temperature=0.0,
            seed=42,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        return json.loads(content)
    except Exception as e:
        logger.warning(f"VisionAgent.GroqScout call failed: {e}")
        return None


def _payload_is_useful(parsed: dict) -> bool:
    """A parsed Vision Agent JSON is useful if it has at least one classified group."""
    if not parsed:
        return False
    if parsed.get("restricted_groups"):
        return True
    if parsed.get("target_groups"):
        return True
    return False


async def run_vision_agent(
    lead_smiles: str,
    diagram_bytes: bytes,
    visual_hints: str = "",
    detected_groups: List[str] = None,
    max_retries: int = 3,
    progress_callback=None,
    labeled_instances: Optional[List[Dict]] = None,
) -> VisionAgentOutput:
    """
    Analyse a 2D Ligand Interaction Diagram (LID).

    Provider chain (user-requested 2026-06-06):
      Tier 1: MiniMax M3 via OpenCode Go's Anthropic-compat endpoint
      Tier 2: Pixtral Large via Mistral
      Tier 3: Groq Llama 4 Scout 17B
    Each tier retries up to max_retries times; cross-tier fallback fires
    when a tier is unavailable OR returns an empty payload.

    Architecture (Approach A):
    - Group DETECTION is handled by RDKit pre_scan_molecule() BEFORE this call.
      `detected_groups` is the authoritative list of what functional groups exist.
    - This function only CLASSIFIES groups as RESTRICTED (binding) or TARGET (modifiable),
      lists ALL contacting residues per group, and optionally flags additional
      scaffold atoms.
    - `visual_hints` provides extra context about the LID (e.g. legend colour codes).
    """
    if not settings.MISTRAL_API_KEY and not settings.GROQ_API_KEY:
        raise RuntimeError("Neither MISTRAL_API_KEY nor GROQ_API_KEY configured, Vision Agent has no provider")

    b64_image = base64.b64encode(diagram_bytes).decode("utf-8")
    # Build the detected-groups block. When labeled_instances are available
    # (the per-instance enumeration from pre_scan_molecule), use them as the
    # unit of classification, gives the Vision Agent stable LID-positional
    # anchors for distinguishing multi-instance matches (two phenyl rings,
    # six aromatic_h positions). Falls back to bare names for older callers.
    if labeled_instances:
        lines = []
        # Group by base name for readability while still listing each instance
        for inst in labeled_instances:
            label = inst.get("label") or inst.get("name", "unknown")
            base = inst.get("name", label)
            hint = inst.get("position_hint", "")
            atoms = inst.get("atom_indices") or []
            if label == base:
                # Single match, no per-instance label needed
                lines.append(f"- {label}  (position: {hint}, atoms: {atoms})")
            else:
                lines.append(f"- {label}  (chemistry: {base}, position: {hint}, atoms: {atoms})")
        detected_str = "\n".join(lines)
    else:
        detected_str = "\n".join(f"- {g}" for g in (detected_groups or []))
    visual_hint_block = f"\n\nVISUAL HINTS:\n{visual_hints}" if visual_hints else ""
    formatted_prompt = VISION_AGENT_SYSTEM_PROMPT.format(
        detected_groups=detected_str,
        visual_hints=visual_hint_block,
    )

    parsed: Optional[dict] = None
    used_provider = "none"

    async def _emit(percent: int, detail: str):
        """Forward progress to orchestrator if a callback is plumbed in.
        Best-effort, never crash the agent on a progress emit failure."""
        if progress_callback is None:
            return
        try:
            await progress_callback("vision", percent, detail)
        except Exception as e:
            logger.debug(f"VisionAgent: progress emit failed: {e}")

    # Tier 1: Groq Scout (promoted 2026-06-11 from Tier 3 fallback per
    # Exp 5 benchmark, Llama 4 Scout 17B-16e tied for top with Jaccard=1.0,
    # 100% JSON validity, 9.5 s mean latency, free quota).
    # See paper/experiments/exp5_model_benchmark/results/stage2_summary.json.
    for attempt in range(max_retries):
        await _emit(6, f"Querying Groq Scout (attempt {attempt + 1}/{max_retries})…")
        candidate = await _call_groq_scout(formatted_prompt, b64_image)
        if _payload_is_useful(candidate):
            parsed = candidate
            used_provider = "groq-llama4-scout-17b"
            break
        if attempt < max_retries - 1:
            await asyncio.sleep(1.5)

    # Tier 2: Pixtral Large. Benchmark Jaccard 0.786, 100% JSON (after backoff).
    if parsed is None:
        for attempt in range(max_retries):
            await _emit(7, f"Falling back to Pixtral Large (attempt {attempt + 1}/{max_retries})…")
            logger.warning(f"VisionAgent: falling back to Pixtral Large, attempt {attempt + 1}/{max_retries}")
            candidate = await _call_pixtral(formatted_prompt, b64_image)
            if _payload_is_useful(candidate):
                parsed = candidate
                used_provider = "pixtral-large"
                break
            if attempt < max_retries - 1:
                await asyncio.sleep(1.5)

    # Tier 3: Kimi K2.6 (demoted from Tier 1, 0% JSON validity in Exp 5;
    # the model refuses strict-JSON instructions, so keep as last-chance).
    if parsed is None and KIMI_VISION_MODEL:
        for attempt in range(max_retries):
            await _emit(8, f"Falling back to Kimi K2.6 (attempt {attempt + 1}/{max_retries})…")
            logger.warning(f"VisionAgent: falling back to Kimi K2.6, attempt {attempt + 1}/{max_retries}")
            candidate = await _call_kimi_k2(formatted_prompt, b64_image)
            if _payload_is_useful(candidate):
                parsed = candidate
                used_provider = f"opencode-go-{KIMI_VISION_MODEL}"
                break
            if attempt < max_retries - 1:
                await asyncio.sleep(1.5)

    # Tier 4: MiniMax M3 (disabled by default, heavy reasoning, env-gated).
    if parsed is None and MINIMAX_VISION_MODEL:
        for attempt in range(max_retries):
            await _emit(9, f"Falling back to MiniMax M3 (attempt {attempt + 1}/{max_retries})…")
            candidate = await _call_minimax_m3(formatted_prompt, b64_image)
            if _payload_is_useful(candidate):
                parsed = candidate
                used_provider = f"opencode-go-{MINIMAX_VISION_MODEL}"
                break
            if attempt < max_retries - 1:
                await asyncio.sleep(1.5)

    if parsed is None:
        logger.error("❌ VisionAgent: all providers exhausted (Scout + Pixtral + Kimi + MiniMax), returning empty output")
        return VisionAgentOutput(restricted_groups=[], target_groups=[], overall_confidence=0.0)

    await _emit(9, f"Validating chemistry from {used_provider}…")
    logger.info(f"✅ VisionAgent: used {used_provider}")
    restricted = parsed.get("restricted_groups", []) or []
    target = parsed.get("target_groups", []) or []
    scaffold_atoms = parsed.get("scaffold_atoms", []) or []
    # Backwards-compat: if an older Vision Agent prompt still emits
    # structural_core_groups, merge them into target. The chemist's
    # correction (2026-06-09): there is no third category, scaffold
    # atoms are EDITABLE unless they make a visible protein contact.
    legacy_structural = parsed.get("structural_core_groups", []) or []
    if legacy_structural:
        logger.info(f"VisionAgent: merging {len(legacy_structural)} legacy structural_core_groups into target_groups")
        target = list(target) + list(legacy_structural)
    structural_core = []  # always empty under new policy; preserved field for schema compat

    # ── Guard rails: drop hallucinations + chemically impossible classifications ──
    # Two checks per entry, in order:
    #   1. group_name (or its base if labeled) must appear in the RDKit-detected list
    #   2. (base group_name, interaction_type) must be chemically possible
    # Multi-residue entries are pruned per-index so a partial match survives
    # the valid subset only.
    detected_set = {normalize_group_name(g) for g in (detected_groups or [])}
    # Build a label → base map from the labeled instances so we can validate
    # both labels ("phenyl_left") and bare names ("phenyl") consistently
    label_to_base: Dict[str, str] = {}
    for inst in (labeled_instances or []):
        label_to_base[normalize_group_name(inst.get("label", ""))] = normalize_group_name(inst.get("name", ""))

    def _base_for_validation(label_norm: str) -> str:
        """Return the base group name for chemistry / detection validation."""
        if label_norm in label_to_base:
            return label_to_base[label_norm]
        # Try progressive suffix stripping (e.g. "phenyl_left" → "phenyl")
        parts = label_norm.split("_")
        for cut in range(len(parts), 0, -1):
            cand = "_".join(parts[:cut])
            if cand in detected_set:
                return cand
        return label_norm

    def _filter_restricted(entries):
        kept = []
        for e in entries:
            label_norm = normalize_group_name(e.get("group_name") or "")
            if not label_norm:
                logger.warning("VisionAgent: dropping entry with blank group_name")
                continue
            base_name = _base_for_validation(label_norm)
            if detected_set and base_name not in detected_set:
                logger.warning(f"VisionAgent: dropping hallucinated group '{label_norm}' (base '{base_name}' not in detected)")
                continue

            # Multi-residue path: filter per-index, keep valid subset
            itypes = e.get("interaction_types") or []
            residues = e.get("residues") or []
            if itypes:
                valid_pairs = [
                    (residues[i] if i < len(residues) else None, t)
                    for i, t in enumerate(itypes)
                    if is_valid_interaction(base_name, t)
                ]
                if not valid_pairs:
                    logger.warning(f"VisionAgent: dropping '{label_norm}', no chemically valid interactions in {itypes}")
                    continue
                e["interaction_types"] = [t for _, t in valid_pairs]
                e["residues"] = [r for r, _ in valid_pairs if r is not None]
                # Also keep the legacy singular fields aligned to the first valid pair
                e["interaction_type"] = valid_pairs[0][1]
                if valid_pairs[0][0]:
                    e["residue"] = valid_pairs[0][0]
            else:
                # Single-interaction path
                itype = e.get("interaction_type") or "hydrophobic"
                if not is_valid_interaction(base_name, itype):
                    logger.warning(f"VisionAgent: dropping chemically invalid ({label_norm} → base {base_name}, {itype})")
                    continue
            kept.append(e)
        return kept

    def _filter_target(entries):
        kept = []
        for e in entries:
            label_norm = normalize_group_name(e.get("group_name") or "")
            if not label_norm:
                continue
            base_name = _base_for_validation(label_norm)
            if detected_set and base_name not in detected_set:
                logger.warning(f"VisionAgent: dropping hallucinated target '{label_norm}' (base '{base_name}' not in detected)")
                continue
            kept.append(e)
        return kept

    cleaned_restricted = _filter_restricted(restricted)
    cleaned_structural = _filter_target(structural_core)  # same shape as target, name validation only
    cleaned_target = _filter_target(target)

    if (
        len(cleaned_restricted) != len(restricted)
        or len(cleaned_target) != len(target)
        or len(cleaned_structural) != len(structural_core)
    ):
        logger.info(
            f"VisionAgent: validator kept {len(cleaned_restricted)}/{len(restricted)} restricted, "
            f"{len(cleaned_structural)}/{len(structural_core)} structural_core, "
            f"{len(cleaned_target)}/{len(target)} target"
        )

    # Pydantic's model_validator on FunctionalGroupInteraction handles both
    # legacy {residue: str} and new {residues: [...]} shapes, no manual
    # normalisation needed here.
    return VisionAgentOutput(
        restricted_groups=cleaned_restricted,
        structural_core_groups=cleaned_structural,
        target_groups=cleaned_target,
        overall_confidence=parsed.get("overall_confidence", 0.85),
        scaffold_atoms=[int(a) for a in scaffold_atoms if isinstance(a, (int, float))],
    )
