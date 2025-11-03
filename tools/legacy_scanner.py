# -*- coding: utf-8 -*-
"""
遗留清理候选扫描器
- 构建 src/ 下的 import 依赖图
- 以入口点集合为根（api/app、tests、examples、scripts、tools）做可达性分析
- 输出未被引用的模块候选到 reports/legacy_cleanup_report.json/.md

使用:
  python tools/legacy_scanner.py
"""
import os
import re
import ast
import json
from pathlib import Path
from typing import Dict, Set, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
REPORT_DIR = ROOT / "reports"

ENTRY_FILES = [
    SRC / "api" / "app.py",
]
ENTRY_DIRS = [
    ROOT / "tests",
    ROOT / "examples",
    ROOT / "scripts",
    ROOT / "tools",
    SRC / "api",
]

MODULE_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def path_to_module(p: Path) -> str:
    try:
        rel = p.relative_to(SRC)
    except ValueError:
        return ""
    parts = list(rel.parts)
    if not parts:
        return ""
    if parts[-1].endswith(".py"):
        parts[-1] = parts[-1][:-3]
    return ".".join(["src"] + [x for x in parts if x and MODULE_RE.match(x)])


def iter_py_files(root: Path) -> List[Path]:
    out: List[Path] = []
    for p in root.rglob("*.py"):
        # 排除 __pycache__ 等
        if "__pycache__" in p.parts:
            continue
        out.append(p)
    return out


def parse_imports(py: Path) -> Set[str]:
    try:
        code = py.read_text(encoding="utf-8")
        tree = ast.parse(code)
    except Exception:
        return set()
    mods: Set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                if isinstance(n.name, str):
                    mods.add(n.name)
        elif isinstance(node, ast.ImportFrom):
            if isinstance(node.module, str):
                mods.add(node.module)
    return mods


def build_graph() -> Tuple[Dict[str, Set[str]], Dict[str, Path]]:
    module_to_path: Dict[str, Path] = {}
    graph: Dict[str, Set[str]] = {}
    files = iter_py_files(SRC)
    for f in files:
        mod = path_to_module(f)
        if not mod:
            continue
        module_to_path[mod] = f
    for mod, f in module_to_path.items():
        imports = parse_imports(f)
        deps: Set[str] = set()
        for imp in imports:
            # 仅保留以 src. 开头的项目内部模块
            if imp == "src" or imp.startswith("src."):
                deps.add(imp)
        graph[mod] = deps
    return graph, module_to_path


def derive_entry_modules(module_to_path: Dict[str, Path]) -> Set[str]:
    entries: Set[str] = set()
    # 显式入口文件
    for f in ENTRY_FILES:
        if f.exists():
            m = path_to_module(f)
            if m:
                entries.add(m)
    # 入口目录中的 import
    for d in ENTRY_DIRS:
        if not d.exists():
            continue
        for f in iter_py_files(d):
            imports = parse_imports(f)
            for imp in imports:
                if imp == "src" or imp.startswith("src."):
                    entries.add(imp)
    return entries


def reachable(graph: Dict[str, Set[str]], roots: Set[str]) -> Set[str]:
    seen: Set[str] = set()
    stack: List[str] = list(roots)
    while stack:
        m = stack.pop()
        if m in seen:
            continue
        seen.add(m)
        for dep in graph.get(m, ()):  # type: ignore
            if dep not in seen:
                stack.append(dep)
    return seen


def main() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    graph, module_to_path = build_graph()
    roots = derive_entry_modules(module_to_path)
    reach = reachable(graph, roots)

    # 候选：src.* 中未可达的模块
    unused: List[Dict[str, str]] = []
    for mod, p in sorted(module_to_path.items()):
        if mod not in reach:
            unused.append({"module": mod, "path": str(p.relative_to(ROOT))})

    summary = {
        "roots": sorted(list(roots)),
        "total_modules": len(module_to_path),
        "reachable": len(reach),
        "unused_count": len(unused),
        "unused_modules": unused,
    }

    (REPORT_DIR / "legacy_cleanup_report.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # 生成 markdown 摘要
    lines: List[str] = []
    lines.append("# 遗留清理候选报告")
    lines.append("")
    lines.append(f"- 入口模块数: {len(roots)}")
    lines.append(f"- 模块总数: {len(module_to_path)}")
    lines.append(f"- 可达模块: {len(reach)}")
    lines.append(f"- 未引用候选: {len(unused)}")
    lines.append("")
    if unused:
        lines.append("## 未引用候选列表（建议逐一人工确认）")
        for item in unused[:200]:
            lines.append(f"- {item['module']} -> `{item['path']}`")
        if len(unused) > 200:
            lines.append(f"… 其余 {len(unused) - 200} 项已省略")
    else:
        lines.append("未发现明显未引用模块")

    (REPORT_DIR / "legacy_cleanup_report.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )

    print(json.dumps({"ok": True, "report": str((REPORT_DIR / 'legacy_cleanup_report.json'))}))


if __name__ == "__main__":
    main()
