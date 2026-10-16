#!/usr/bin/env python3
import argparse
import json
import shutil
import time
from pathlib import Path

NAME = "pii_anonymizer"
TIMEOUT_MS = 30000


def main() -> None:
    parser = argparse.ArgumentParser(description="Register the PII anonymizer hook in a picoclaw config.")
    parser.add_argument("config")
    parser.add_argument("--python", required=True)
    parser.add_argument("--hook", required=True)
    parser.add_argument("--anon-home", required=True)
    parser.add_argument("--priority", type=int, default=200)
    args = parser.parse_args()

    path = Path(args.config)
    config = json.loads(path.read_text(encoding="utf-8"))
    shutil.copy2(path, f"{path}.bak.pre-anonymizer.{int(time.time())}")

    hooks = config.setdefault("hooks", {})
    hooks["enabled"] = True
    defaults = hooks.setdefault("defaults", {})
    defaults["interceptor_timeout_ms"] = max(int(defaults.get("interceptor_timeout_ms", 0)), TIMEOUT_MS)
    hooks.setdefault("processes", {})[NAME] = {
        "enabled": True,
        "priority": args.priority,
        "transport": "stdio",
        "command": [args.python, args.hook],
        "intercept": ["before_llm", "after_llm", "before_tool"],
        "env": {"ANON_HOME": args.anon_home},
    }
    path.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"registered {NAME} in {path}")


if __name__ == "__main__":
    main()
