#!/usr/bin/env python3
"""
前端构建优化工具
Frontend Build Optimizer

用于优化前端构建过程，包括资源压缩、合并、缓存等
"""

import gzip
import json
import logging
import mimetypes
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class FrontendBuildOptimizer:
    """前端构建优化器"""

    def __init__(
        self, frontend_dir: str = "frontend", output_dir: str = "frontend/dist"
    ):
        self.frontend_dir = Path(frontend_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 支持压缩的文件类型
        self.compressible_types = {
            "text/html",
            "text/css",
            "text/javascript",
            "application/javascript",
            "application/json",
            "text/plain",
            "text/xml",
            "application/xml",
        }

        # 文件扩展名映射
        self.extension_map = {
            ".html": "text/html",
            ".css": "text/css",
            ".js": "application/javascript",
            ".json": "application/json",
            ".txt": "text/plain",
            ".xml": "application/xml",
        }

    def optimize_html_files(self) -> Dict[str, Any]:
        """优化HTML文件"""
        logger.info("开始优化HTML文件...")

        html_files = list(self.frontend_dir.glob("*.html"))
        optimization_results = []

        for html_file in html_files:
            logger.info(f"优化HTML文件: {html_file.name}")

            # 读取原始文件
            with open(html_file, "r", encoding="utf-8") as f:
                content = f.read()

            # 执行优化
            optimized_content = self._optimize_html_content(content)

            # 保存优化后的文件
            output_file = self.output_dir / html_file.name
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(optimized_content)

            # 压缩文件
            compressed_file = self._compress_file(output_file)

            # 记录优化结果
            original_size = html_file.stat().st_size
            optimized_size = output_file.stat().st_size
            compressed_size = (
                compressed_file.stat().st_size if compressed_file else optimized_size
            )

            optimization_results.append(
                {
                    "file": html_file.name,
                    "original_size": original_size,
                    "optimized_size": optimized_size,
                    "compressed_size": compressed_size,
                    "compression_ratio": (1 - compressed_size / original_size) * 100
                    if original_size > 0
                    else 0,
                }
            )

        return {"total_files": len(html_files), "results": optimization_results}

    def optimize_css_files(self) -> Dict[str, Any]:
        """优化CSS文件"""
        logger.info("开始优化CSS文件...")

        css_files = list(self.frontend_dir.glob("*.css"))
        optimization_results = []

        for css_file in css_files:
            logger.info(f"优化CSS文件: {css_file.name}")

            # 读取原始文件
            with open(css_file, "r", encoding="utf-8") as f:
                content = f.read()

            # 执行CSS优化
            optimized_content = self._optimize_css_content(content)

            # 保存优化后的文件
            output_file = self.output_dir / css_file.name
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(optimized_content)

            # 压缩文件
            compressed_file = self._compress_file(output_file)

            # 记录优化结果
            original_size = css_file.stat().st_size
            optimized_size = output_file.stat().st_size
            compressed_size = (
                compressed_file.stat().st_size if compressed_file else optimized_size
            )

            optimization_results.append(
                {
                    "file": css_file.name,
                    "original_size": original_size,
                    "optimized_size": optimized_size,
                    "compressed_size": compressed_size,
                    "compression_ratio": (1 - compressed_size / original_size) * 100
                    if original_size > 0
                    else 0,
                }
            )

        return {"total_files": len(css_files), "results": optimization_results}

    def optimize_js_files(self) -> Dict[str, Any]:
        """优化JavaScript文件"""
        logger.info("开始优化JavaScript文件...")

        js_files = list(self.frontend_dir.glob("*.js"))
        optimization_results = []

        for js_file in js_files:
            logger.info(f"优化JavaScript文件: {js_file.name}")

            # 读取原始文件
            with open(js_file, "r", encoding="utf-8") as f:
                content = f.read()

            # 执行JavaScript优化
            optimized_content = self._optimize_js_content(content)

            # 保存优化后的文件
            output_file = self.output_dir / js_file.name
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(optimized_content)

            # 压缩文件
            compressed_file = self._compress_file(output_file)

            # 记录优化结果
            original_size = js_file.stat().st_size
            optimized_size = output_file.stat().st_size
            compressed_size = (
                compressed_file.stat().st_size if compressed_file else optimized_size
            )

            optimization_results.append(
                {
                    "file": js_file.name,
                    "original_size": original_size,
                    "optimized_size": optimized_size,
                    "compressed_size": compressed_size,
                    "compression_ratio": (1 - compressed_size / original_size) * 100
                    if original_size > 0
                    else 0,
                }
            )

        return {"total_files": len(js_files), "results": optimization_results}

    def _optimize_html_content(self, content: str) -> str:
        """优化HTML内容"""
        import re

        # 移除HTML注释（保留条件注释）
        content = re.sub(r"<!--(?!\[if|\s*\[if).*?-->", "", content, flags=re.DOTALL)

        # 移除多余空白
        content = re.sub(r"\s+", " ", content)

        # 移除标签间的空白
        content = re.sub(r">\s+<", "><", content)

        # 优化script标签
        content = self._optimize_script_tags(content)

        # 优化link标签
        content = self._optimize_link_tags(content)

        return content.strip()

    def _optimize_css_content(self, content: str) -> str:
        """优化CSS内容"""
        import re

        # 移除CSS注释
        content = re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)

        # 移除多余空白
        content = re.sub(r"\s+", " ", content)

        # 移除分号前的空白
        content = re.sub(r"\s*;\s*", ";", content)

        # 移除冒号前后的空白
        content = re.sub(r"\s*:\s*", ":", content)

        # 移除大括号前后的空白
        content = re.sub(r"\s*{\s*", "{", content)
        content = re.sub(r"\s*}\s*", "}", content)

        # 移除逗号后的空白
        content = re.sub(r",\s*", ",", content)

        # 移除末尾分号
        content = re.sub(r";}", "}", content)

        return content.strip()

    def _optimize_js_content(self, content: str) -> str:
        """优化JavaScript内容"""
        import re

        # 移除单行注释
        content = re.sub(r"//.*$", "", content, flags=re.MULTILINE)

        # 移除多行注释
        content = re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)

        # 移除多余空白
        content = re.sub(r"\s+", " ", content)

        # 移除分号前的空白
        content = re.sub(r"\s*;\s*", ";", content)

        # 移除逗号后的空白
        content = re.sub(r",\s*", ",", content)

        # 移除大括号前后的空白
        content = re.sub(r"\s*{\s*", "{", content)
        content = re.sub(r"\s*}\s*", "}", content)

        return content.strip()

    def _optimize_script_tags(self, content: str) -> str:
        """优化script标签"""
        import re

        # 为没有async/defer的script标签添加defer
        def add_defer(match):
            script_content = match.group(0)
            if "async" not in script_content and "defer" not in script_content:
                script_content = script_content.replace("<script", "<script defer")
            return script_content

        content = re.sub(r"<script[^>]*>", add_defer, content)

        return content

    def _optimize_link_tags(self, content: str) -> str:
        """优化link标签"""
        import re

        # 为CSS链接添加preload
        def add_preload(match):
            link_content = match.group(0)
            if 'rel="stylesheet"' in link_content and "preload" not in link_content:
                # 这里可以添加preload逻辑，但需要小心处理
                pass
            return link_content

        content = re.sub(r"<link[^>]*>", add_preload, content)

        return content

    def _compress_file(self, file_path: Path) -> Optional[Path]:
        """压缩文件"""
        try:
            # 检查文件类型是否支持压缩
            mime_type, _ = mimetypes.guess_type(str(file_path))
            if mime_type not in self.compressible_types:
                return None

            # 创建压缩文件
            compressed_path = file_path.with_suffix(file_path.suffix + ".gz")

            with open(file_path, "rb") as f_in:
                with gzip.open(compressed_path, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)

            logger.info(f"文件已压缩: {compressed_path}")
            return compressed_path

        except Exception as e:
            logger.error(f"压缩文件失败 {file_path}: {e}")
            return None

    def generate_cache_manifest(self) -> Dict[str, Any]:
        """生成缓存清单"""
        logger.info("生成缓存清单...")

        # 收集所有静态资源
        static_files = []

        # HTML文件
        for html_file in self.frontend_dir.glob("*.html"):
            static_files.append(
                {
                    "url": f"/{html_file.name}",
                    "type": "html",
                    "size": html_file.stat().st_size,
                }
            )

        # CSS文件
        for css_file in self.frontend_dir.glob("*.css"):
            static_files.append(
                {
                    "url": f"/{css_file.name}",
                    "type": "css",
                    "size": css_file.stat().st_size,
                }
            )

        # JavaScript文件
        for js_file in self.frontend_dir.glob("*.js"):
            static_files.append(
                {
                    "url": f"/{js_file.name}",
                    "type": "js",
                    "size": js_file.stat().st_size,
                }
            )

        # 生成缓存策略
        cache_strategies = {
            "html": {"cache_control": "no-cache", "etag": True, "last_modified": True},
            "css": {
                "cache_control": "max-age=31536000",
                "etag": True,
                "last_modified": True,
            },
            "js": {
                "cache_control": "max-age=31536000",
                "etag": True,
                "last_modified": True,
            },
        }

        manifest = {
            "version": datetime.now().strftime("%Y%m%d_%H%M%S"),
            "files": static_files,
            "cache_strategies": cache_strategies,
            "total_size": sum(f["size"] for f in static_files),
        }

        # 保存清单文件
        manifest_file = self.output_dir / "cache_manifest.json"
        with open(manifest_file, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)

        logger.info(f"缓存清单已保存到: {manifest_file}")
        return manifest

    def generate_service_worker(self) -> str:
        """生成Service Worker"""
        logger.info("生成Service Worker...")

        sw_content = """
// Service Worker for Frontend Performance Optimization
const CACHE_NAME = 'frontend-cache-v1';
const STATIC_CACHE = 'static-cache-v1';
const DYNAMIC_CACHE = 'dynamic-cache-v1';

// 需要缓存的静态资源
const STATIC_ASSETS = [
    '/',
    '/index.html',
    '/common.css',
    '/theme.css',
    '/nav.css',
    '/app.js',
    '/nav.js'
];

// 安装事件
self.addEventListener('install', event => {
    console.log('Service Worker installing...');
    event.waitUntil(
        caches.open(STATIC_CACHE)
            .then(cache => {
                console.log('Caching static assets...');
                return cache.addAll(STATIC_ASSETS);
            })
            .then(() => self.skipWaiting())
    );
});

// 激活事件
self.addEventListener('activate', event => {
    console.log('Service Worker activating...');
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames.map(cacheName => {
                    if (cacheName !== STATIC_CACHE && cacheName !== DYNAMIC_CACHE) {
                        console.log('Deleting old cache:', cacheName);
                        return caches.delete(cacheName);
                    }
                })
            );
        }).then(() => self.clients.claim())
    );
});

// 拦截请求
self.addEventListener('fetch', event => {
    const { request } = event;
    const url = new URL(request.url);

    // 只处理同源请求
    if (url.origin !== location.origin) {
        return;
    }

    event.respondWith(
        caches.match(request)
            .then(response => {
                // 如果缓存中有，直接返回
                if (response) {
                    return response;
                }

                // 否则发起网络请求
                return fetch(request)
                    .then(fetchResponse => {
                        // 检查响应是否有效
                        if (!fetchResponse || fetchResponse.status !== 200 || fetchResponse.type !== 'basic') {
                            return fetchResponse;
                        }

                        // 克隆响应
                        const responseToCache = fetchResponse.clone();

                        // 根据资源类型决定缓存策略
                        if (request.url.match(/\\.(css|js|png|jpg|jpeg|gif|svg)$/)) {
                            // 静态资源缓存
                            caches.open(STATIC_CACHE)
                                .then(cache => {
                                    cache.put(request, responseToCache);
                                });
                        } else if (request.url.match(/\\.(html)$/)) {
                            // HTML文件缓存
                            caches.open(DYNAMIC_CACHE)
                                .then(cache => {
                                    cache.put(request, responseToCache);
                                });
                        }

                        return fetchResponse;
                    })
                    .catch(() => {
                        // 网络请求失败，尝试返回缓存
                        if (request.destination === 'document') {
                            return caches.match('/index.html');
                        }
                    });
            })
    );
});

// 消息处理
self.addEventListener('message', event => {
    if (event.data && event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }
});
"""

        # 保存Service Worker文件
        sw_file = self.output_dir / "sw.js"
        with open(sw_file, "w", encoding="utf-8") as f:
            f.write(sw_content.strip())

        logger.info(f"Service Worker已保存到: {sw_file}")
        return str(sw_file)

    def generate_build_report(self) -> Dict[str, Any]:
        """生成构建报告"""
        logger.info("生成构建优化报告...")

        # 执行各种优化
        html_results = self.optimize_html_files()
        css_results = self.optimize_css_files()
        js_results = self.optimize_js_files()

        # 生成缓存清单
        cache_manifest = self.generate_cache_manifest()

        # 生成Service Worker
        sw_file = self.generate_service_worker()

        # 计算总体统计
        total_original_size = 0
        total_optimized_size = 0
        total_compressed_size = 0

        for result in (
            html_results["results"] + css_results["results"] + js_results["results"]
        ):
            total_original_size += result["original_size"]
            total_optimized_size += result["optimized_size"]
            total_compressed_size += result["compressed_size"]

        overall_compression_ratio = (
            (1 - total_compressed_size / total_original_size) * 100
            if total_original_size > 0
            else 0
        )

        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_files": html_results["total_files"]
                + css_results["total_files"]
                + js_results["total_files"],
                "html_files": html_results["total_files"],
                "css_files": css_results["total_files"],
                "js_files": js_results["total_files"],
                "total_original_size": total_original_size,
                "total_optimized_size": total_optimized_size,
                "total_compressed_size": total_compressed_size,
                "overall_compression_ratio": overall_compression_ratio,
            },
            "html_optimization": html_results,
            "css_optimization": css_results,
            "js_optimization": js_results,
            "cache_manifest": cache_manifest,
            "service_worker": sw_file,
            "recommendations": self._generate_build_recommendations(
                overall_compression_ratio
            ),
        }

        # 保存报告
        report_file = self.output_dir / "build_report.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        logger.info(f"构建报告已保存到: {report_file}")
        return report

    def _generate_build_recommendations(self, compression_ratio: float) -> List[str]:
        """生成构建建议"""
        recommendations = []

        if compression_ratio < 30:
            recommendations.append("压缩率较低，建议检查是否有未优化的资源")

        if compression_ratio > 70:
            recommendations.append("压缩效果良好，可以考虑启用更激进的优化")

        recommendations.extend(
            [
                "建议在生产环境中启用Gzip压缩",
                "考虑使用CDN加速静态资源",
                "定期更新Service Worker缓存策略",
                "监控缓存命中率和性能指标",
            ]
        )

        return recommendations


def main():
    """主函数"""
    optimizer = FrontendBuildOptimizer()
    report = optimizer.generate_build_report()

    print("\n" + "=" * 60)
    print("前端构建优化报告")
    print("=" * 60)

    summary = report["summary"]
    print(f"\n📊 构建摘要:")
    print(f"  总文件数: {summary['total_files']}")
    print(f"  HTML文件: {summary['html_files']}")
    print(f"  CSS文件: {summary['css_files']}")
    print(f"  JavaScript文件: {summary['js_files']}")

    print(f"\n📦 文件大小:")
    print(f"  原始大小: {summary['total_original_size']:,} 字节")
    print(f"  优化后大小: {summary['total_optimized_size']:,} 字节")
    print(f"  压缩后大小: {summary['total_compressed_size']:,} 字节")
    print(f"  总体压缩率: {summary['overall_compression_ratio']:.1f}%")

    print(f"\n🚀 优化建议:")
    for recommendation in report["recommendations"]:
        print(f"  • {recommendation}")

    print(f"\n📄 详细报告已保存到: frontend/dist/build_report.json")
    print(f"📄 缓存清单已保存到: frontend/dist/cache_manifest.json")
    print(f"📄 Service Worker已保存到: frontend/dist/sw.js")


if __name__ == "__main__":
    main()
