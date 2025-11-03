#!/bin/bash

# 脚本名称
SCRIPT_NAME="阶段二和阶段三接口性能测试"

# 后端服务URL
BASE_URL="http://localhost:8000"

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查后端服务是否运行
check_backend_status() {
    local response=$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/health")
    if [ "$response" -eq 200 ]; then
        echo -e "${GREEN}✅ 后端服务运行正常${NC}"
        return 0
    else
        echo -e "${RED}❌ 后端服务未运行或不可达 (HTTP状态码: $response)${NC}"
        return 1
    fi
}

# 性能测试函数
perf_test() {
    local endpoint=$1
    local method=${2:-GET}
    local payload=${3:-""}
    local concurrent=${4:-10}
    local requests=${5:-100}
    local force_domain=${6:-"false"}

    local url="${BASE_URL}${endpoint}"
    if [ "$force_domain" = "true" ]; then
        url="${url}${endpoint}?force_domain=true"
    fi

    echo "--- 性能测试: ${method} ${endpoint} (force_domain=${force_domain}) ---"
    echo "并发数: ${concurrent}, 总请求数: ${requests}"

    # 使用Python脚本进行性能测试
    python3 <<EOF
import asyncio
import aiohttp
import time
import statistics
from typing import List

async def fetch(session, url, method, payload=None):
    start = time.time()
    try:
        if method == "GET":
            async with session.get(url) as response:
                await response.read()
                status = response.status
        elif method == "POST":
            async with session.post(url, json=payload) as response:
                await response.read()
                status = response.status
        elif method == "PUT":
            async with session.put(url, json=payload) as response:
                await response.read()
                status = response.status
        elif method == "DELETE":
            async with session.delete(url) as response:
                await response.read()
                status = response.status
        elapsed = (time.time() - start) * 1000  # 转换为毫秒
        return elapsed, status
    except Exception as e:
        elapsed = (time.time() - start) * 1000
        return elapsed, 0

async def run_perf_test(url, method, payload, concurrent, total_requests):
    connector = aiohttp.TCPConnector(limit=concurrent)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = []
        for i in range(total_requests):
            tasks.append(fetch(session, url, method, payload))

        results = await asyncio.gather(*tasks)

        latencies = [r[0] for r in results if r[1] == 200]
        statuses = [r[1] for r in results]

        if latencies:
            latencies.sort()
            p50 = latencies[len(latencies) // 2]
            p95 = latencies[int(len(latencies) * 0.95)]
            p99 = latencies[int(len(latencies) * 0.99)]
            avg = statistics.mean(latencies)
            max_latency = max(latencies)
            min_latency = min(latencies)

            success_count = statuses.count(200)
            success_rate = (success_count / len(statuses)) * 100
            qps = (success_count / (sum(latencies) / 1000)) if latencies else 0

            print(f"  成功请求: {success_count}/{len(statuses)} ({success_rate:.1f}%)")
            print(f"  QPS: {qps:.2f}")
            print(f"  平均延迟: {avg:.2f}ms")
            print(f"  P50延迟: {p50:.2f}ms")
            print(f"  P95延迟: {p95:.2f}ms")
            print(f"  P99延迟: {p99:.2f}ms")
            print(f"  最大延迟: {max_latency:.2f}ms")
            print(f"  最小延迟: {min_latency:.2f}ms")
        else:
            print(f"  ❌ 没有成功请求")

# 解析参数
import sys
url = sys.argv[1]
method = sys.argv[2]
concurrent = int(sys.argv[3])
requests = int(sys.argv[4])
payload = eval(sys.argv[5]) if len(sys.argv) > 5 and sys.argv[5] != "None" else None

asyncio.run(run_perf_test(url, method, payload, concurrent, requests))
EOF
}

# 主执行逻辑
echo "=========================================="
echo "$SCRIPT_NAME"
echo "=========================================="
echo ""

if ! check_backend_status; then
    exit 1
fi

echo ""
echo "开始性能测试..."
echo ""

# 阶段二接口性能测试（读操作）
echo "=== 阶段二接口（读操作）==="
echo ""

echo "1. GET /api/v1/system/info"
echo "  旧实现:"
python3 <<'PYEOF'
import asyncio
import aiohttp
import time
import statistics

async def fetch(session, url):
    start = time.time()
    try:
        async with session.get(url) as response:
            await response.read()
            status = response.status
        elapsed = (time.time() - start) * 1000
        return elapsed, status
    except Exception as e:
        elapsed = (time.time() - start) * 1000
        return elapsed, 0

async def run_test(url, concurrent=10, total=100):
    connector = aiohttp.TCPConnector(limit=concurrent)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [fetch(session, url) for _ in range(total)]
        results = await asyncio.gather(*tasks)
        latencies = [r[0] for r in results if r[1] == 200]
        if latencies:
            latencies.sort()
            print(f"    成功: {len(latencies)}/{total}, QPS: {len(latencies)/(sum(latencies)/1000):.2f}, P95: {latencies[int(len(latencies)*0.95)]:.2f}ms")
        else:
            print(f"    ❌ 没有成功请求")

asyncio.run(run_test("http://localhost:8000/api/v1/system/info"))
PYEOF

echo "  领域服务:"
python3 <<'PYEOF'
import asyncio
import aiohttp
import time
import statistics

async def fetch(session, url):
    start = time.time()
    try:
        async with session.get(url) as response:
            await response.read()
            status = response.status
        elapsed = (time.time() - start) * 1000
        return elapsed, status
    except Exception as e:
        elapsed = (time.time() - start) * 1000
        return elapsed, 0

async def run_test(url, concurrent=10, total=100):
    connector = aiohttp.TCPConnector(limit=concurrent)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [fetch(session, url) for _ in range(total)]
        results = await asyncio.gather(*tasks)
        latencies = [r[0] for r in results if r[1] == 200]
        if latencies:
            latencies.sort()
            print(f"    成功: {len(latencies)}/{total}, QPS: {len(latencies)/(sum(latencies)/1000):.2f}, P95: {latencies[int(len(latencies)*0.95)]:.2f}ms")
        else:
            print(f"    ❌ 没有成功请求")

asyncio.run(run_test("http://localhost:8000/api/v1/system/info?force_domain=true"))
PYEOF

echo ""
echo "2. GET /api/v1/alerts/history-db"
echo "  旧实现:"
python3 <<'PYEOF'
import asyncio
import aiohttp
import time

async def fetch(session, url):
    start = time.time()
    try:
        async with session.get(url) as response:
            await response.read()
            status = response.status
        elapsed = (time.time() - start) * 1000
        return elapsed, status
    except Exception as e:
        elapsed = (time.time() - start) * 1000
        return elapsed, 0

async def run_test(url, concurrent=10, total=100):
    connector = aiohttp.TCPConnector(limit=concurrent)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [fetch(session, url) for _ in range(total)]
        results = await asyncio.gather(*tasks)
        latencies = [r[0] for r in results if r[1] == 200]
        if latencies:
            latencies.sort()
            print(f"    成功: {len(latencies)}/{total}, QPS: {len(latencies)/(sum(latencies)/1000):.2f}, P95: {latencies[int(len(latencies)*0.95)]:.2f}ms")
        else:
            print(f"    ❌ 没有成功请求")

asyncio.run(run_test("http://localhost:8000/api/v1/alerts/history-db?limit=10"))
PYEOF

echo "  领域服务:"
python3 <<'PYEOF'
import asyncio
import aiohttp
import time

async def fetch(session, url):
    start = time.time()
    try:
        async with session.get(url) as response:
            await response.read()
            status = response.status
        elapsed = (time.time() - start) * 1000
        return elapsed, status
    except Exception as e:
        elapsed = (time.time() - start) * 1000
        return elapsed, 0

async def run_test(url, concurrent=10, total=100):
    connector = aiohttp.TCPConnector(limit=concurrent)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [fetch(session, url) for _ in range(total)]
        results = await asyncio.gather(*tasks)
        latencies = [r[0] for r in results if r[1] == 200]
        if latencies:
            latencies.sort()
            print(f"    成功: {len(latencies)}/{total}, QPS: {len(latencies)/(sum(latencies)/1000):.2f}, P95: {latencies[int(len(latencies)*0.95)]:.2f}ms")
        else:
            print(f"    ❌ 没有成功请求")

asyncio.run(run_test("http://localhost:8000/api/v1/alerts/history-db?limit=10&force_domain=true"))
PYEOF

echo ""
echo "3. GET /api/v1/alerts/rules"
echo "  旧实现:"
python3 <<'PYEOF'
import asyncio
import aiohttp
import time

async def fetch(session, url):
    start = time.time()
    try:
        async with session.get(url) as response:
            await response.read()
            status = response.status
        elapsed = (time.time() - start) * 1000
        return elapsed, status
    except Exception as e:
        elapsed = (time.time() - start) * 1000
        return elapsed, 0

async def run_test(url, concurrent=10, total=100):
    connector = aiohttp.TCPConnector(limit=concurrent)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [fetch(session, url) for _ in range(total)]
        results = await asyncio.gather(*tasks)
        latencies = [r[0] for r in results if r[1] == 200]
        if latencies:
            latencies.sort()
            print(f"    成功: {len(latencies)}/{total}, QPS: {len(latencies)/(sum(latencies)/1000):.2f}, P95: {latencies[int(len(latencies)*0.95)]:.2f}ms")
        else:
            print(f"    ❌ 没有成功请求")

asyncio.run(run_test("http://localhost:8000/api/v1/alerts/rules"))
PYEOF

echo "  领域服务:"
python3 <<'PYEOF'
import asyncio
import aiohttp
import time

async def fetch(session, url):
    start = time.time()
    try:
        async with session.get(url) as response:
            await response.read()
            status = response.status
        elapsed = (time.time() - start) * 1000
        return elapsed, status
    except Exception as e:
        elapsed = (time.time() - start) * 1000
        return elapsed, 0

async def run_test(url, concurrent=10, total=100):
    connector = aiohttp.TCPConnector(limit=concurrent)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [fetch(session, url) for _ in range(total)]
        results = await asyncio.gather(*tasks)
        latencies = [r[0] for r in results if r[1] == 200]
        if latencies:
            latencies.sort()
            print(f"    成功: {len(latencies)}/{total}, QPS: {len(latencies)/(sum(latencies)/1000):.2f}, P95: {latencies[int(len(latencies)*0.95)]:.2f}ms")
        else:
            print(f"    ❌ 没有成功请求")

asyncio.run(run_test("http://localhost:8000/api/v1/alerts/rules?force_domain=true"))
PYEOF

echo ""
echo "=== 阶段三写操作接口（谨慎测试）==="
echo ""

echo "⚠️  写操作接口性能测试需要更谨慎，建议使用小规模测试"
echo ""

echo "✅ 性能测试完成"
echo ""
echo "详细性能数据已收集，请查看上方输出"
