#!/usr/bin/env python3
"""Install or verify the framework-specific OpenSpec assets bundled with ZW SDD."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
ASSET_ROOT = SKILL_ROOT / "assets" / "openspec"
SUPPORTED_FRAMEWORKS = ("hyperf", "phalcon")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def composer_packages(root: Path) -> set[str]:
    path = root / "composer.json"
    if not path.is_file():
        return set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    packages: set[str] = set()
    for section in ("require", "require-dev"):
        values = data.get(section, {})
        if isinstance(values, dict):
            packages.update(str(name).lower() for name in values)
    return packages


def detect_framework(root: Path) -> str:
    packages = composer_packages(root)
    hyperf = any(name.startswith("hyperf/") for name in packages) or (root / "bin/hyperf.php").is_file()
    phalcon = (
        any("phalcon" in name for name in packages)
        or (root / "run/cli.php").is_file()
        or ((root / "apps").is_dir() and (root / "library").is_dir())
    )
    if hyperf == phalcon:
        state = "conflicting" if hyperf else "missing"
        raise ValueError(f"framework evidence is {state}; pass --framework hyperf or --framework phalcon")
    return "hyperf" if hyperf else "phalcon"


def asset_map(framework: str) -> dict[Path, Path]:
    sources: dict[Path, Path] = {}
    for layer in (ASSET_ROOT / "common", ASSET_ROOT / "frameworks" / framework):
        for source in sorted(path for path in layer.rglob("*") if path.is_file()):
            sources[source.relative_to(layer)] = source
    return sources


def classify(target_root: Path, sources: dict[Path, Path]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {"create": [], "update": [], "unchanged": []}
    for relative, source in sources.items():
        target = target_root / "openspec" / relative
        if not target.exists():
            result["create"].append(relative.as_posix())
        elif target.is_file() and sha256(target) == sha256(source):
            result["unchanged"].append(relative.as_posix())
        else:
            result["update"].append(relative.as_posix())
    return result


def install(target_root: Path, sources: dict[Path, Path], changes: dict[str, list[str]], force: bool) -> None:
    if changes["update"] and not force:
        raise RuntimeError("managed files differ; inspect the reported update list or rerun with --force")
    writable = set(changes["create"])
    if force:
        writable.update(changes["update"])
    for relative, source in sources.items():
        if relative.as_posix() not in writable:
            continue
        target = target_root / "openspec" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=Path, default=Path.cwd(), help="target project root")
    parser.add_argument("--framework", choices=("auto", *SUPPORTED_FRAMEWORKS), default="auto")
    parser.add_argument("--check", action="store_true", help="verify without writing")
    parser.add_argument("--dry-run", action="store_true", help="show planned changes without writing")
    parser.add_argument("--force", action="store_true", help="replace differing managed files")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    target = args.target.expanduser().resolve()
    if not target.is_dir():
        print(json.dumps({"error": f"target directory does not exist: {target}"}, ensure_ascii=False))
        return 2
    try:
        framework = detect_framework(target) if args.framework == "auto" else args.framework
        sources = asset_map(framework)
        changes = classify(target, sources)
        report = {"framework": framework, "target": str(target), **changes}
        if args.check:
            report["status"] = "ok" if not changes["create"] and not changes["update"] else "drift"
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0 if report["status"] == "ok" else 1
        if args.dry_run:
            report["status"] = "dry-run"
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0
        install(target, sources, changes, args.force)
        report["status"] = "installed"
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, RuntimeError) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False, indent=2))
        return 2


if __name__ == "__main__":
    sys.exit(main())
