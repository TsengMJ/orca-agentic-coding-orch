#!/usr/bin/env python3
"""Resolve AAC slot runtime/model/args from config/workflow.yaml."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    print("PyYAML required: uv run --with pyyaml scripts/resolve_slot.py …", file=sys.stderr)
    sys.exit(2)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config" / "workflow.yaml"


def _truthy(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def load_config(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"invalid config: {path}")
    return data


def apply_env_overrides(cfg: dict) -> dict:
    slots = cfg.setdefault("slots", {})
    for name in ("A", "B", "I"):
        model_env = os.environ.get(f"AAC_SLOT_{name}_MODEL")
        if model_env:
            slot = slots.get(name)
            if slot is None:
                slots[name] = {"runtime": "cursor", "model": model_env, "args": []}
            elif isinstance(slot, dict):
                slot["model"] = model_env

    gates = cfg.setdefault("gates", {})
    if "AAC_GATE_CMD" in os.environ:
        gates["gate_cmd"] = os.environ["AAC_GATE_CMD"]
    if "AAC_BUILD_GATE_CMD" in os.environ:
        gates["build_gate_cmd"] = os.environ["AAC_BUILD_GATE_CMD"]
    if "AAC_MAX_ROUNDS" in os.environ:
        gates["max_rounds"] = int(os.environ["AAC_MAX_ROUNDS"])
    if "AAC_HUMAN_GATE" in os.environ:
        gates["human_gate"] = _truthy(os.environ["AAC_HUMAN_GATE"])
    if "AAC_HUMAN_GATE_PLAN" in os.environ:
        gates["human_gate_plan"] = _truthy(os.environ["AAC_HUMAN_GATE_PLAN"])
    if "AAC_OPEN_PR" in os.environ:
        gates["open_pr"] = _truthy(os.environ["AAC_OPEN_PR"])
    if "AAC_AGENT_CALL_RETRIES" in os.environ:
        gates["agent_call_retries"] = int(os.environ["AAC_AGENT_CALL_RETRIES"])
    if "AAC_AGENT_TIMEOUT_SEC" in os.environ:
        gates["agent_timeout_sec"] = int(os.environ["AAC_AGENT_TIMEOUT_SEC"])
    if "AAC_NOTIFY_CMD" in os.environ:
        gates["notify_cmd"] = os.environ["AAC_NOTIFY_CMD"]
    return cfg


def stage_model_override(cfg: dict, name: str, stage: str | None) -> str | None:
    """Return stage_models[stage][slot] when set."""
    if not stage:
        return None
    name = name.upper()
    stages = cfg.get("stage_models") or {}
    row = stages.get(stage) or {}
    if not isinstance(row, dict):
        return None
    value = row.get(name)
    if value is None and name == "I":
        # Implementer may fall back to the owner's stage model.
        owner = str((cfg.get("roles") or {}).get("owner") or "A").upper()
        value = row.get(owner)
    if value is None or str(value).strip() == "":
        return None
    return str(value).strip()


def resolve_slot(cfg: dict, name: str, stage: str | None = None) -> dict:
    name = name.upper()
    if name not in {"A", "B", "I"}:
        raise SystemExit(f"slot must be A, B, or I (got {name})")

    slots = cfg.get("slots") or {}
    roles = cfg.get("roles") or {}
    raw = slots.get(name)

    if name == "I" and raw is None:
        owner = str(roles.get("owner") or "A").upper()
        raw = slots.get(owner)
        inherited_from = owner
    else:
        inherited_from = None

    if not isinstance(raw, dict):
        raise SystemExit(f"slot {name} is not configured")

    model = stage_model_override(cfg, name, stage) or raw.get("model")
    out = {
        "slot": name,
        "runtime": raw.get("runtime") or "cursor",
        "model": model,
        "args": list(raw.get("args") or []),
        "inherited_from": inherited_from,
        "stage": stage,
        "owner": str(roles.get("owner") or "A").upper(),
        "reviewer": str(roles.get("reviewer") or "B").upper(),
    }
    if not out["model"]:
        raise SystemExit(f"slot {name} missing model")
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("slot", help="A | B | I")
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
        help="path to workflow.yaml",
    )
    parser.add_argument(
        "--stage",
        default="",
        help="optional stage key from stage_models (spec|plan|acceptance|implement|gate|final)",
    )
    parser.add_argument(
        "--field",
        choices=("runtime", "model", "args", "json", "all"),
        default="all",
        help="print one field (default: human one-liner)",
    )
    args = parser.parse_args()

    cfg = apply_env_overrides(load_config(args.config))
    resolved = resolve_slot(cfg, args.slot, stage=args.stage or None)

    if args.field == "json":
        print(json.dumps(resolved, indent=2))
    elif args.field == "runtime":
        print(resolved["runtime"])
    elif args.field == "model":
        print(resolved["model"])
    elif args.field == "args":
        print(json.dumps(resolved["args"]))
    else:
        inherit = f" (inherit {resolved['inherited_from']})" if resolved["inherited_from"] else ""
        stage = f" stage={resolved['stage']}" if resolved.get("stage") else ""
        print(f"{resolved['slot']}{inherit}{stage}: {resolved['runtime']} / {resolved['model']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
