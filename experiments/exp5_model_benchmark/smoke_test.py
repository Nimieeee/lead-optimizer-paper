#!/usr/bin/env python3
"""
Smoke-test every provider with a tiny call before launching the full benchmark.
Verifies that API keys are set, network is reachable, and each provider's
response shape is what we expect.

Run:
    python3 smoke_test.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from providers import call, ProviderResponse


TINY_SYSTEM = "You are a JSON emitter. Reply with exactly the JSON {\"ok\": true} and nothing else."
TINY_USER = "ack"


PROBES = [
    ("openai",   "gpt-4o"),
    ("openai",   "gpt-5"),
    ("gemini",   "gemini-3-flash-preview"),
    ("opencode", "kimi-k2.6"),
    ("mistral",  "mistral-large-latest"),
    ("groq",     "openai/gpt-oss-120b"),
]


def env_status() -> dict:
    return {
        "OPENAI_API_KEY":      bool(os.environ.get("OPENAI_API_KEY")),
        "GEMINI_API_KEY":      bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")),
        "OPENCODE_GO_API_KEY": bool(os.environ.get("OPENCODE_GO_API_KEY")),
        "MISTRAL_API_KEY":     bool(os.environ.get("MISTRAL_API_KEY")),
        "GROQ_API_KEY":        bool(os.environ.get("GROQ_API_KEY")),
    }


async def main():
    print("=" * 60)
    print("Provider smoke test")
    print("=" * 60)
    print("Env keys present:")
    for k, v in env_status().items():
        print(f"  {k:25s} {'YES' if v else ', missing ,'}")
    print()

    results = []
    for provider, model in PROBES:
        print(f"  probing {provider:9s} / {model:40s} ...", end="", flush=True)
        # 2048 tokens, leaves room for reasoning-model internal CoT before the answer
        r = await call(provider, model, TINY_SYSTEM, TINY_USER, max_tokens=2048, timeout=60)
        if r.ok():
            print(f" OK [{r.runtime_s:.2f}s] {r.text[:80]!r}")
        else:
            print(f" FAIL [{r.runtime_s:.2f}s] {r.error}")
        results.append({
            "provider": provider, "model": model,
            "ok": r.ok(),
            "runtime_s": round(r.runtime_s, 2),
            "text": r.text[:200], "error": r.error,
            "usage_in": r.usage_in, "usage_out": r.usage_out,
        })

    out = HERE / "results" / "smoke.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"env": env_status(), "results": results}, indent=2))
    print()
    n_ok = sum(1 for r in results if r["ok"])
    print(f"  {n_ok}/{len(results)} providers responded OK")
    print(f"  results written to {out}")


if __name__ == "__main__":
    asyncio.run(main())
