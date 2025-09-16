"""
架构分析器
Architecture Analyzer

分析项目架构，识别耦合问题，提供优化建议
"""

import ast
import os
import logging
from typing import Dict, List, Set, Tuple, Any
from dataclasses import dataclass, field
from collections import defaultdict
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class ModuleInfo:
    """模块信息"""
    name: str
    path: str
    imports: Set[str] = field(default_factory=set)
    exports: Set[str] = field(default_factory=set)
    dependencies: Set[str] = field(default_factory=set)
    dependents: Set[str] = field(default_factory=set)
    lines_of_code: int = 0
    complexity_score: float = 0.0
    coupling_score: float = 0.0

@dataclass
class DependencyInfo:
    """依赖信息"""
    source: str
    target: str
    import_type: str  # 'direct', 'relative', 'absolute'
    line_number: int
    is_circular: bool = False

@dataclass
class ArchitectureMetrics:
    """架构指标"""
    total_modules: int = 0
    total_dependencies: int = 0
    circular_dependencies: int = 0
    high_coupling_modules: int = 0
    average_coupling: float = 0.0
    max_coupling: float = 0.0
    architecture_complexity: float = 0.0

class ArchitectureAnalyzer:
    """架构分析器"""
    
    def __init__(self, project_root: str = "src"):
        self.project_root = Path(project_root)
        self.modules: Dict[str, ModuleInfo] = {}
        self.dependencies: List[DependencyInfo] = []
        self.circular_dependencies: List[List[str]] = []
        
    def analyze_project(self) -> Dict[str, Any]:
        """分析整个项目架构"""
        logger.info("开始架构分析...")
        
        # 1. 扫描所有Python文件
        self._scan_python_files()
        
        # 2. 分析模块依赖
        self._analyze_dependencies()
        
        # 3. 检测循环依赖
        self._detect_circular_dependencies()
        
        # 4. 计算耦合度
        self._calculate_coupling_scores()
        
        # 5. 生成架构指标
        metrics = self._calculate_architecture_metrics()
        
        # 6. 生成优化建议
        recommendations = self._generate_recommendations()
        
        return {
            "modules": {name: self._module_to_dict(module) for name, module in self.modules.items()},
            "dependencies": [self._dependency_to_dict(dep) for dep in self.dependencies],
            "circular_dependencies": self.circular_dependencies,
            "metrics": self._metrics_to_dict(metrics),
            "recommendations": recommendations
        }
    
    def _scan_python_files(self):
        """扫描所有Python文件"""
        for py_file in self.project_root.rglob("*.py"):
            if py_file.name == "__init__.py":
                continue
                
            module_name = self._get_module_name(py_file)
            if module_name:
                self.modules[module_name] = ModuleInfo(
                    name=module_name,
                    path=str(py_file)
                )
    
    def _get_module_name(self, file_path: Path) -> str:
        """获取模块名称"""
        try:
            relative_path = file_path.relative_to(self.project_root)
            module_name = str(relative_path).replace("/", ".").replace("\\", ".").replace(".py", "")
            return module_name
        except ValueError:
            return ""
    
    def _analyze_dependencies(self):
        """分析模块依赖关系"""
        for module_name, module_info in self.modules.items():
            try:
                with open(module_info.path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 解析AST
                tree = ast.parse(content)
                
                # 分析导入语句
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            self._process_import(module_name, alias.name, "direct", node.lineno)
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            self._process_import(module_name, node.module, "relative", node.lineno)
                
                # 计算代码行数
                module_info.lines_of_code = len(content.splitlines())
                
            except Exception as e:
                logger.warning(f"分析模块 {module_name} 失败: {e}")
    
    def _process_import(self, source_module: str, target_module: str, import_type: str, line_number: int):
        """处理导入语句"""
        # 清理模块名
        target_module = target_module.split('.')[0]  # 只取顶级模块名
        
        # 检查是否是项目内部模块
        if target_module in self.modules:
            dependency = DependencyInfo(
                source=source_module,
                target=target_module,
                import_type=import_type,
                line_number=line_number
            )
            self.dependencies.append(dependency)
            
            # 更新模块信息
            self.modules[source_module].dependencies.add(target_module)
            self.modules[target_module].dependents.add(source_module)
    
    def _detect_circular_dependencies(self):
        """检测循环依赖"""
        visited = set()
        rec_stack = set()
        
        def dfs(module_name: str, path: List[str]):
            if module_name in rec_stack:
                # 发现循环依赖
                cycle_start = path.index(module_name)
                cycle = path[cycle_start:] + [module_name]
                self.circular_dependencies.append(cycle)
                return
            
            if module_name in visited:
                return
            
            visited.add(module_name)
            rec_stack.add(module_name)
            
            for dep in self.modules[module_name].dependencies:
                dfs(dep, path + [module_name])
            
            rec_stack.remove(module_name)
        
        for module_name in self.modules:
            if module_name not in visited:
                dfs(module_name, [])
    
    def _calculate_coupling_scores(self):
        """计算耦合度分数"""
        for module_name, module_info in self.modules.items():
            # 计算耦合度：依赖数量 + 被依赖数量
            coupling_score = len(module_info.dependencies) + len(module_info.dependents)
            module_info.coupling_score = coupling_score
            
            # 计算复杂度：代码行数 + 依赖数量
            complexity_score = module_info.lines_of_code + len(module_info.dependencies) * 10
            module_info.complexity_score = complexity_score
    
    def _calculate_architecture_metrics(self) -> ArchitectureMetrics:
        """计算架构指标"""
        metrics = ArchitectureMetrics()
        
        metrics.total_modules = len(self.modules)
        metrics.total_dependencies = len(self.dependencies)
        metrics.circular_dependencies = len(self.circular_dependencies)
        
        if self.modules:
            coupling_scores = [module.coupling_score for module in self.modules.values()]
            metrics.average_coupling = sum(coupling_scores) / len(coupling_scores)
            metrics.max_coupling = max(coupling_scores)
            
            # 高耦合模块（超过平均值的1.5倍）
            metrics.high_coupling_modules = len([
                score for score in coupling_scores 
                if score > metrics.average_coupling * 1.5
            ])
        
        # 架构复杂度：循环依赖 + 高耦合模块
        metrics.architecture_complexity = (
            metrics.circular_dependencies * 10 + 
            metrics.high_coupling_modules * 5
        )
        
        return metrics
    
    def _generate_recommendations(self) -> List[Dict[str, Any]]:
        """生成优化建议"""
        recommendations = []
        
        # 1. 循环依赖建议
        if self.circular_dependencies:
            recommendations.append({
                "type": "circular_dependency",
                "priority": "high",
                "title": "解决循环依赖",
                "description": f"发现 {len(self.circular_dependencies)} 个循环依赖",
                "details": self.circular_dependencies,
                "suggestions": [
                    "使用依赖注入模式",
                    "引入抽象层",
                    "重构模块职责"
                ]
            })
        
        # 2. 高耦合模块建议
        high_coupling_modules = [
            name for name, module in self.modules.items()
            if module.coupling_score > self._calculate_architecture_metrics().average_coupling * 1.5
        ]
        
        if high_coupling_modules:
            recommendations.append({
                "type": "high_coupling",
                "priority": "medium",
                "title": "降低模块耦合度",
                "description": f"发现 {len(high_coupling_modules)} 个高耦合模块",
                "details": high_coupling_modules,
                "suggestions": [
                    "使用接口抽象",
                    "实现依赖倒置",
                    "拆分大型模块"
                ]
            })
        
        # 3. 复杂模块建议
        complex_modules = [
            (name, module.complexity_score) for name, module in self.modules.items()
            if module.complexity_score > 1000
        ]
        
        if complex_modules:
            recommendations.append({
                "type": "complexity",
                "priority": "medium",
                "title": "简化复杂模块",
                "description": f"发现 {len(complex_modules)} 个复杂模块",
                "details": complex_modules,
                "suggestions": [
                    "拆分功能职责",
                    "提取公共组件",
                    "使用设计模式"
                ]
            })
        
        # 4. 架构模式建议
        recommendations.append({
            "type": "architecture_pattern",
            "priority": "low",
            "title": "采用架构模式",
            "description": "建议采用分层架构和依赖注入",
            "suggestions": [
                "实现分层架构（表现层、业务层、数据层）",
                "使用依赖注入容器",
                "引入事件驱动架构",
                "实现插件化架构"
            ]
        })
        
        return recommendations
    
    def _module_to_dict(self, module: ModuleInfo) -> Dict[str, Any]:
        """模块信息转字典"""
        return {
            "name": module.name,
            "path": module.path,
            "dependencies": list(module.dependencies),
            "dependents": list(module.dependents),
            "lines_of_code": module.lines_of_code,
            "complexity_score": module.complexity_score,
            "coupling_score": module.coupling_score
        }
    
    def _dependency_to_dict(self, dep: DependencyInfo) -> Dict[str, Any]:
        """依赖信息转字典"""
        return {
            "source": dep.source,
            "target": dep.target,
            "import_type": dep.import_type,
            "line_number": dep.line_number,
            "is_circular": dep.is_circular
        }
    
    def _metrics_to_dict(self, metrics: ArchitectureMetrics) -> Dict[str, Any]:
        """指标转字典"""
        return {
            "total_modules": metrics.total_modules,
            "total_dependencies": metrics.total_dependencies,
            "circular_dependencies": metrics.circular_dependencies,
            "high_coupling_modules": metrics.high_coupling_modules,
            "average_coupling": metrics.average_coupling,
            "max_coupling": metrics.max_coupling,
            "architecture_complexity": metrics.architecture_complexity
        }

def analyze_project_architecture(project_root: str = "src") -> Dict[str, Any]:
    """分析项目架构（便捷函数）"""
    analyzer = ArchitectureAnalyzer(project_root)
    return analyzer.analyze_project()

if __name__ == "__main__":
    # 运行架构分析
    result = analyze_project_architecture()
    
    print("=== 架构分析结果 ===")
    print(f"总模块数: {result['metrics']['total_modules']}")
    print(f"总依赖数: {result['metrics']['total_dependencies']}")
    print(f"循环依赖: {result['metrics']['circular_dependencies']}")
    print(f"高耦合模块: {result['metrics']['high_coupling_modules']}")
    print(f"平均耦合度: {result['metrics']['average_coupling']:.2f}")
    print(f"架构复杂度: {result['metrics']['architecture_complexity']}")
    
    print("\n=== 优化建议 ===")
    for rec in result['recommendations']:
        print(f"- {rec['title']}: {rec['description']}")

