from __future__ import annotations

import os
import time
from typing import Iterable, List, Optional


def cleanup_old_files(
    base_paths: Iterable[str],
    days: int = 30,
    patterns: Optional[List[str]] = None,
) -> int:
    """删除 base_paths 下早于 days 天的文件，返回删除数量。

    - base_paths: 需要清理的目录（不存在则忽略）
    - days: 保留天数，早于该天数的文件会被删除
    - patterns: 仅限定后缀（如 ['.jpg','.mp4','.json']），为空则不限制
    """
    now = time.time()
    cutoff = now - float(days) * 86400.0
    deleted_count = 0

    for base_path in base_paths:
        if not base_path or not os.path.exists(base_path):
            continue

        for root, _, files in os.walk(base_path):
            for filename in files:
                try:
                    if (
                        patterns
                        and os.path.splitext(filename)[1].lower() not in patterns
                    ):
                        continue

                    filepath = os.path.join(root, filename)

                    # os.path.getmtime can raise FileNotFoundError, so we handle it.
                    mtime = os.path.getmtime(filepath)

                    if mtime < cutoff:
                        os.remove(filepath)
                        deleted_count += 1
                except (OSError, FileNotFoundError):
                    # This can happen if the file is deleted between os.walk and os.remove,
                    # or if there are permission issues. We'll just skip it.
                    continue

    return deleted_count
