#!/usr/bin/env python3
import hashlib
import json
import logging
import os
import re
import sys
from collections import OrderedDict
from pathlib import Path

BASE_DIR = Path(os.environ.get("ANON_HOME", str(Path.home() / ".local" / "share" / "anonimizador-dp")))
MODEL_DIR = Path(os.environ.get("ANON_MODEL", str(BASE_DIR / "model")))
FAIL_OPEN = os.environ.get("ANON_FAIL_OPEN") == "1"
CHUNK_CHARS = 50000
MAX_SESSIONS = 50
MAX_CACHE = 4000
TAG_PATTERN = re.compile(r"<\s*\|?\s*(\w+_\d+)\s*\|?\s*>")


class Masker:
    def __init__(self, extractor):
        self.extractor = extractor
        self.sessions = OrderedDict()
        self.cache = OrderedDict()

    def session(self, key: str) -> dict:
        state = self.sessions.get(key)
        if state is None:
            state = {"tags": {}, "values": {}, "counts": {}}
            self.sessions[key] = state
            while len(self.sessions) > MAX_SESSIONS:
                self.sessions.popitem(last=False)
        else:
            self.sessions.move_to_end(key)
        return state

    def entities(self, text: str) -> list:
        digest = hashlib.sha1(text.encode("utf-8")).hexdigest()
        cached = self.cache.get(digest)
        if cached is not None:
            return cached
        found = []
        offset = 0
        while offset < len(text):
            end = min(len(text), offset + CHUNK_CHARS)
            if end < len(text):
                cut = text.rfind("\n", offset, end)
                end = cut + 1 if cut > offset else end
            piece = text[offset:end]
            for entity in self.extractor.extract_entities(piece, return_type="label_position"):
                found.append((offset + entity["start_position"], offset + entity["end_position"], entity["label"]))
            offset = end
        found.sort()
        self.cache[digest] = found
        while len(self.cache) > MAX_CACHE:
            self.cache.popitem(last=False)
        return found

    def mask(self, text: str, state: dict) -> str:
        if not text:
            return text
        parts, cursor = [], 0
        for start, end, label in self.entities(text):
            if start < cursor:
                continue
            value = text[start:end]
            tag = state["tags"].get((label, value))
            if tag is None:
                state["counts"][label] = state["counts"].get(label, 0) + 1
                tag = f"<|{label}_{state['counts'][label]}|>"
                state["tags"][(label, value)] = tag
                state["values"][tag[2:-2]] = value
            parts.append(text[cursor:start])
            parts.append(tag)
            cursor = end
        parts.append(text[cursor:])
        return "".join(parts)


def restore(text: str, state: dict, json_safe: bool = False) -> str:
    if not text or not state["values"]:
        return text

    def swap(match):
        value = state["values"].get(match.group(1))
        if value is None:
            return match.group(0)
        return json.dumps(value, ensure_ascii=False)[1:-1] if json_safe else value

    return TAG_PATTERN.sub(swap, text)


def warn_system(message: dict, masker: Masker, state: dict) -> None:
    texts = [message.get("content")] + [p.get("text") for p in message.get("system_parts") or [] if isinstance(p, dict)]
    count = sum(len(masker.entities(t)) for t in texts if isinstance(t, str) and t)
    if count and state.get("warned") != count:
        state["warned"] = count
        sys.stderr.write(f"warning: system prompt contains {count} personal data item(s) the engine does not let hooks mask\n")
        sys.stderr.flush()


def mask_message(message: dict, masker: Masker, state: dict) -> dict:
    if message.get("role") == "system":
        warn_system(message, masker, state)
        return message
    out = dict(message)
    if isinstance(out.get("content"), str):
        out["content"] = masker.mask(out["content"], state)
    if isinstance(out.get("reasoning_content"), str):
        out["reasoning_content"] = masker.mask(out["reasoning_content"], state)
    if isinstance(out.get("system_parts"), list):
        out["system_parts"] = [
            {**p, "text": masker.mask(p.get("text", ""), state)} if isinstance(p, dict) else p
            for p in out["system_parts"]
        ]
    if isinstance(out.get("tool_calls"), list):
        calls = []
        for call in out["tool_calls"]:
            fn = call.get("function") if isinstance(call, dict) else None
            if fn and isinstance(fn.get("arguments"), str):
                call = {**call, "function": {**fn, "arguments": masker.mask(fn["arguments"], state)}}
            calls.append(call)
        out["tool_calls"] = calls
    return out


def session_key(params: dict) -> str:
    meta = params.get("meta") or {}
    return str(meta.get("SessionKey") or params.get("chat_id") or "default")


def before_llm(params: dict, masker: Masker) -> dict:
    state = masker.session(session_key(params))
    request = dict(params)
    request["messages"] = [mask_message(m, masker, state) for m in (params.get("messages") or [])]
    return {"action": "modify", "request": request}


def after_llm(params: dict, masker: Masker) -> dict:
    state = masker.session(session_key(params))
    response = dict(params.get("response") or {})
    for key in ("content", "reasoning_content", "reasoning"):
        if isinstance(response.get(key), str):
            response[key] = restore(response[key], state)
    if isinstance(response.get("tool_calls"), list):
        calls = []
        for call in response["tool_calls"]:
            fn = call.get("function") if isinstance(call, dict) else None
            if fn and isinstance(fn.get("arguments"), str):
                call = {**call, "function": {**fn, "arguments": restore(fn["arguments"], state, json_safe=True)}}
            calls.append(call)
        response["tool_calls"] = calls
    result = dict(params)
    result["response"] = response
    return {"action": "modify", "response": result}


def reply(request_id, result=None, error=None) -> None:
    body = {"jsonrpc": "2.0", "id": request_id}
    if error is not None:
        body["error"] = {"code": -32000, "message": error}
    else:
        body["result"] = result
    sys.stdout.write(json.dumps(body, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def load_masker() -> Masker:
    logging.getLogger("anonimizar").setLevel(logging.WARNING)
    from anonimizar import Anonimizar

    return Masker(Anonimizar(model_path=str(MODEL_DIR)))


def main() -> None:
    masker, load_error = None, None
    try:
        masker = load_masker()
    except Exception as exc:
        load_error = str(exc)
        sys.stderr.write(f"anonymizer failed to load: {exc}\n")
        sys.stderr.flush()
    handlers = {"hook.before_llm": before_llm, "hook.after_llm": after_llm}
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            continue
        method, request_id = request.get("method"), request.get("id")
        if request_id in (None, 0):
            continue
        if method == "hook.hello":
            reply(request_id, {"ok": True, "name": "pii-anonymizer"})
            continue
        handler = handlers.get(method)
        if handler is None:
            reply(request_id, {"action": "continue"})
            continue
        try:
            if masker is None:
                raise RuntimeError(load_error or "anonymizer not loaded")
            reply(request_id, handler(request.get("params") or {}, masker))
        except Exception as exc:
            sys.stderr.write(f"{method}: {exc}\n")
            sys.stderr.flush()
            if method == "hook.before_llm" and not FAIL_OPEN:
                reply(request_id, {"action": "abort_turn", "reason": "anonymizer unavailable; nothing was sent to the model"})
            else:
                reply(request_id, {"action": "continue"})


if __name__ == "__main__":
    main()
