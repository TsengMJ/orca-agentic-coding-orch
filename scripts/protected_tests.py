#!/usr/bin/env python3
"""Freeze and check acceptance-test bytes.

arm writes sha256 of each path into aac/.run/<id>/protected-tests.json.
check exits 2 if any protected file is missing or its hash changed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from aac_common import ROOT


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def manifest_path(run_id: str) -> Path:
    return ROOT / "aac" / ".run" / run_id / "protected-tests.json"


def arm(run_id: str, paths: list[str]) -> dict:
    if not paths:
        raise SystemExit("refusing to arm an empty protected-test list")
    files = {}
    for rel in paths:
        path = ROOT / rel
        if not path.is_file():
            raise SystemExit(f"cannot protect missing file: {rel}")
        files[rel] = file_sha256(path)
    payload = {"run_id": run_id, "files": files}
    dest = manifest_path(run_id)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def check(run_id: str) -> list[str]:
    dest = manifest_path(run_id)
    if not dest.is_file():
        return ["protected-tests.json missing"]
    payload = json.loads(dest.read_text(encoding="utf-8"))
    files = payload.get("files") or {}
    if not files:
        return ["protected list is empty"]
    problems = []
    for rel, expected in files.items():
        path = ROOT / rel
        if not path.is_file():
            problems.append(f"missing {rel}")
            continue
        actual = file_sha256(path)
        if actual != expected:
            problems.append(f"hash changed {rel}")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--arm", nargs="+", metavar="PATH")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.arm:
        payload = arm(args.run_id, args.arm)
        print(f"armed {len(payload['files'])} file(s)")
        return 0
    problems = check(args.run_id)
    if problems:
        print("PROTECTED TEST CHECK FAILED", file=sys.stderr)
        for item in problems:
            print(f"- {item}", file=sys.stderr)
        return 2
    print("protected tests unchanged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
