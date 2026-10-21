"""Preparation CLI. Run from the repository root with an explicit manifest."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import tempfile

from .prompts import render_skill_block
from .registry import load_registry, read_json
from .retrieval import select_skills
from .schema import RetrievalContext


def _parser():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ["lint", "list", "select", "render", "export"]:
        command = commands.add_parser(name)
        command.add_argument("--manifest", type=Path, required=True)
        if name in {"select", "render"}:
            command.add_argument("--context", type=Path, required=True)
            command.add_argument("--purpose", choices=["training", "validation"], default="training")
        if name == "render":
            command.add_argument("--max-chars", type=int, default=4000)
        if name == "export":
            command.add_argument("--output", type=Path, required=True)
            command.add_argument("--overwrite", action="store_true")
    return parser


def _dump(data):
    return json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def _export(path, data, overwrite):
    content = _dump(data)
    if not overwrite:
        with path.open("x", encoding="utf-8") as handle:
            handle.write(content)
        return
    # Write fully before replacing an existing export, avoiding partial snapshots.
    fd, name = tempfile.mkstemp(dir=path.parent, prefix=".spatial-skills-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def main(argv=None):
    args = _parser().parse_args(argv)
    try:
        registry = load_registry(args.manifest)
        if args.command == "lint":
            result = dict(library_version=registry.library_version, kind=registry.kind,
                          card_count=len(registry.list_cards()), digest=registry.digest,
                          untested_count=sum(c.validation_status == "untested" for c in registry.list_cards()))
        elif args.command == "list":
            result = [dict(id=c.id, version=c.version, name=c.name, task_families=c.task_families,
                           review_status=c.review_status, validation_status=c.validation_status)
                      for c in registry.list_cards()]
        elif args.command == "export":
            _export(args.output, registry.to_bundle(), args.overwrite)
            result = dict(output=str(args.output), digest=registry.digest)
        else:
            data = read_json(args.context)
            keys = {"task_family", "task_text", "public_history_text", "available_capabilities"}
            if not isinstance(data, dict) or set(data) != keys:
                raise ValueError("context must contain exactly the four public RetrievalContext fields")
            context = RetrievalContext(**data)
            selected = select_skills(registry, context, args.purpose)
            if args.command == "render":
                if selected.contains_untested:
                    print("Validation preview contains untested skills; effectiveness is unverified.", file=sys.stderr)
                block = render_skill_block([registry.get(i) for i in selected.selected_ids], args.max_chars)
                if block:
                    print(block)
                return 0
            result = selected.to_dict()
        print(_dump(result), end="")
        return 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
