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
    deleted = 0
    for base in base_paths:
        if not base:
            continue
        try:
            if not os.path.exists(base):
                continue
            for root, dirs, files in os.walk(base):
                for fn in files:
                    try:
                        if patterns:
                            ext = os.path.splitext(fn)[1].lower()
                            if ext not in patterns:
                                continue
                        fp = os.path.join(root, fn)
                        try:
                            st = os.stat(fp)
                            mtime = st.st_mtime
                        except Exception:
                            continue
                        if mtime < cutoff:
                            try:
                                os.remove(fp)
                                deleted += 1
                            except Exception:
                                pass
        except Exception:
            continue
    return deleted


