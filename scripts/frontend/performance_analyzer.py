#!/usr/bin/env python3
"""
前端性能分析工具
Frontend Performance Analyzer

用于分析前端性能指标，生成优化建议
"""

import json
import logging
import os
import subprocess
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


@dataclass
class PerformanceMetrics:
    """性能指标数据类"""

    url: str
    first_contentful_paint: float
    largest_contentful_paint: float
    first_input_delay: float
    cumulative_layout_shift: float
    speed_index: float
    total_blocking_time: float
    time_to_interactive: float
    timestamp: str


@dataclass
class ResourceInfo:
    """资源信息"""

    url: str
    size: int
    type: str
    load_time: float
    cached: bool


@dataclass
class OptimizationSuggestion:
    """优化建议"""

    category: str
    priority: str
    description: str
    impact: str
    effort: str
    implementation: str


class FrontendPerformanceAnalyzer:
    """前端性能分析器"""

    def __init__(self, frontend_dir: str = "frontend"):
        self.frontend_dir = Path(frontend_dir)
        self.results_dir = Path("reports/frontend_performance")
        self.results_dir.mkdir(parents=True, exist_ok=True)

    def analyze_html_files(self) -> List[Dict[str, Any]]:
        """分析HTML文件"""
        html_files = list(self.frontend_dir.glob("*.html"))
        analysis_results = []

        for html_file in html_files:
            logger.info(f"分析HTML文件: {html_file.name}")

            # 读取文件内容
            with open(html_file, "r", encoding="utf-8") as f:
                content = f.read()

            # 分析文件大小
            file_size = html_file.stat().st_size

            # 分析外部资源
            external_resources = self._extract_external_resources(content)

            # 分析内联资源
            inline_resources = self._extract_inline_resources(content)

            # 分析性能问题
            performance_issues = self._analyze_performance_issues(content)

            analysis_results.append(
                {
                    "file": html_file.name,
                    "size": file_size,
                    "external_resources": external_resources,
                    "inline_resources": inline_resources,
                    "performance_issues": performance_issues,
                    "suggestions": self._generate_suggestions(performance_issues),
                }
            )

        return analysis_results

    def analyze_css_files(self) -> List[Dict[str, Any]]:
        """分析CSS文件"""
        css_files = list(self.frontend_dir.glob("*.css"))
        analysis_results = []

        for css_file in css_files:
            logger.info(f"分析CSS文件: {css_file.name}")

            with open(css_file, "r", encoding="utf-8") as f:
                content = f.read()

            # 分析CSS性能
            unused_rules = self._find_unused_css_rules(content)
            large_selectors = self._find_large_selectors(content)
            duplicate_rules = self._find_duplicate_rules(content)

            analysis_results.append(
                {
                    "file": css_file.name,
                    "size": css_file.stat().st_size,
                    "unused_rules": unused_rules,
                    "large_selectors": large_selectors,
                    "duplicate_rules": duplicate_rules,
                    "suggestions": self._generate_css_suggestions(
                        unused_rules, large_selectors, duplicate_rules
                    ),
                }
            )

        return analysis_results

    def analyze_js_files(self) -> List[Dict[str, Any]]:
        """分析JavaScript文件"""
        js_files = list(self.frontend_dir.glob("*.js"))
        analysis_results = []

        for js_file in js_files:
            logger.info(f"分析JavaScript文件: {js_file.name}")

            with open(js_file, "r", encoding="utf-8") as f:
                content = f.read()

            # 分析JavaScript性能
            large_functions = self._find_large_functions(content)
            duplicate_code = self._find_duplicate_code(content)
            performance_issues = self._analyze_js_performance(content)

            analysis_results.append(
                {
                    "file": js_file.name,
                    "size": js_file.stat().st_size,
                    "large_functions": large_functions,
                    "duplicate_code": duplicate_code,
                    "performance_issues": performance_issues,
                    "suggestions": self._generate_js_suggestions(
                        large_functions, duplicate_code, performance_issues
                    ),
                }
            )

        return analysis_results

    def _extract_external_resources(self, content: str) -> List[Dict[str, str]]:
        """提取外部资源"""
        import re

        resources = []

        # 查找CSS链接
        css_pattern = (
            r'<link[^>]*href=["\']([^"\']+)["\'][^>]*rel=["\']stylesheet["\'][^>]*>'
        )
        css_matches = re.findall(css_pattern, content, re.IGNORECASE)
        for match in css_matches:
            resources.append({"type": "css", "url": match})

        # 查找JavaScript文件
        js_pattern = r'<script[^>]*src=["\']([^"\']+)["\'][^>]*>'
        js_matches = re.findall(js_pattern, content, re.IGNORECASE)
        for match in js_matches:
            resources.append({"type": "js", "url": match})

        # 查找图片
        img_pattern = r'<img[^>]*src=["\']([^"\']+)["\'][^>]*>'
        img_matches = re.findall(img_pattern, content, re.IGNORECASE)
        for match in img_matches:
            resources.append({"type": "img", "url": match})

        return resources

    def _extract_inline_resources(self, content: str) -> Dict[str, Any]:
        """提取内联资源"""
        import re

        inline_resources = {"css": [], "js": [], "images": []}

        # 内联CSS
        inline_css_pattern = r"<style[^>]*>(.*?)</style>"
        css_matches = re.findall(inline_css_pattern, content, re.DOTALL | re.IGNORECASE)
        for css in css_matches:
            inline_resources["css"].append(
                {
                    "size": len(css.strip()),
                    "content": css.strip()[:100] + "..."
                    if len(css.strip()) > 100
                    else css.strip(),
                }
            )

        # 内联JavaScript
        inline_js_pattern = r"<script[^>]*>(.*?)</script>"
        js_matches = re.findall(inline_js_pattern, content, re.DOTALL | re.IGNORECASE)
        for js in js_matches:
            if not re.search(r"src=", js, re.IGNORECASE):  # 排除有src属性的script
                inline_resources["js"].append(
                    {
                        "size": len(js.strip()),
                        "content": js.strip()[:100] + "..."
                        if len(js.strip()) > 100
                        else js.strip(),
                    }
                )

        return inline_resources

    def _analyze_performance_issues(self, content: str) -> List[str]:
        """分析性能问题"""
        issues = []

        # 检查是否有阻塞渲染的资源
        if "<link" in content and 'rel="stylesheet"' in content:
            issues.append("存在阻塞渲染的CSS资源")

        # 检查是否有同步JavaScript
        if "<script" in content and "async" not in content and "defer" not in content:
            issues.append("存在同步JavaScript加载")

        # 检查是否有大图片
        if "<img" in content:
            issues.append("需要检查图片优化")

        # 检查是否有内联样式
        if "style=" in content:
            issues.append("存在内联样式，建议外部化")

        return issues

    def _find_unused_css_rules(self, content: str) -> List[str]:
        """查找未使用的CSS规则"""
        # 简化实现，实际应该与HTML文件交叉分析
        unused_rules = []

        # 查找可能的未使用规则
        import re

        class_pattern = r"\.([a-zA-Z0-9_-]+)"
        classes = re.findall(class_pattern, content)

        # 这里应该与HTML文件中的class使用情况对比
        # 简化实现，返回一些示例
        if len(classes) > 10:
            unused_rules.append(f"发现{len(classes)}个CSS类，建议检查使用情况")

        return unused_rules

    def _find_large_selectors(self, content: str) -> List[str]:
        """查找复杂的选择器"""
        large_selectors = []

        # 查找复杂选择器
        import re

        selector_pattern = r"([.#][a-zA-Z0-9_-]+(?:\s+[.#][a-zA-Z0-9_-]+){3,})"
        selectors = re.findall(selector_pattern, content)

        for selector in selectors:
            if len(selector.split()) > 3:
                large_selectors.append(f"复杂选择器: {selector}")

        return large_selectors

    def _find_duplicate_rules(self, content: str) -> List[str]:
        """查找重复的CSS规则"""
        # 简化实现
        return ["建议检查CSS规则重复"]

    def _find_large_functions(self, content: str) -> List[str]:
        """查找大型JavaScript函数"""
        large_functions = []

        # 查找函数定义
        import re

        function_pattern = r"function\s+([a-zA-Z0-9_]+)\s*\([^)]*\)\s*\{"
        functions = re.findall(function_pattern, content)

        # 简化分析
        if len(functions) > 5:
            large_functions.append(f"发现{len(functions)}个函数，建议检查函数大小")

        return large_functions

    def _find_duplicate_code(self, content: str) -> List[str]:
        """查找重复代码"""
        return ["建议检查代码重复"]

    def _analyze_js_performance(self, content: str) -> List[str]:
        """分析JavaScript性能问题"""
        issues = []

        # 检查是否有性能问题
        if "setInterval" in content:
            issues.append("使用setInterval，建议检查频率")

        if "document.getElementById" in content:
            issues.append("频繁DOM查询，建议缓存元素引用")

        if "innerHTML" in content:
            issues.append("使用innerHTML，注意XSS风险")

        return issues

    def _generate_suggestions(self, issues: List[str]) -> List[OptimizationSuggestion]:
        """生成优化建议"""
        suggestions = []

        for issue in issues:
            if "阻塞渲染" in issue:
                suggestions.append(
                    OptimizationSuggestion(
                        category="资源加载",
                        priority="高",
                        description="优化CSS加载策略",
                        impact="减少首屏渲染时间",
                        effort="低",
                        implementation="使用preload或异步加载非关键CSS",
                    )
                )
            elif "同步JavaScript" in issue:
                suggestions.append(
                    OptimizationSuggestion(
                        category="脚本加载",
                        priority="高",
                        description="异步加载JavaScript",
                        impact="减少阻塞渲染",
                        effort="低",
                        implementation="添加async或defer属性",
                    )
                )
            elif "图片优化" in issue:
                suggestions.append(
                    OptimizationSuggestion(
                        category="图片优化",
                        priority="中",
                        description="优化图片资源",
                        impact="减少加载时间",
                        effort="中",
                        implementation="使用WebP格式，添加懒加载",
                    )
                )

        return [asdict(s) for s in suggestions]

    def _generate_css_suggestions(
        self,
        unused_rules: List[str],
        large_selectors: List[str],
        duplicate_rules: List[str],
    ) -> List[Dict[str, str]]:
        """生成CSS优化建议"""
        suggestions = []

        if unused_rules:
            suggestions.append(
                {
                    "category": "CSS优化",
                    "priority": "中",
                    "description": "移除未使用的CSS规则",
                    "impact": "减少文件大小",
                    "effort": "中",
                    "implementation": "使用工具检测并移除未使用的CSS",
                }
            )

        if large_selectors:
            suggestions.append(
                {
                    "category": "CSS优化",
                    "priority": "低",
                    "description": "简化CSS选择器",
                    "impact": "提高渲染性能",
                    "effort": "中",
                    "implementation": "重构复杂选择器为简单选择器",
                }
            )

        return suggestions

    def _generate_js_suggestions(
        self,
        large_functions: List[str],
        duplicate_code: List[str],
        performance_issues: List[str],
    ) -> List[Dict[str, str]]:
        """生成JavaScript优化建议"""
        suggestions = []

        if performance_issues:
            suggestions.append(
                {
                    "category": "JavaScript优化",
                    "priority": "高",
                    "description": "优化JavaScript性能",
                    "impact": "提高执行效率",
                    "effort": "中",
                    "implementation": "缓存DOM查询，优化事件处理",
                }
            )

        if large_functions:
            suggestions.append(
                {
                    "category": "代码结构",
                    "priority": "中",
                    "description": "重构大型函数",
                    "impact": "提高可维护性",
                    "effort": "高",
                    "implementation": "将大函数拆分为小函数",
                }
            )

        return suggestions

    def generate_report(self) -> Dict[str, Any]:
        """生成性能分析报告"""
        logger.info("开始生成前端性能分析报告...")

        # 分析各种文件
        html_analysis = self.analyze_html_files()
        css_analysis = self.analyze_css_files()
        js_analysis = self.analyze_js_files()

        # 生成总体建议
        all_suggestions = []
        for analysis in html_analysis + css_analysis + js_analysis:
            all_suggestions.extend(analysis.get("suggestions", []))

        # 按优先级排序
        priority_order = {"高": 1, "中": 2, "低": 3}
        all_suggestions.sort(
            key=lambda x: priority_order.get(x.get("priority", "低"), 3)
        )

        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "html_files": len(html_analysis),
                "css_files": len(css_analysis),
                "js_files": len(js_analysis),
                "total_suggestions": len(all_suggestions),
            },
            "html_analysis": html_analysis,
            "css_analysis": css_analysis,
            "js_analysis": js_analysis,
            "optimization_suggestions": all_suggestions,
            "recommendations": self._generate_recommendations(all_suggestions),
        }

        # 保存报告
        report_file = (
            self.results_dir
            / f"performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        logger.info(f"性能分析报告已保存到: {report_file}")
        return report

    def _generate_recommendations(
        self, suggestions: List[Dict[str, str]]
    ) -> Dict[str, List[str]]:
        """生成推荐实施计划"""
        recommendations = {"immediate": [], "short_term": [], "long_term": []}

        for suggestion in suggestions:
            priority = suggestion.get("priority", "低")
            effort = suggestion.get("effort", "高")

            if priority == "高" and effort == "低":
                recommendations["immediate"].append(suggestion["description"])
            elif priority in ["高", "中"] and effort in ["低", "中"]:
                recommendations["short_term"].append(suggestion["description"])
            else:
                recommendations["long_term"].append(suggestion["description"])

        return recommendations


def main():
    """主函数"""
    analyzer = FrontendPerformanceAnalyzer()
    report = analyzer.generate_report()

    print("\n" + "=" * 60)
    print("前端性能分析报告")
    print("=" * 60)

    print(f"\n📊 分析摘要:")
    print(f"  HTML文件: {report['summary']['html_files']} 个")
    print(f"  CSS文件: {report['summary']['css_files']} 个")
    print(f"  JavaScript文件: {report['summary']['js_files']} 个")
    print(f"  优化建议: {report['summary']['total_suggestions']} 条")

    print(f"\n🚀 推荐实施计划:")
    recommendations = report["recommendations"]

    if recommendations["immediate"]:
        print(f"\n  立即实施 ({len(recommendations['immediate'])} 项):")
        for item in recommendations["immediate"]:
            print(f"    • {item}")

    if recommendations["short_term"]:
        print(f"\n  短期实施 ({len(recommendations['short_term'])} 项):")
        for item in recommendations["short_term"]:
            print(f"    • {item}")

    if recommendations["long_term"]:
        print(f"\n  长期实施 ({len(recommendations['long_term'])} 项):")
        for item in recommendations["long_term"]:
            print(f"    • {item}")

    print(f"\n📄 详细报告已保存到: reports/frontend_performance/")


if __name__ == "__main__":
    main()
