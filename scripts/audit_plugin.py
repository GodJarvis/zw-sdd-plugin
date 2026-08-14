#!/usr/bin/env python3
"""Audit the canonical ZW SDD plugin without third-party dependencies."""

from __future__ import annotations

import json
import re
import stat
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_NAME = "zw-sdd-plugin"
EXPECTED_SKILL_COUNT = 46
MANIFESTS = (
    ROOT / ".codex-plugin/plugin.json",
    ROOT / ".claude-plugin/plugin.json",
    ROOT / ".cursor-plugin/plugin.json",
)
MARKETPLACES = (
    ROOT / ".agents/plugins/marketplace.json",
    ROOT / ".claude-plugin/marketplace.json",
    ROOT / ".cursor-plugin/marketplace.json",
)
MERGED_WORKFLOWS = (
    "zwflow-apply",
    "zwflow-run",
    "zwflow-verify",
    "zwflow-deploy-doc-gen",
    "zwflow-yapi-doc-gen",
    "zwflow-qa-test",
)
FORBIDDEN_HOST_TERMS = re.compile(
    r"AskUserQuestion|request_user_input|TodoWrite|TaskCreate|TaskUpdate|"
    r"EnterPlanMode|update_plan|spawn_agent|subagent_type"
)
FORBIDDEN_HOST_PATHS = re.compile(r"\.(?:claude|agents|codex|cursor)/")
FRAMEWORK_MARKERS = re.compile(
    r"Hyperf|Phalcon|co-phpunit|config/autoload|run/cli\.php|"
    r"apps/|library/|hyperf-test|phalcon-test|amqp:consume|RabbitMq"
)


class Audit:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.checks = 0

    def require(self, condition: bool, message: str) -> None:
        self.checks += 1
        if not condition:
            self.errors.append(message)

    def load_json(self, path: Path) -> dict:
        self.require(path.is_file(), f"缺少 JSON 文件：{path.relative_to(ROOT)}")
        if not path.is_file():
            return {}
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            self.errors.append(f"JSON 无效：{path.relative_to(ROOT)}：{exc}")
            return {}
        self.require(isinstance(value, dict), f"JSON 顶层必须是对象：{path.relative_to(ROOT)}")
        return value if isinstance(value, dict) else {}

    def audit_manifests(self) -> None:
        manifests = [self.load_json(path) for path in MANIFESTS]
        versions = {item.get("version") for item in manifests}
        for path, manifest in zip(MANIFESTS, manifests, strict=True):
            rel = path.relative_to(ROOT)
            self.require(manifest.get("name") == PLUGIN_NAME, f"插件名不一致：{rel}")
            self.require(manifest.get("skills") == "./skills/", f"skills 路径不是 canonical 目录：{rel}")
            self.require(manifest.get("license") == "MIT", f"许可证不是 MIT：{rel}")
            self.require(bool(manifest.get("description")), f"缺少描述：{rel}")
        self.require(len(versions) == 1 and None not in versions, "三宿主 manifest 版本号不一致")

        for path in MARKETPLACES:
            market = self.load_json(path)
            plugins = market.get("plugins")
            self.require(isinstance(plugins, list) and len(plugins) == 1, f"市场插件条目异常：{path.relative_to(ROOT)}")
            if isinstance(plugins, list) and plugins:
                self.require(plugins[0].get("name") == PLUGIN_NAME, f"市场插件名不一致：{path.relative_to(ROOT)}")

        codex_market = self.load_json(ROOT / ".agents/plugins/marketplace.json")
        if codex_market.get("plugins"):
            entry = codex_market["plugins"][0]
            source = entry.get("source", {})
            self.require(source == {"source": "local", "path": "./"}, "Codex 市场 source 必须指向仓库根")
            self.require(entry.get("policy", {}).get("installation") == "AVAILABLE", "Codex 市场缺少安装策略")
            self.require(entry.get("policy", {}).get("authentication") == "ON_INSTALL", "Codex 市场缺少认证策略")

    def audit_skills(self) -> None:
        skill_dirs = sorted(path for path in (ROOT / "skills").iterdir() if path.is_dir())
        self.require(len(skill_dirs) == EXPECTED_SKILL_COUNT, f"skill 数量应为 {EXPECTED_SKILL_COUNT}，实际为 {len(skill_dirs)}")
        self.require(not (ROOT / "skills/claude-config-sync").exists(), "不应携带旧的跨目录复制 skill：claude-config-sync")

        names: list[str] = []
        for skill_dir in skill_dirs:
            skill_file = skill_dir / "SKILL.md"
            self.require(skill_file.is_file(), f"缺少 SKILL.md：{skill_dir.name}")
            if not skill_file.is_file():
                continue
            text = skill_file.read_text(encoding="utf-8")
            match = re.match(r"^---\n(?P<header>.*?)\n---\n", text, re.DOTALL)
            self.require(match is not None, f"frontmatter 无效：{skill_file.relative_to(ROOT)}")
            if not match:
                continue
            header = match.group("header")
            name_match = re.search(r"^name:\s*[\"']?([^\"'\n]+)[\"']?\s*$", header, re.MULTILINE)
            desc_match = re.search(r"^description:\s*.+$", header, re.MULTILINE)
            self.require(name_match is not None, f"frontmatter 缺少 name：{skill_dir.name}")
            self.require(desc_match is not None, f"frontmatter 缺少 description：{skill_dir.name}")
            if name_match:
                name = name_match.group(1).strip()
                names.append(name)
                self.require(name == skill_dir.name, f"skill 名与目录不一致：{skill_dir.name} != {name}")

        self.require(len(names) == len(set(names)), "存在重复 skill name")

        for path in (ROOT / "skills").rglob("*"):
            if not path.is_file() or path.suffix not in {".md", ".yaml", ".yml"}:
                continue
            text = path.read_text(encoding="utf-8")
            match = FORBIDDEN_HOST_TERMS.search(text)
            self.require(match is None, f"canonical skill 出现宿主工具名 {match.group(0) if match else ''}：{path.relative_to(ROOT)}")
            path_match = FORBIDDEN_HOST_PATHS.search(text)
            self.require(path_match is None, f"canonical skill 出现宿主配置路径：{path.relative_to(ROOT)}")

        for workflow in MERGED_WORKFLOWS:
            root = ROOT / "skills" / workflow
            for path in root.rglob("*.md"):
                if "references/frameworks" in path.as_posix():
                    continue
                text = path.read_text(encoding="utf-8")
                match = FRAMEWORK_MARKERS.search(text)
                self.require(match is None, f"框架细节未下沉（{match.group(0) if match else ''}）：{path.relative_to(ROOT)}")
            for framework in ("hyperf", "phalcon"):
                ref = root / f"references/frameworks/{framework}.md"
                self.require(ref.is_file(), f"缺少框架引用：{ref.relative_to(ROOT)}")

    def audit_openspec_assets(self) -> None:
        asset_root = ROOT / "skills/zw-sdd-init/assets/openspec"
        common = asset_root / "common"
        self.require((common / "GLOSSARY.md").is_file(), "OpenSpec common 缺少 GLOSSARY.md")
        self.require((common / "schemas/hotfix-workflow/schema.yaml").is_file(), "OpenSpec common 缺少 hotfix schema")
        self.require(not (common / "config.yaml").exists(), "框架 config.yaml 不应进入 common")
        self.require(not (common / "schemas/zw-workflow/schema.yaml").exists(), "框架 zw-workflow schema 不应进入 common")

        for framework in ("hyperf", "phalcon"):
            overlay = asset_root / "frameworks" / framework
            for relative in (
                "config.yaml",
                "schemas/zw-workflow/schema.yaml",
                "schemas/zw-workflow/templates/design.md",
                "schemas/zw-workflow/templates/tasks.md",
            ):
                self.require((overlay / relative).is_file(), f"OpenSpec overlay 缺少：{framework}/{relative}")

        installer = ROOT / "skills/zw-sdd-init/scripts/install_openspec.py"
        self.require(installer.is_file(), "缺少 OpenSpec 安装器")
        if installer.is_file():
            mode = installer.stat().st_mode
            self.require(bool(mode & stat.S_IXUSR), "OpenSpec 安装器缺少可执行权限")

    def audit_repository(self) -> None:
        for relative in ("README.md", "CHANGELOG.md", "LICENSE", "docs/architecture.md"):
            self.require((ROOT / relative).is_file(), f"缺少仓库文件：{relative}")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.require(f"{EXPECTED_SKILL_COUNT} 个 skills" in readme, "README skill 数量未同步")
        for path in ROOT.rglob("*"):
            if not path.is_file() or ".git" in path.parts:
                continue
            if path.resolve() == Path(__file__).resolve():
                continue
            if path.suffix not in {".md", ".json", ".yaml", ".yml", ".py"}:
                continue
            text = path.read_text(encoding="utf-8")
            self.require("Local developer" not in text, f"残留 scaffold 作者占位：{path.relative_to(ROOT)}")
            self.require("Zw Sdd Plugin plugin" not in text, f"残留 scaffold 描述：{path.relative_to(ROOT)}")

    def run(self) -> int:
        self.audit_manifests()
        self.audit_skills()
        self.audit_openspec_assets()
        self.audit_repository()
        if self.errors:
            print(f"[FAIL] ZW SDD 插件审计失败：{len(self.errors)} 项")
            for error in self.errors:
                print(f"- {error}")
            return 1
        print(f"[OK] ZW SDD 插件审计通过：{self.checks} 项检查，{EXPECTED_SKILL_COUNT} 个 canonical skills")
        return 0


if __name__ == "__main__":
    sys.exit(Audit().run())
