#!/usr/bin/env python3
"""
数据库初始化脚本
用于创建数据库表和插入初始数据

使用方式：
    python -m scripts.init_database
"""

import asyncio
import logging

from src.database.init_db import main

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

if __name__ == "__main__":
    asyncio.run(main())
