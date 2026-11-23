#!/usr/bin/env python3
"""Dependency-free provider adapters: call a model API directly, without agy.

Supported providers: openai, anthropic, google. Model slugs must be passed by the
caller (this module never guesses a model id). Keys come from the environment:

  openai     OPENAI_API_KEY
  anthropic  ANTHROPIC_API_KEY
  google     GEMINI_API_KEY or GOOGLE_API_KEY

Extra knobs (optional):
  ORCHESTRA_OPENAI_BASE_URL, ORCHESTRA_ANTHROPIC_BASE_URL, ORCHESTRA_GOOGLE_BASE_URL
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

PROVIDERS = ("openai", "anthropic", "google")

KEY_ENV = {
    "openai": ("OPENAI_API_KEY",),
    "anthropic": ("ANTHROPIC_API_KEY",),
    "google": ("GEMINI_API_KEY", "GOOGLE_API_KEY"),
}

BASE_URL = {
    "openai": "https://api.openai.com/v1/chat/completions",
    "anthropic": "https://api.anthropic.com/v1/messages",
    "google": "https://generativelanguage.googleapis.com/v1beta/models",
}


def api_key(provider: str) -> str | None:
    for name in KEY_ENV.get(provider, ()):
        value = os.environ.get(name)
        if value:
            return value.strip()
    return None


def build_request(provider: str, model: str, prompt: str, max_tokens: int = 4000) -> dict[str, Any]:
    """Return {url, headers, body} for a single-turn completion request."""
    if provider not in PROVIDERS:
        raise ValueError(f"unknown provider {provider!r}; choose from {', '.join(PROVIDERS)}")
    if not model:
        raise ValueError("a model id is required for direct provider calls")

    if provider == "openai":
        url = os.environ.get("ORCHESTRA_OPENAI_BASE_URL") or BASE_URL["openai"]
        body = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_completion_tokens": max_tokens,
        }
        headers = {"content-type": "application/json"}
        return {"url": url, "headers": headers, "body": body}

    if provider == "anthropic":
        url = os.environ.get("ORCHESTRA_ANTHROPIC_BASE_URL") or BASE_URL["anthropic"]
        body = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        headers = {"content-type": "application/json", "anthropic-version": "2023-06-01"}
        return {"url": url, "headers": headers, "body": body}

    base = os.environ.get("ORCHESTRA_GOOGLE_BASE_URL") or BASE_URL["google"]
    url = f"{base.rstrip('/')}/{model}:generateContent"
    body = {"contents": [{"parts": [{"text": prompt}]}]}
    return {"url": url, "headers": {"content-type": "application/json"}, "body": body}


def parse_response(provider: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Extract text + normalized token usage from a provider response body."""
    text = ""
    usage: dict[str, int] = {}
    if provider == "openai":
        choices = payload.get("choices") or []
        if choices:
            message = choices[0].get("message") or {}
            content = message.get("content")
            text = content if isinstance(content, str) else json.dumps(content)
        raw = payload.get("usage") or {}
        usage = {
            "input_tokens": int(raw.get("prompt_tokens") or 0),
            "output_tokens": int(raw.get("completion_tokens") or 0),
        }
    elif provider == "anthropic":
        blocks = payload.get("content") or []
        text = "".join(block.get("text", "") for block in blocks if isinstance(block, dict))
        raw = payload.get("usage") or {}
        usage = {
            "input_tokens": int(raw.get("input_tokens") or 0),
            "output_tokens": int(raw.get("output_tokens") or 0),
        }
    elif provider == "google":
        candidates = payload.get("candidates") or []
        if candidates:
            parts = (candidates[0].get("content") or {}).get("parts") or []
            text = "".join(part.get("text", "") for part in parts if isinstance(part, dict))
        raw = payload.get("usageMetadata") or {}
        usage = {
            "input_tokens": int(raw.get("promptTokenCount") or 0),
            "output_tokens": int(raw.get("candidatesTokenCount") or 0),
        }
    return {"text": text.strip(), "usage": usage}


def complete(
    provider: str,
    model: str,
    prompt: str,
    timeout: int = 180,
    max_tokens: int = 4000,
) -> dict[str, Any]:
    """Run one completion. Returns {ok, text, usage, provider, model} or {ok: False, error}."""
    key = api_key(provider)
    if not key:
        envs = " or ".join(KEY_ENV.get(provider, ("<api key>",)))
        return {"ok": False, "provider": provider, "model": model, "error": f"missing API key: set {envs}"}
    try:
        request_spec = build_request(provider, model, prompt, max_tokens)
    except ValueError as exc:
        return {"ok": False, "provider": provider, "model": model, "error": str(exc)}

    url = request_spec["url"]
    headers = dict(request_spec["headers"])
    if provider == "openai":
        headers["authorization"] = f"Bearer {key}"
    elif provider == "anthropic":
        headers["x-api-key"] = key
    else:
        url = f"{url}?key={key}"

    data = json.dumps(request_spec["body"]).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
            status = response.status
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:600]
        return {
            "ok": False,
            "provider": provider,
            "model": model,
            "status": exc.code,
            "error": f"HTTP {exc.code}: {detail}",
        }
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return {"ok": False, "provider": provider, "model": model, "error": f"request failed: {exc}"}

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {
            "ok": False,
            "provider": provider,
            "model": model,
            "status": status,
            "error": f"non-JSON response: {raw[:300]}",
        }
    parsed = parse_response(provider, payload)
    return {
        "ok": bool(parsed["text"]) or status == 200,
        "provider": provider,
        "model": model,
        "status": status,
        "text": parsed["text"],
        "usage": parsed["usage"],
    }
