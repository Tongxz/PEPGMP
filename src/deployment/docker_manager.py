"""
Docker部署管理器
提供Docker容器的创建、管理、监控功能
"""

import asyncio
import json
import logging
import os
import subprocess
from datetime import datetime
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class DockerManager:
    """Docker容器管理器"""
    
    def __init__(self):
        self.docker_host = os.getenv("DOCKER_HOST", "unix:///var/run/docker.sock")
        self.network_name = os.getenv("DOCKER_NETWORK", "pyt-prod-network")
    
    async def create_deployment(self, deployment_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        创建Docker部署
        
        Args:
            deployment_config: 部署配置
            
        Returns:
            部署结果
        """
        try:
            deployment_id = deployment_config.get("id")
            name = deployment_config.get("name")
            image = deployment_config.get("image", "pyt-api:latest")
            replicas = deployment_config.get("replicas", 1)
            environment = deployment_config.get("environment", "production")
            
            logger.info(f"开始创建Docker部署: {name}")
            
            # 构建Docker Compose配置
            compose_config = self._build_docker_compose_config(deployment_config)
            
            # 创建临时docker-compose文件
            compose_file = f"/tmp/deployment_{deployment_id}.yml"
            with open(compose_file, "w") as f:
                f.write(compose_config)
            
            # 启动服务
            cmd = [
                "docker-compose",
                "-f", compose_file,
                "up", "-d", "--scale", f"api={replicas}"
            ]
            
            result = await self._run_command(cmd)
            
            if result["success"]:
                logger.info(f"✅ Docker部署创建成功: {name}")
                
                # 获取容器状态
                status = await self._get_deployment_status(deployment_id)
                
                return {
                    "success": True,
                    "deployment_id": deployment_id,
                    "status": "running",
                    "containers": status.get("containers", []),
                    "message": f"部署 {name} 创建成功"
                }
            else:
                logger.error(f"❌ Docker部署创建失败: {result['error']}")
                return {
                    "success": False,
                    "deployment_id": deployment_id,
                    "error": result["error"],
                    "message": f"部署 {name} 创建失败"
                }
                
        except Exception as e:
            logger.error(f"Docker部署创建异常: {e}")
            return {
                "success": False,
                "deployment_id": deployment_config.get("id"),
                "error": str(e),
                "message": "部署创建异常"
            }
    
    async def update_deployment(self, deployment_id: str, update_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        更新Docker部署
        
        Args:
            deployment_id: 部署ID
            update_config: 更新配置
            
        Returns:
            更新结果
        """
        try:
            logger.info(f"开始更新Docker部署: {deployment_id}")
            
            # 获取当前部署状态
            current_status = await self._get_deployment_status(deployment_id)
            
            if not current_status.get("exists", False):
                return {
                    "success": False,
                    "error": "部署不存在",
                    "message": f"部署 {deployment_id} 不存在"
                }
            
            # 执行滚动更新
            cmd = [
                "docker-compose",
                "-f", f"/tmp/deployment_{deployment_id}.yml",
                "up", "-d", "--no-deps", "--build"
            ]
            
            result = await self._run_command(cmd)
            
            if result["success"]:
                logger.info(f"✅ Docker部署更新成功: {deployment_id}")
                return {
                    "success": True,
                    "deployment_id": deployment_id,
                    "status": "updated",
                    "message": f"部署 {deployment_id} 更新成功"
                }
            else:
                logger.error(f"❌ Docker部署更新失败: {result['error']}")
                return {
                    "success": False,
                    "deployment_id": deployment_id,
                    "error": result["error"],
                    "message": f"部署 {deployment_id} 更新失败"
                }
                
        except Exception as e:
            logger.error(f"Docker部署更新异常: {e}")
            return {
                "success": False,
                "deployment_id": deployment_id,
                "error": str(e),
                "message": "部署更新异常"
            }
    
    async def delete_deployment(self, deployment_id: str) -> Dict[str, Any]:
        """
        删除Docker部署
        
        Args:
            deployment_id: 部署ID
            
        Returns:
            删除结果
        """
        try:
            logger.info(f"开始删除Docker部署: {deployment_id}")
            
            # 停止并删除服务
            cmd = [
                "docker-compose",
                "-f", f"/tmp/deployment_{deployment_id}.yml",
                "down", "-v"
            ]
            
            result = await self._run_command(cmd)
            
            if result["success"]:
                # 清理临时文件
                compose_file = f"/tmp/deployment_{deployment_id}.yml"
                if os.path.exists(compose_file):
                    os.remove(compose_file)
                
                logger.info(f"✅ Docker部署删除成功: {deployment_id}")
                return {
                    "success": True,
                    "deployment_id": deployment_id,
                    "message": f"部署 {deployment_id} 删除成功"
                }
            else:
                logger.error(f"❌ Docker部署删除失败: {result['error']}")
                return {
                    "success": False,
                    "deployment_id": deployment_id,
                    "error": result["error"],
                    "message": f"部署 {deployment_id} 删除失败"
                }
                
        except Exception as e:
            logger.error(f"Docker部署删除异常: {e}")
            return {
                "success": False,
                "deployment_id": deployment_id,
                "error": str(e),
                "message": "部署删除异常"
            }
    
    async def get_deployment_status(self, deployment_id: str) -> Dict[str, Any]:
        """
        获取部署状态
        
        Args:
            deployment_id: 部署ID
            
        Returns:
            部署状态
        """
        return await self._get_deployment_status(deployment_id)
    
    async def scale_deployment(self, deployment_id: str, replicas: int) -> Dict[str, Any]:
        """
        扩缩容部署
        
        Args:
            deployment_id: 部署ID
            replicas: 副本数
            
        Returns:
            扩缩容结果
        """
        try:
            logger.info(f"开始扩缩容部署: {deployment_id} -> {replicas} 副本")
            
            cmd = [
                "docker-compose",
                "-f", f"/tmp/deployment_{deployment_id}.yml",
                "up", "-d", "--scale", f"api={replicas}"
            ]
            
            result = await self._run_command(cmd)
            
            if result["success"]:
                logger.info(f"✅ Docker部署扩缩容成功: {deployment_id}")
                return {
                    "success": True,
                    "deployment_id": deployment_id,
                    "replicas": replicas,
                    "message": f"部署 {deployment_id} 扩缩容到 {replicas} 副本成功"
                }
            else:
                logger.error(f"❌ Docker部署扩缩容失败: {result['error']}")
                return {
                    "success": False,
                    "deployment_id": deployment_id,
                    "error": result["error"],
                    "message": f"部署 {deployment_id} 扩缩容失败"
                }
                
        except Exception as e:
            logger.error(f"Docker部署扩缩容异常: {e}")
            return {
                "success": False,
                "deployment_id": deployment_id,
                "error": str(e),
                "message": "部署扩缩容异常"
            }
    
    def _build_docker_compose_config(self, deployment_config: Dict[str, Any]) -> str:
        """
        构建Docker Compose配置
        
        Args:
            deployment_config: 部署配置
            
        Returns:
            Docker Compose YAML配置
        """
        deployment_id = deployment_config.get("id")
        name = deployment_config.get("name")
        image = deployment_config.get("image", "pyt-api:latest")
        replicas = deployment_config.get("replicas", 1)
        environment = deployment_config.get("environment", "production")
        
        # 环境变量
        env_vars = deployment_config.get("environment_variables", {})
        env_str = "\n".join([f"      - {k}={v}" for k, v in env_vars.items()])
        
        # 端口映射
        ports = deployment_config.get("ports", [{"container": 8000, "host": 8000}])
        port_str = "\n".join([f"      - \"{p['host']}:{p['container']}\"" for p in ports])
        
        # 资源限制
        cpu_limit = deployment_config.get("cpu_limit", "1")
        memory_limit = deployment_config.get("memory_limit", "2Gi")
        
        compose_config = f"""
version: "3.8"

services:
  api:
    image: {image}
    container_name: {name}-{deployment_id}
    environment:
{env_str}
    ports:
{port_str}
    deploy:
      resources:
        limits:
          cpus: '{cpu_limit}'
          memory: {memory_limit}
    networks:
      - {self.network_name}
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

networks:
  {self.network_name}:
    external: true
"""
        return compose_config
    
    async def _get_deployment_status(self, deployment_id: str) -> Dict[str, Any]:
        """
        获取部署状态
        
        Args:
            deployment_id: 部署ID
            
        Returns:
            部署状态信息
        """
        try:
            # 检查容器是否存在
            cmd = ["docker", "ps", "-a", "--filter", f"name={deployment_id}", "--format", "json"]
            result = await self._run_command(cmd)
            
            if not result["success"]:
                return {"exists": False, "error": result["error"]}
            
            containers = []
            if result["output"]:
                for line in result["output"].strip().split("\n"):
                    if line.strip():
                        try:
                            container_info = json.loads(line)
                            containers.append(container_info)
                        except json.JSONDecodeError:
                            continue
            
            if not containers:
                return {"exists": False, "containers": []}
            
            # 分析容器状态
            running_containers = [c for c in containers if c.get("State") == "running"]
            total_containers = len(containers)
            running_count = len(running_containers)
            
            status = "running" if running_count > 0 else "stopped"
            
            return {
                "exists": True,
                "status": status,
                "total_containers": total_containers,
                "running_containers": running_count,
                "containers": containers
            }
            
        except Exception as e:
            logger.error(f"获取部署状态失败: {e}")
            return {"exists": False, "error": str(e)}
    
    async def _run_command(self, cmd: List[str]) -> Dict[str, Any]:
        """
        运行命令
        
        Args:
            cmd: 命令列表
            
        Returns:
            命令执行结果
        """
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            return {
                "success": process.returncode == 0,
                "output": stdout.decode() if stdout else "",
                "error": stderr.decode() if stderr else "",
                "returncode": process.returncode
            }
            
        except Exception as e:
            return {
                "success": False,
                "output": "",
                "error": str(e),
                "returncode": -1
            }
