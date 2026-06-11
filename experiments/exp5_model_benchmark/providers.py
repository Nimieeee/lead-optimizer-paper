"""
Unified provider abstraction for the cross-model benchmark.

Each provider exposes a single async function:

    await call(model: str, system: str, user: str, image_b64: str|None) -> ProviderResponse

ProviderResponse is a dataclass with .text (the raw assistant response),
runtime_s, usage tokens (when reported), error (if any), and provider+model
echoed for trace.

Five providers implemented:
  - openai   (OpenAI SDK)
  - gemini   (google-genai SDK)
  - opencode (httpx, OAI-compat at https://opencode.ai/zen/go/v1)
  - mistral  (httpx, Mistral REST)
  - groq     (groq SDK)

All keys read from environment variables only. Nothing is persisted to disk.
"""

from __future__ import annotations

import asyncio
import base64
import os
import time
from dataclasses import dataclass, field
from typing import Optional

import httpx


# ──────────────────────────────────────────────────────────────


@dataclass
class ProviderResponse:
    provider: str
    model: str
    text: str = ""
    runtime_s: float = 0.0
    usage_in: int = 0
    usage_out: int = 0
    error: Optional[str] = None
    raw: dict = field(default_factory=dict)

    def ok(self) -> bool:
        return self.error is None and bool(self.text)


def _img_data_url(image_b64: str) -> str:
    return f"data:image/png;base64,{image_b64}"


# ──────────────────────────────────────────────────────────────
# OpenAI


def _is_reasoning_model(model: str) -> bool:
    """OpenAI reasoning models, gpt-5*, o1*, o3*, o4*.
    These burn output tokens on internal CoT; need bigger budget."""
    m = model.lower()
    return m.startswith("gpt-5") or m.startswith("o1") or m.startswith("o3") or m.startswith("o4")


async def call_openai(model: str, system: str, user: str, image_b64: Optional[str] = None,
                      max_tokens: int = 8192, timeout: float = 180.0) -> ProviderResponse:
    from openai import AsyncOpenAI
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        return ProviderResponse(provider="openai", model=model, error="OPENAI_API_KEY missing")

    client = AsyncOpenAI(api_key=key, timeout=timeout)
    if image_b64:
        user_content = [
            {"type": "text", "text": user},
            {"type": "image_url", "image_url": {"url": _img_data_url(image_b64)}},
        ]
    else:
        user_content = user

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user_content},
    ]

    # Reasoning models need a much larger output budget, internal CoT chews
    # through the cap before producing the visible answer.
    effective_max = max(max_tokens, 16384) if _is_reasoning_model(model) else max_tokens

    # response_format json_object, enforces JSON-only output when the
    # system prompt asks for JSON. Most OpenAI chat models support it;
    # fall back silently if a model rejects.
    wants_json = "json" in (system or "").lower()

    t0 = time.perf_counter()
    # Retry on 429 with exponential backoff
    delays = [2, 4, 8, 16]
    last_err = None
    for attempt in range(5):
        try:
            kwargs = {"model": model, "messages": messages}
            if wants_json:
                kwargs["response_format"] = {"type": "json_object"}
            try:
                resp = await client.chat.completions.create(max_completion_tokens=effective_max, **kwargs)
            except Exception:
                # Older / non-reasoning models: max_tokens (and may not support response_format)
                kwargs.pop("response_format", None)
                resp = await client.chat.completions.create(max_tokens=effective_max, **kwargs)

            text = (resp.choices[0].message.content or "").strip()
            usage_in = getattr(resp.usage, "prompt_tokens", 0) or 0
            usage_out = getattr(resp.usage, "completion_tokens", 0) or 0
            return ProviderResponse(
                provider="openai", model=model, text=text,
                runtime_s=time.perf_counter() - t0,
                usage_in=usage_in, usage_out=usage_out,
            )
        except Exception as e:
            last_err = f"{type(e).__name__}: {e}"
            # Only retry transient errors
            msg = str(e).lower()
            if "429" in msg or "rate" in msg or "503" in msg or "overload" in msg:
                if attempt < 4:
                    await asyncio.sleep(delays[attempt])
                    continue
            break

    return ProviderResponse(
        provider="openai", model=model,
        runtime_s=time.perf_counter() - t0,
        error=last_err,
    )


# ──────────────────────────────────────────────────────────────
# Google Gemini


async def call_gemini(model: str, system: str, user: str, image_b64: Optional[str] = None,
                      max_tokens: int = 8192, timeout: float = 90.0) -> ProviderResponse:
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        return ProviderResponse(provider="gemini", model=model, error="GEMINI_API_KEY missing")

    try:
        from google import genai
        from google.genai import types as gtypes
    except ImportError:
        return ProviderResponse(provider="gemini", model=model, error="google-genai not installed")

    client = genai.Client(api_key=key)

    parts = [gtypes.Part.from_text(text=user)]
    if image_b64:
        parts.append(gtypes.Part.from_bytes(data=base64.b64decode(image_b64), mime_type="image/png"))

    # Enforce JSON-only when the system instruction asks for it
    wants_json = "json" in (system or "").lower()
    cfg_kwargs = {
        "system_instruction": system,
        "max_output_tokens": max_tokens,
        "temperature": 0.2,
    }
    if wants_json:
        cfg_kwargs["response_mime_type"] = "application/json"
    config = gtypes.GenerateContentConfig(**cfg_kwargs)

    t0 = time.perf_counter()
    delays = [2, 4, 8, 16]
    last_err = None
    for attempt in range(5):
        try:
            loop = asyncio.get_event_loop()
            resp = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: client.models.generate_content(
                        model=model,
                        contents=[gtypes.Content(role="user", parts=parts)],
                        config=config,
                    ),
                ),
                timeout=timeout,
            )
            text = (resp.text or "").strip() if hasattr(resp, "text") and resp.text else ""
            usage_in = getattr(resp.usage_metadata, "prompt_token_count", 0) if getattr(resp, "usage_metadata", None) else 0
            usage_out = getattr(resp.usage_metadata, "candidates_token_count", 0) if getattr(resp, "usage_metadata", None) else 0
            return ProviderResponse(
                provider="gemini", model=model, text=text,
                runtime_s=time.perf_counter() - t0,
                usage_in=usage_in, usage_out=usage_out,
            )
        except Exception as e:
            last_err = f"{type(e).__name__}: {e}"
            msg = str(e).lower()
            if "503" in msg or "unavailable" in msg or "high demand" in msg or "timeout" in msg or "429" in msg:
                if attempt < 4:
                    await asyncio.sleep(delays[attempt])
                    continue
            break
    return ProviderResponse(
        provider="gemini", model=model,
        runtime_s=time.perf_counter() - t0,
        error=last_err,
    )


# ──────────────────────────────────────────────────────────────
# OpenCode Go (OAI-compat)


OPENCODE_BASE = "https://opencode.ai/zen/go/v1"


async def call_opencode(model: str, system: str, user: str, image_b64: Optional[str] = None,
                        max_tokens: int = 8192, timeout: float = 90.0) -> ProviderResponse:
    key = os.environ.get("OPENCODE_GO_API_KEY")
    if not key:
        return ProviderResponse(provider="opencode", model=model, error="OPENCODE_GO_API_KEY missing")

    if image_b64:
        user_content = [
            {"type": "text", "text": user},
            {"type": "image_url", "image_url": {"url": _img_data_url(image_b64)}},
        ]
    else:
        user_content = user

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user_content},
        ],
        "max_tokens": max_tokens,
        "temperature": 0.2,
        "stream": False,
    }
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

    t0 = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(f"{OPENCODE_BASE}/chat/completions", json=payload, headers=headers)
            if resp.status_code != 200:
                return ProviderResponse(
                    provider="opencode", model=model,
                    runtime_s=time.perf_counter() - t0,
                    error=f"HTTP {resp.status_code}: {resp.text[:300]}",
                )
            body = resp.json()
            choice = (body.get("choices") or [{}])[0]
            msg = choice.get("message") or {}
            text = (msg.get("content") or "").strip()
            # OpenCode also returns reasoning_content for thinking models, silently dropped here.
            usage = body.get("usage") or {}
            return ProviderResponse(
                provider="opencode", model=model, text=text,
                runtime_s=time.perf_counter() - t0,
                usage_in=usage.get("prompt_tokens", 0),
                usage_out=usage.get("completion_tokens", 0),
            )
    except Exception as e:
        return ProviderResponse(
            provider="opencode", model=model,
            runtime_s=time.perf_counter() - t0,
            error=f"{type(e).__name__}: {e}",
        )


# ──────────────────────────────────────────────────────────────
# Mistral


MISTRAL_BASE = "https://api.mistral.ai/v1"


async def call_mistral(model: str, system: str, user: str, image_b64: Optional[str] = None,
                       max_tokens: int = 8192, timeout: float = 90.0) -> ProviderResponse:
    key = os.environ.get("MISTRAL_API_KEY")
    if not key:
        return ProviderResponse(provider="mistral", model=model, error="MISTRAL_API_KEY missing")

    if image_b64:
        user_content = [
            {"type": "text", "text": user},
            {"type": "image_url", "image_url": _img_data_url(image_b64)},
        ]
    else:
        user_content = user

    wants_json = "json" in (system or "").lower()
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user_content},
        ],
        "max_tokens": max_tokens,
        "temperature": 0.2,
    }
    if wants_json:
        payload["response_format"] = {"type": "json_object"}
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

    t0 = time.perf_counter()
    delays = [2, 4, 8, 16, 30]
    last_err = None
    for attempt in range(6):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(f"{MISTRAL_BASE}/chat/completions", json=payload, headers=headers)
                if resp.status_code == 429:
                    last_err = f"HTTP 429 (rate-limit retry {attempt + 1}/6)"
                    if attempt < 5:
                        await asyncio.sleep(delays[attempt])
                        continue
                if resp.status_code != 200:
                    return ProviderResponse(
                        provider="mistral", model=model,
                        runtime_s=time.perf_counter() - t0,
                        error=f"HTTP {resp.status_code}: {resp.text[:300]}",
                    )
                body = resp.json()
                choice = (body.get("choices") or [{}])[0]
                text = ((choice.get("message") or {}).get("content") or "").strip()
                usage = body.get("usage") or {}
                return ProviderResponse(
                    provider="mistral", model=model, text=text,
                    runtime_s=time.perf_counter() - t0,
                    usage_in=usage.get("prompt_tokens", 0),
                    usage_out=usage.get("completion_tokens", 0),
                )
        except Exception as e:
            last_err = f"{type(e).__name__}: {e}"
            if "429" in str(e) and attempt < 5:
                await asyncio.sleep(delays[attempt])
                continue
            break
    return ProviderResponse(
        provider="mistral", model=model,
        runtime_s=time.perf_counter() - t0,
        error=last_err,
    )


# ──────────────────────────────────────────────────────────────
# Groq


async def call_groq(model: str, system: str, user: str, image_b64: Optional[str] = None,
                    max_tokens: int = 8192, timeout: float = 90.0) -> ProviderResponse:
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        return ProviderResponse(provider="groq", model=model, error="GROQ_API_KEY missing")

    from groq import AsyncGroq
    client = AsyncGroq(api_key=key, timeout=timeout)

    if image_b64:
        user_content = [
            {"type": "text", "text": user},
            {"type": "image_url", "image_url": {"url": _img_data_url(image_b64)}},
        ]
    else:
        user_content = user

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user_content},
    ]

    t0 = time.perf_counter()
    try:
        resp = await client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=0.2,
        )
        text = (resp.choices[0].message.content or "").strip()
        usage_in = getattr(resp.usage, "prompt_tokens", 0)
        usage_out = getattr(resp.usage, "completion_tokens", 0)
        return ProviderResponse(
            provider="groq", model=model, text=text,
            runtime_s=time.perf_counter() - t0,
            usage_in=usage_in, usage_out=usage_out,
        )
    except Exception as e:
        return ProviderResponse(
            provider="groq", model=model,
            runtime_s=time.perf_counter() - t0,
            error=f"{type(e).__name__}: {e}",
        )


# ──────────────────────────────────────────────────────────────
# Dispatcher


PROVIDERS = {
    "openai":   call_openai,
    "gemini":   call_gemini,
    "opencode": call_opencode,
    "mistral":  call_mistral,
    "groq":     call_groq,
}


async def call(provider: str, model: str, system: str, user: str,
               image_b64: Optional[str] = None, max_tokens: int = 8192,
               timeout: float = 90.0) -> ProviderResponse:
    fn = PROVIDERS.get(provider)
    if fn is None:
        return ProviderResponse(provider=provider, model=model, error=f"unknown provider {provider!r}")
    return await fn(model, system, user, image_b64=image_b64, max_tokens=max_tokens, timeout=timeout)
