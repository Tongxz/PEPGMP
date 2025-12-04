#!/usr/bin/env python3
"""
项目根目录重命名验证脚本

用于验证项目根目录重命名后是否还有其他受影响的地方，包括：
1. 硬编码的绝对路径
2. 旧目录名引用
3. 配置文件中的路径
4. 环境变量引用
5. 文档中的示例路径
"""

import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent


# 颜色输出
class Colors:
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    BLUE = "\033[0;34m"
    CYAN = "\033[0;36m"
    RESET = "\033[0m"


def print_header(text: str):
    """打印标题"""
    print(f"\n{Colors.CYAN}{'='*70}{Colors.RESET}")
    print(f"{Colors.BLUE}{text}{Colors.RESET}")
    print(f"{Colors.CYAN}{'='*70}{Colors.RESET}\n")


def print_success(text: str):
    """打印成功信息"""
    print(f"{Colors.GREEN}✓{Colors.RESET} {text}")


def print_warning(text: str):
    """打印警告信息"""
    print(f"{Colors.YELLOW}⚠{Colors.RESET} {text}")


def print_error(text: str):
    """打印错误信息"""
    print(f"{Colors.RED}✗{Colors.RESET} {text}")


def print_info(text: str):
    """打印信息"""
    print(f"{Colors.BLUE}ℹ{Colors.RESET} {text}")


# 需要检查的旧目录名模式
OLD_DIR_PATTERNS = [
    r"\bPyt\b",  # 旧的目录名
    r"/Users/zhou/Code/Pyt",  # macOS 绝对路径
    r"~/projects/Pyt",  # 用户目录路径
    r"/mnt/c/Users/YourName/Code/Pyt",  # WSL Windows 路径
    r"/mnt/f/code/PythonCode/Pyt",  # WSL 路径
]

# 需要检查的硬编码路径模式
HARDCODED_PATH_PATTERNS = [
    r"/Users/[^/\s]+/Code/[^/\s]+",  # macOS 绝对路径
    r"/mnt/[cdef]/[^/\s]+/Code/[^/\s]+",  # WSL 路径
    r"/home/[^/\s]+/projects/[^/\s]+",  # Linux 部署路径
]

# 需要忽略的目录
IGNORE_DIRS = {
    ".git",
    "__pycache__",
    "venv",
    "node_modules",
    "htmlcov",
    ".pytest_cache",
    "mlruns",
    "dist",
    "build",
    ".idea",
    ".vscode",
    ".env",
    "logs",
    "backups",
    "output",
    "temp",
    "data",
    "models",
    "datasets",
}

# 需要检查的文件扩展名
CHECK_EXTENSIONS = {
    ".py",
    ".sh",
    ".ps1",
    ".yml",
    ".yaml",
    ".json",
    ".md",
    ".txt",
    ".conf",
    ".ini",
    ".env",
}


def should_ignore(path: Path) -> bool:
    """判断路径是否应该被忽略"""
    parts = path.parts
    for part in parts:
        if part in IGNORE_DIRS:
            return True
        if part.startswith("."):
            return True
    return False


def search_pattern_in_file(
    file_path: Path, pattern: str, pattern_name: str
) -> List[Tuple[int, str]]:
    """在文件中搜索模式"""
    matches = []
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            for line_num, line in enumerate(f, 1):
                if re.search(pattern, line, re.IGNORECASE):
                    matches.append((line_num, line.rstrip()))
    except Exception:
        # 忽略无法读取的文件
        pass
    return matches


def check_old_directory_references() -> Dict[str, List[Tuple[Path, int, str]]]:
    """检查旧目录名引用"""
    print_header("检查旧目录名引用")

    results = defaultdict(list)

    for pattern in OLD_DIR_PATTERNS:
        pattern_name = pattern.replace("\\b", "").replace("\\", "")

        for file_path in PROJECT_ROOT.rglob("*"):
            if should_ignore(file_path):
                continue

            if file_path.is_file() and file_path.suffix in CHECK_EXTENSIONS:
                matches = search_pattern_in_file(file_path, pattern, pattern_name)
                if matches:
                    rel_path = file_path.relative_to(PROJECT_ROOT)
                    for line_num, line_content in matches:
                        results[pattern_name].append((rel_path, line_num, line_content))

    return results


def check_hardcoded_paths() -> Dict[str, List[Tuple[Path, int, str]]]:
    """检查硬编码的绝对路径"""
    print_header("检查硬编码的绝对路径")

    results = defaultdict(list)

    for pattern in HARDCODED_PATH_PATTERNS:
        pattern_name = f"硬编码路径: {pattern}"

        for file_path in PROJECT_ROOT.rglob("*"):
            if should_ignore(file_path):
                continue

            if file_path.is_file() and file_path.suffix in CHECK_EXTENSIONS:
                matches = search_pattern_in_file(file_path, pattern, pattern_name)
                if matches:
                    rel_path = file_path.relative_to(PROJECT_ROOT)
                    for line_num, line_content in matches:
                        # 排除一些常见的合理路径
                        if not any(
                            skip in line_content
                            for skip in [
                                "/usr/",
                                "/opt/",
                                "/var/",
                                "/etc/",
                                "/bin/",
                                "/sbin/",
                                "/lib/",
                                "/sys/",
                                "docker-compose",
                                "nginx.conf",
                            ]
                        ):
                            results[pattern_name].append(
                                (rel_path, line_num, line_content)
                            )

    return results


def check_config_files() -> List[Tuple[Path, List[str]]]:
    """检查配置文件中的路径引用"""
    print_header("检查配置文件中的路径引用")

    config_files = [
        PROJECT_ROOT / ".env",
        PROJECT_ROOT / ".env.production",
        PROJECT_ROOT / ".env.local",
        PROJECT_ROOT / "docker-compose.yml",
        PROJECT_ROOT / "docker-compose.prod.yml",
    ]

    results = []

    for config_file in config_files:
        if not config_file.exists():
            continue

        issues = []
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    # 检查包含路径的环境变量或配置
                    if any(
                        keyword in line.lower()
                        for keyword in ["path", "dir", "file", "volume"]
                    ):
                        # 检查是否包含绝对路径
                        if re.search(r"[A-Z]:\\|/[a-z]/|~/[^/\s]+/[^/\s]+", line):
                            # 排除一些合理的路径
                            if not any(
                                skip in line
                                for skip in [
                                    "/usr/",
                                    "/opt/",
                                    "/var/",
                                    "/etc/",
                                    "docker-compose",
                                    "container_name",
                                ]
                            ):
                                issues.append(f"行 {line_num}: {line.rstrip()}")
        except Exception:
            pass

        if issues:
            results.append((config_file.relative_to(PROJECT_ROOT), issues))

    return results


def check_script_default_paths() -> List[Tuple[Path, List[str]]]:
    """检查脚本中的默认路径"""
    print_header("检查脚本中的默认路径")

    script_files = [
        PROJECT_ROOT / "scripts" / "prepare_minimal_deploy.sh",
        PROJECT_ROOT / "scripts" / "deploy_prod_wsl.sh",
        PROJECT_ROOT / "scripts" / "import_images_from_windows.sh",
        PROJECT_ROOT / "scripts" / "export_images_to_wsl.ps1",
        PROJECT_ROOT / "scripts" / "mlops" / "train_hairnet_workflow.py",
    ]

    results = []

    for script_file in script_files:
        if not script_file.exists():
            continue

        issues = []
        try:
            with open(script_file, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    # 检查默认路径变量
                    if re.search(
                        r"DEPLOY_DIR|PROJECT_PATH|WSL_PROJECT_PATH|WINDOWS_PROJECT",
                        line,
                    ):
                        # 检查是否包含硬编码路径
                        if re.search(r"[A-Z]:\\|/[a-z]/|~/[^/\s]+/[^/\s]+", line):
                            issues.append(f"行 {line_num}: {line.rstrip()}")
        except Exception:
            pass

        if issues:
            results.append((script_file.relative_to(PROJECT_ROOT), issues))

    return results


def check_python_path_references() -> List[Tuple[Path, List[str]]]:
    """检查Python代码中的路径引用"""
    print_header("检查Python代码中的硬编码路径")

    results = []

    for py_file in PROJECT_ROOT.rglob("*.py"):
        if should_ignore(py_file):
            continue

        issues = []
        try:
            with open(py_file, "r", encoding="utf-8") as f:
                content = f.read()

                # 检查硬编码的绝对路径
                abs_path_pattern = (
                    r'["\'](/Users/[^"\']+|/mnt/[^"\']+|/home/[^"\']+)["\']'
                )
                matches = re.finditer(abs_path_pattern, content)

                for match in matches:
                    path_str = match.group(1)
                    # 排除系统路径
                    if not any(
                        skip in path_str
                        for skip in [
                            "/usr/",
                            "/opt/",
                            "/var/",
                            "/etc/",
                            "/bin/",
                            "/sbin/",
                            "/lib/",
                            "/sys/",
                        ]
                    ):
                        # 获取行号
                        line_num = content[: match.start()].count("\n") + 1
                        line_content = content.split("\n")[line_num - 1]
                        issues.append(f"行 {line_num}: {line_content.strip()}")
        except Exception:
            pass

        if issues:
            results.append((py_file.relative_to(PROJECT_ROOT), issues))

    return results


def check_docker_configs() -> List[Tuple[Path, List[str]]]:
    """检查Docker配置文件中的路径"""
    print_header("检查Docker配置文件")

    docker_files = list(PROJECT_ROOT.glob("docker-compose*.yml")) + list(
        PROJECT_ROOT.glob("Dockerfile*")
    )

    results = []

    for docker_file in docker_files:
        issues = []
        try:
            with open(docker_file, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    # 检查卷挂载中的绝对路径
                    if ":" in line and (
                        "volume" in line.lower() or "./" in line or "/" in line
                    ):
                        # 检查是否包含可能的问题路径
                        if re.search(r"[A-Z]:\\|/Users/[^/\s]+/[^/\s]+/[^/\s]+", line):
                            issues.append(f"行 {line_num}: {line.rstrip()}")
        except Exception:
            pass

        if issues:
            results.append((docker_file.relative_to(PROJECT_ROOT), issues))

    return results


def print_results(results: Dict[str, List[Tuple[Path, int, str]]], title: str):
    """打印检查结果"""
    if not results:
        print_success(f"{title}: 未发现问题")
        return

    print_warning(f"{title}: 发现 {sum(len(v) for v in results.values())} 个潜在问题\n")

    for pattern_name, matches in results.items():
        print(f"\n{Colors.YELLOW}模式: {pattern_name}{Colors.RESET}")
        print(f"{'─' * 70}")

        # 按文件分组
        by_file = defaultdict(list)
        for rel_path, line_num, line_content in matches:
            by_file[rel_path].append((line_num, line_content))

        for rel_path, file_matches in sorted(by_file.items()):
            print(f"\n{Colors.CYAN}{rel_path}{Colors.RESET}")
            for line_num, line_content in file_matches:
                # 高亮匹配部分
                highlighted = re.sub(
                    OLD_DIR_PATTERNS[0]
                    if pattern_name.startswith("Pyt")
                    else r"(/[^/\s]+/[^/\s]+)",
                    lambda m: f"{Colors.RED}{m.group(0)}{Colors.RESET}",
                    line_content,
                )
                print(f"  行 {line_num:4d}: {highlighted}")


def print_file_results(results: List[Tuple[Path, List[str]]], title: str):
    """打印文件检查结果"""
    if not results:
        print_success(f"{title}: 未发现问题")
        return

    print_warning(f"{title}: 发现 {len(results)} 个文件需要检查\n")

    for rel_path, issues in results:
        print(f"\n{Colors.CYAN}{rel_path}{Colors.RESET}")
        for issue in issues:
            print(f"  {issue}")


def main():
    """主函数"""
    print(f"\n{Colors.CYAN}{'='*70}{Colors.RESET}")
    print(f"{Colors.BLUE}项目根目录重命名验证工具{Colors.RESET}")
    print(f"{Colors.CYAN}{'='*70}{Colors.RESET}")
    print(f"\n项目根目录: {PROJECT_ROOT}")
    print(f"当前目录名: {PROJECT_ROOT.name}\n")

    all_issues = False

    # 1. 检查旧目录名引用
    old_refs = check_old_directory_references()
    if old_refs:
        print_results(old_refs, "旧目录名引用检查")
        all_issues = True

    # 2. 检查硬编码路径
    hardcoded_paths = check_hardcoded_paths()
    if hardcoded_paths:
        print_results(hardcoded_paths, "硬编码路径检查")
        all_issues = True

    # 3. 检查配置文件
    config_issues = check_config_files()
    if config_issues:
        print_file_results(config_issues, "配置文件检查")
        all_issues = True

    # 4. 检查脚本默认路径
    script_issues = check_script_default_paths()
    if script_issues:
        print_file_results(script_issues, "脚本默认路径检查")
        all_issues = True

    # 5. 检查Python代码路径引用
    python_issues = check_python_path_references()
    if python_issues:
        print_file_results(python_issues, "Python代码路径检查")
        all_issues = True

    # 6. 检查Docker配置
    docker_issues = check_docker_configs()
    if docker_issues:
        print_file_results(docker_issues, "Docker配置检查")
        all_issues = True

    # 总结
    print_header("验证总结")

    if not all_issues:
        print_success("所有检查通过！未发现需要更新的路径引用。")
        print_info("建议:")
        print("  1. 检查环境变量文件（.env.*）是否包含路径引用")
        print("  2. 检查IDE配置文件是否需要更新")
        print("  3. 检查CI/CD配置文件（如.github/workflows/）")
        return 0
    else:
        print_warning("发现一些可能需要更新的路径引用。")
        print_info("建议:")
        print("  1. 审查上述发现的问题")
        print("  2. 确认是否需要更新为新的目录名或使用相对路径")
        print("  3. 参考 docs/项目重命名指南.md 进行修改")
        print("  4. 重新运行此脚本验证修改结果")
        return 1


if __name__ == "__main__":
    sys.exit(main())
