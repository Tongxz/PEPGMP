#!/usr/bin/env python3
"""
按保留期清理输出目录与日志文件。

默认目标：
- output/captures
- logs

用法：
  python scripts/cleanup_output.py --days 30 --dry-run
  python scripts/cleanup_output.py --days 14 --yes --paths output/captures logs
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from typing import Iterable, List


def iter_files(paths: Iterable[str]) -> Iterable[str]:
    for base in paths:
        if not os.path.exists(base):
            continue
        if os.path.isfile(base):
            yield base
            continue
        for root, _dirs, files in os.walk(base):
            for fn in files:
                yield os.path.join(root, fn)


def human_size(n: int) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if n < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024.0
    return f"{n:.1f}PB"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Cleanup output & logs by retention days"
    )
    parser.add_argument("--days", type=int, default=30, help="保留天数（删除早于该天数的文件）")
    parser.add_argument(
        "--paths", nargs="*", default=["output/captures", "logs"], help="要清理的路径列表"
    )
    parser.add_argument("--dry-run", action="store_true", help="仅预览将删除的内容，不实际删除")
    parser.add_argument("--yes", action="store_true", help="确认执行删除操作")
    args = parser.parse_args()

    now = time.time()
    ttl = float(args.days) * 86400.0
    remove_list: List[str] = []
    total_bytes = 0

    for fp in iter_files(args.paths):
        try:
            st = os.stat(fp)
            age = now - float(st.st_mtime)
            if age >= ttl:
                remove_list.append(fp)
                total_bytes += int(st.st_size)
        except FileNotFoundError:
            continue
        except Exception:
            continue

    print(f"将删除 {len(remove_list)} 个文件，累计约 {human_size(total_bytes)}（早于 {args.days} 天）")
    for fp in remove_list[:50]:
        print(" - ", fp)
    if len(remove_list) > 50:
        print(f" ... 其余 {len(remove_list) - 50} 个未列出")

    if args.dry_run or (not args.yes):
        print("预览模式（未执行删除）。如要执行，请添加 --yes 并去掉 --dry-run。")
        return 0

    removed = 0
    for fp in remove_list:
        try:
            os.remove(fp)
            removed += 1
        except Exception:
            continue
    print(f"已删除 {removed}/{len(remove_list)} 个文件。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
