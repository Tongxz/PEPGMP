import json
import logging
import time
from enum import Enum
from typing import Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)


class RegionType(Enum):
    """区域类型枚举"""

    ENTRANCE = "entrance"  # 入口区域
    HANDWASH = "handwash"  # 洗手区域
    SANITIZE = "sanitize"  # 消毒区域
    WORK_AREA = "work_area"  # 工作区域
    RESTRICTED = "restricted"  # 限制区域
    MONITORING = "monitoring"  # 监控区域


class Region:
    """区域类"""

    def __init__(
        self,
        region_id: str,
        region_type: RegionType,
        polygon: List[Tuple[int, int]],
        name: str = "",
    ):
        """
        初始化区域

        Args:
            region_id: 区域唯一标识
            region_type: 区域类型
            polygon: 区域多边形顶点列表 [(x1,y1), (x2,y2), ...]
            name: 区域名称
        """
        self.region_id = region_id
        self.region_type = region_type
        self.polygon = polygon
        self.name = name or f"{region_type.value}_{region_id}"
        self.is_active = True

        # 区域规则配置
        self.rules = {
            "required_behaviors": [],  # 必需的行为
            "forbidden_behaviors": [],  # 禁止的行为
            "max_occupancy": -1,  # 最大容纳人数 (-1表示无限制)
            "min_duration": 0.0,  # 最小停留时间
            "max_duration": -1.0,  # 最大停留时间 (-1表示无限制)
            "alert_on_violation": True,  # 违规时是否报警
        }

        # 统计信息
        self.stats = {
            "total_entries": 0,
            "current_occupancy": 0,
            "violations": 0,
            "last_entry_time": None,
            "last_exit_time": None,
        }

        logger.info(f"Region {self.name} created with {len(polygon)} vertices")

        # 预计算AABB包围盒用于快速过滤（x_min,y_min,x_max,y_max）
        self._recompute_aabb()

    def _recompute_aabb(self) -> None:
        """根据当前多边形重算AABB。"""
        try:
            if self.polygon:
                xs = [float(x) for (x, _) in self.polygon]
                ys = [float(y) for (_, y) in self.polygon]
                self._aabb = (min(xs), min(ys), max(xs), max(ys))
            else:
                self._aabb = (0.0, 0.0, 0.0, 0.0)
        except Exception:
            self._aabb = (0.0, 0.0, 0.0, 0.0)

    def point_in_region(self, point: Tuple[int, int]) -> bool:
        """
        判断点是否在区域内（射线法）

        Args:
            point: 点坐标 (x, y)

        Returns:
            True if point is inside the region
        """
        x, y = point
        n = len(self.polygon)
        inside = False

        p1x, p1y = self.polygon[0]
        for i in range(1, n + 1):
            p2x, p2y = self.polygon[i % n]
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        else:
                            xinters = x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y

        return inside

    def bbox_in_region(self, bbox: List[int], threshold: float = 0.5) -> bool:
        """
        判断边界框是否在区域内

        Args:
            bbox: 边界框 [x1, y1, x2, y2]
            threshold: 重叠阈值（0.5表示边界框50%以上在区域内）

        Returns:
            True if bbox overlaps with region above threshold
        """
        x1, y1, x2, y2 = bbox

        # 预过滤：若与区域AABB有足够重叠则快速判定True；否则继续用中心点/顶点判定
        try:
            ax1, ay1, ax2, ay2 = self._aabb
            ix1 = max(float(x1), ax1); iy1 = max(float(y1), ay1)
            ix2 = min(float(x2), ax2); iy2 = min(float(y2), ay2)
            if ix2 > ix1 and iy2 > iy1:
                inter = (ix2 - ix1) * (iy2 - iy1)
                area_bbox = max(1.0, float(x2 - x1) * float(y2 - y1))
                if inter / area_bbox >= float(threshold):
                    return True
        except Exception:
            pass

        # 中心点优先：若中心点在区域内，直接认为重叠
        cx, cy = ((x1 + x2) // 2, (y1 + y2) // 2)
        try:
            if self.point_in_region((cx, cy)):
                return True
        except Exception:
            pass

        # 检查边界框的关键点
        points = [
            (x1, y1),  # 左上
            (x2, y1),  # 右上
            (x1, y2),  # 左下
            (x2, y2),  # 右下
            (cx, cy),  # 中心
        ]

        inside_count = sum(1 for point in points if self.point_in_region(point))
        overlap_ratio = inside_count / len(points)

        return overlap_ratio >= threshold

    def set_rule(self, rule_name: str, value):
        """设置区域规则"""
        if rule_name in self.rules:
            self.rules[rule_name] = value
            logger.info(f"Region {self.name} rule '{rule_name}' set to {value}")
        else:
            logger.warning(f"Unknown rule '{rule_name}' for region {self.name}")

    def get_center(self) -> Tuple[float, float]:
        """获取区域中心点"""
        if not self.polygon:
            return (0, 0)

        x_coords = [point[0] for point in self.polygon]
        y_coords = [point[1] for point in self.polygon]

        center_x = sum(x_coords) / len(x_coords)
        center_y = sum(y_coords) / len(y_coords)

        return (center_x, center_y)

    def get_area(self) -> float:
        """计算区域面积（鞋带公式）"""
        if len(self.polygon) < 3:
            return 0.0

        area = 0.0
        n = len(self.polygon)

        for i in range(n):
            j = (i + 1) % n
            area += self.polygon[i][0] * self.polygon[j][1]
            area -= self.polygon[j][0] * self.polygon[i][1]

        return abs(area) / 2.0

    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            "region_id": self.region_id,
            "region_type": self.region_type.value,
            "polygon": self.polygon,
            "name": self.name,
            "is_active": self.is_active,
            "rules": self.rules,
            "stats": self.stats,
        }


class RegionManager:
    """区域管理器

    管理所有检测区域，处理区域相关的逻辑
    """

    def __init__(self):
        """初始化区域管理器"""
        self.regions = {}  # region_id -> Region
        self.region_occupancy = {}  # region_id -> set of track_ids
        self.track_regions = {}  # track_id -> set of region_ids
        self.meta = {
            "canvas_size": None,      # {width:int,height:int}
            "background_size": None,  # {width:int,height:int}
            "fit_mode": None,         # 'contain'|'cover'|'stretch'
            "ref_size": None          # 'WxH' string
        }

        logger.info("RegionManager initialized")

    def add_region(self, region: Region) -> bool:
        """
        添加区域

        Args:
            region: 区域对象

        Returns:
            True if successfully added
        """
        if region.region_id in self.regions:
            logger.warning(f"Region {region.region_id} already exists")
            return False

        self.regions[region.region_id] = region
        self.region_occupancy[region.region_id] = set()

        logger.info(f"Region {region.name} added successfully")
        return True

    def remove_region(self, region_id: str) -> bool:
        """
        移除区域

        Args:
            region_id: 区域ID

        Returns:
            True if successfully removed
        """
        if region_id not in self.regions:
            logger.warning(f"Region {region_id} not found")
            return False

        # 清理相关数据
        del self.regions[region_id]
        if region_id in self.region_occupancy:
            del self.region_occupancy[region_id]

        # 清理追踪目标的区域记录
        for track_id in self.track_regions:
            self.track_regions[track_id].discard(region_id)

        logger.info(f"Region {region_id} removed successfully")
        return True

    def update_track_regions(self, track_id: int, bbox: List[int]) -> List[str]:
        """
        更新追踪目标所在的区域

        Args:
            track_id: 追踪目标ID
            bbox: 边界框

        Returns:
            当前所在的区域ID列表
        """
        current_regions = set()

        # 检查每个区域
        for region_id, region in self.regions.items():
            if not region.is_active:
                continue

            if region.bbox_in_region(bbox):
                current_regions.add(region_id)

        # 获取之前的区域
        previous_regions = self.track_regions.get(track_id, set())

        # 处理进入的区域
        entered_regions = current_regions - previous_regions
        for region_id in entered_regions:
            self._handle_region_entry(track_id, region_id)

        # 处理离开的区域
        exited_regions = previous_regions - current_regions
        for region_id in exited_regions:
            self._handle_region_exit(track_id, region_id)

        # 更新记录
        self.track_regions[track_id] = current_regions

        return list(current_regions)

    def _handle_region_entry(self, track_id: int, region_id: str):
        """处理区域进入事件"""
        region = self.regions[region_id]

        # 更新占用情况
        self.region_occupancy[region_id].add(track_id)

        # 更新统计信息
        region.stats["total_entries"] += 1
        region.stats["current_occupancy"] = len(self.region_occupancy[region_id])
        region.stats["last_entry_time"] = time.time()

        logger.info(f"Track {track_id} entered region {region.name}")

        # 检查容量限制
        max_occupancy = region.rules["max_occupancy"]
        if max_occupancy > 0 and region.stats["current_occupancy"] > max_occupancy:
            self._trigger_violation(region_id, track_id, "max_occupancy_exceeded")

    def _handle_region_exit(self, track_id: int, region_id: str):
        """处理区域离开事件"""
        region = self.regions[region_id]

        # 更新占用情况
        self.region_occupancy[region_id].discard(track_id)

        # 更新统计信息
        region.stats["current_occupancy"] = len(self.region_occupancy[region_id])
        region.stats["last_exit_time"] = time.time()

        logger.info(f"Track {track_id} exited region {region.name}")

    def _trigger_violation(self, region_id: str, track_id: int, violation_type: str):
        """触发违规事件"""
        region = self.regions[region_id]
        region.stats["violations"] += 1

        if region.rules["alert_on_violation"]:
            logger.warning(
                f"Violation in region {region.name}: {violation_type} by track {track_id}"
            )

    def check_behavior_compliance(self, track_id: int, behaviors: Dict) -> List[Dict]:
        """
        检查行为合规性

        Args:
            track_id: 追踪目标ID
            behaviors: 当前行为状态

        Returns:
            违规信息列表
        """
        violations = []

        if track_id not in self.track_regions:
            return violations

        for region_id in self.track_regions[track_id]:
            region = self.regions[region_id]

            # 检查必需行为
            for required_behavior in region.rules["required_behaviors"]:
                if (
                    required_behavior not in behaviors
                    or not behaviors[required_behavior].is_active
                ):
                    violation = {
                        "region_id": region_id,
                        "region_name": region.name,
                        "track_id": track_id,
                        "violation_type": "missing_required_behavior",
                        "details": f"Required behavior '{required_behavior}' not detected",
                    }
                    violations.append(violation)

            # 检查禁止行为
            for forbidden_behavior in region.rules["forbidden_behaviors"]:
                if (
                    forbidden_behavior in behaviors
                    and behaviors[forbidden_behavior].is_active
                ):
                    violation = {
                        "region_id": region_id,
                        "region_name": region.name,
                        "track_id": track_id,
                        "violation_type": "forbidden_behavior_detected",
                        "details": f"Forbidden behavior '{forbidden_behavior}' detected",
                    }
                    violations.append(violation)

        return violations

    def get_region_stats(self, region_id: str) -> Optional[Dict]:
        """获取区域统计信息"""
        if region_id not in self.regions:
            return None

        region = self.regions[region_id]
        return region.stats.copy()

    def get_all_regions_info(self) -> List[Dict]:
        """获取所有区域信息"""
        return [region.to_dict() for region in self.regions.values()]

    def save_regions_config(self, file_path: str) -> bool:
        """
        保存区域配置到文件

        Args:
            file_path: 配置文件路径

        Returns:
            True if successfully saved
        """
        try:
            config = {"regions": [region.to_dict() for region in self.regions.values()]}
            if any(self.meta.values()):
                config["meta"] = self.meta

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            logger.info(f"Regions config saved to {file_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to save regions config: {e}")
            return False

    def load_regions_config(self, file_path: str) -> bool:
        """
        从文件加载区域配置

        Args:
            file_path: 配置文件路径

        Returns:
            True if successfully loaded
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                config = json.load(f)

            # 清空现有区域
            self.regions.clear()
            self.region_occupancy.clear()
            self.track_regions.clear()

            # 记录 meta（可选）
            self.meta = config.get("meta", self.meta) or self.meta

            # 加载区域（兼容多种字段命名：type/region_type、points/polygon、id/region_id、is_active/isActive）
            for region_data in config.get("regions", []):
                try:
                    r_type = region_data.get("type") or region_data.get("region_type")
                    r_id = region_data.get("id") or region_data.get("region_id")
                    r_points = region_data.get("points") or region_data.get("polygon") or []
                    r_name = region_data.get("name", "")
                    r_active = region_data.get("is_active", region_data.get("isActive", True))
                    r_rules = region_data.get("rules", {})
                    r_stats = region_data.get("stats", None)

                    if not r_type or not r_id or not r_points:
                        raise ValueError("Region missing required fields (type/id/points)")

                    # 规范化多边形点：支持 [{"x":..,"y":..}] 或 [[x,y]]/[(x,y)]，保留为浮点以便后续按帧尺寸缩放
                    norm_points = []
                    for pt in r_points:
                        if isinstance(pt, dict):
                            x = pt.get("x") if "x" in pt else pt.get("X")
                            y = pt.get("y") if "y" in pt else pt.get("Y")
                            if x is None or y is None:
                                raise ValueError("Point dict missing x/y")
                        elif isinstance(pt, (list, tuple)) and len(pt) >= 2:
                            x, y = pt[0], pt[1]
                        else:
                            raise ValueError("Unsupported point format")

                        # 将字符串/数值统一为浮点，延后到使用时再转换为像素整型
                        def _to_float(v):
                            if isinstance(v, str):
                                try:
                                    v = float(v)
                                except Exception:
                                    raise ValueError(f"Invalid numeric string in point: {v}")
                            if isinstance(v, (int, float)):
                                return float(v)
                            raise ValueError(f"Invalid point coordinate type: {type(v)}")

                        norm_points.append((_to_float(x), _to_float(y)))

                    region_type = RegionType(r_type)
                    region = Region(
                        r_id,
                        region_type,
                        norm_points,
                        r_name,
                    )
                    region.is_active = r_active
                    # 合并规则
                    if isinstance(r_rules, dict):
                        region.rules.update(r_rules)
                    if isinstance(r_stats, dict):
                        region.stats.update(r_stats)

                    self.add_region(region)
                except Exception as e:
                    logger.error(f"Skip invalid region entry: {e}")

            logger.info(f"Regions config loaded from {file_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to load regions config: {e}")
            return False

    def apply_mapping(self, frame_width: int, frame_height: int):
        """按 meta 优先映射到帧尺寸；若 meta 不全，回退到现有逻辑。

        优先级：
        - 若存在 canvas/background/fit_mode：调用 scale_from_canvas_and_bg
        - 否则若存在 ref_size（"WxH"）：调用 scale_from_reference
        - 否则调用 scale_to_frame_if_needed
        """
        try:
            if getattr(self, "_scaled_once", False):
                return
            meta = self.meta or {}
            cs = meta.get("canvas_size") or {}
            bs = meta.get("background_size") or {}
            fit = meta.get("fit_mode") or "contain"
            ref = meta.get("ref_size") or None
            if all(k in cs for k in ("width", "height")) and all(k in bs for k in ("width", "height")):
                cw = int(cs.get("width") or 0); ch = int(cs.get("height") or 0)
                bw = int(bs.get("width") or 0); bh = int(bs.get("height") or 0)
                if cw > 0 and ch > 0 and bw > 0 and bh > 0:
                    self.scale_from_canvas_and_bg(cw, ch, bw, bh, frame_width, frame_height, fit_mode=str(fit))
                    try:
                        self._last_mapping = f"canvas_bg_fit(cw={cw},ch={ch},bw={bw},bh={bh},fit={fit})"
                    except Exception:
                        pass
                    return
            if isinstance(ref, str) and ("x" in ref.lower()):
                try:
                    rw, rh = map(int, ref.lower().split("x", 1))
                    if rw > 0 and rh > 0:
                        self.scale_from_reference(rw, rh, frame_width, frame_height)
                        try:
                            self._last_mapping = f"ref_size({rw}x{rh})"
                        except Exception:
                            pass
                        return
                except Exception:
                    pass
            self.scale_to_frame_if_needed(frame_width, frame_height)
            try:
                self._last_mapping = "auto"
            except Exception:
                pass
        except Exception as e:
            logger.warning(f"apply_mapping failed: {e}")

    def scale_to_frame_if_needed(self, frame_width: int, frame_height: int):
        """在知道视频帧尺寸后，对区域坐标做一次性缩放以适配当前帧坐标系。

        规则：
        - 若所有坐标均在[0,1]范围，按归一化坐标：x*=W, y*=H。
        - 否则，若最大坐标明显大于当前帧尺寸（>1.2x），按各自轴向做线性缩放到当前帧范围。
        - 其余情况认为已是像素坐标，保持不变。
        """
        try:
            if not self.regions:
                return
            if getattr(self, "_scaled_once", False):
                return
            max_x = 0.0
            max_y = 0.0
            min_x = 1e18
            min_y = 1e18
            for r in self.regions.values():
                for (x, y) in r.polygon:
                    max_x = max(max_x, float(x))
                    max_y = max(max_y, float(y))
                    min_x = min(min_x, float(x))
                    min_y = min(min_y, float(y))

            W = float(max(1, frame_width))
            H = float(max(1, frame_height))

            def _apply_scale(sx: float, sy: float):
                for r in self.regions.values():
                    new_poly = []
                    for (x, y) in r.polygon:
                        nx = float(x) * sx
                        ny = float(y) * sy
                        new_poly.append((nx, ny))
                    r.polygon = new_poly
                    try:
                        r._recompute_aabb()
                    except Exception:
                        pass

            # 情况一：归一化坐标
            if max_x <= 1.0 and max_y <= 1.0 and min_x >= 0.0 and min_y >= 0.0:
                _apply_scale(W, H)
                logger.info(f"Regions scaled from normalized coords to frame size W={W}, H={H}")
                self._scaled_once = True
                return

            # 情况二：坐标来自更大参考分辨率，按最大坐标压缩到当前帧
            if max_x > 1.2 * W or max_y > 1.2 * H:
                sx = W / max_x if max_x > 0 else 1.0
                sy = H / max_y if max_y > 0 else 1.0
                _apply_scale(sx, sy)
                logger.info(f"Regions scaled from larger reference (max=({max_x:.1f},{max_y:.1f})) to frame ({W:.0f},{H:.0f}) with sx={sx:.4f}, sy={sy:.4f}")
                self._scaled_once = True
                return

            # 情况三：像素坐标但显著小于当前帧，推断为较小参考分辨率，放大到当前帧
            if (max_x > 1.0 or max_y > 1.0) and (max_x < 0.8 * W and max_y < 0.8 * H):
                sx = W / max_x if max_x > 0 else 1.0
                sy = H / max_y if max_y > 0 else 1.0
                _apply_scale(sx, sy)
                logger.info(f"Regions scaled up from smaller reference (max=({max_x:.1f},{max_y:.1f})) to frame ({W:.0f},{H:.0f}) with sx={sx:.4f}, sy={sy:.4f}")
                self._scaled_once = True
                return

            # 情况四：已是像素坐标且与帧相近，无需缩放
            logger.info("Regions appear to be in pixel coordinates; no scaling applied.")
            self._scaled_once = True
        except Exception as e:
            logger.warning(f"scale_to_frame_if_needed failed: {e}")

    def scale_from_reference(self, ref_width: int, ref_height: int, frame_width: int, frame_height: int):
        """按指定参考分辨率缩放到当前帧分辨率。

        用于前端标注在 ref_width x ref_height 画布下保存的像素坐标，
        显示/检测时需要映射到 frame_width x frame_height。
        """
        try:
            if not self.regions:
                return
            if ref_width <= 0 or ref_height <= 0:
                logger.warning("scale_from_reference ignored: invalid reference size")
                return
            if getattr(self, "_scaled_once", False):
                logger.info("Regions already scaled; skip scale_from_reference")
                return
            sx = float(frame_width) / float(ref_width)
            sy = float(frame_height) / float(ref_height)
            for r in self.regions.values():
                new_poly = []
                for (x, y) in r.polygon:
                    nx = float(x) * sx
                    ny = float(y) * sy
                    new_poly.append((nx, ny))
                r.polygon = new_poly
                try:
                    r._recompute_aabb()
                except Exception:
                    pass
            self._scaled_once = True
            logger.info(f"Regions scaled from reference ({ref_width}x{ref_height}) to frame ({frame_width}x{frame_height}) with sx={sx:.4f}, sy={sy:.4f}")
        except Exception as e:
            logger.warning(f"scale_from_reference failed: {e}")

    def scale_from_canvas_and_bg(self, canvas_width: int, canvas_height: int,
                                 bg_width: int, bg_height: int,
                                 frame_width: int, frame_height: int,
                                 fit_mode: str = "contain"):
        """将基于前端画布坐标标注的区域，映射到当前视频帧坐标。

        参数:
        - canvas_width/height: 前端用于标注的画布尺寸
        - bg_width/height: 画布中展示的背景图实际分辨率
        - frame_width/height: 当前视频帧尺寸
        - fit_mode: 背景图在画布的铺放方式（contain/cover/stretch），默认contain

        逻辑:
        1) 先从画布坐标还原到背景图像素坐标（根据fit/偏移）
        2) 再按背景图->视频帧的等比缩放映射（逐轴缩放）
        """
        try:
            if not self.regions:
                return
            if canvas_width <= 0 or canvas_height <= 0 or bg_width <= 0 or bg_height <= 0:
                logger.warning("scale_from_canvas_and_bg ignored: invalid sizes")
                return
            if getattr(self, "_scaled_once", False):
                logger.info("Regions already scaled; skip scale_from_canvas_and_bg")
                return

            cw = float(canvas_width); ch = float(canvas_height)
            bw = float(bg_width); bh = float(bg_height)

            if fit_mode not in ("contain", "cover", "stretch"):
                fit_mode = "contain"

            if fit_mode == "stretch":
                s = (cw / bw, ch / bh)
                dx, dy = 0.0, 0.0
            elif fit_mode == "cover":
                s_uni = max(cw / bw, ch / bh)
                s = (s_uni, s_uni)
                dx = (cw - bw * s_uni) / 2.0
                dy = (ch - bh * s_uni) / 2.0
            else:  # contain
                s_uni = min(cw / bw, ch / bh)
                s = (s_uni, s_uni)
                dx = (cw - bw * s_uni) / 2.0
                dy = (ch - bh * s_uni) / 2.0

            fx = float(frame_width) / bw
            fy = float(frame_height) / bh

            def _map_point(xc: float, yc: float):
                # 画布->背景像素
                xb = (float(xc) - dx) / s[0]
                yb = (float(yc) - dy) / s[1]
                # 背景->视频帧
                xf = xb * fx
                yf = yb * fy
                return (xf, yf)

            for r in self.regions.values():
                new_poly = []
                for (x, y) in r.polygon:
                    nx, ny = _map_point(x, y)
                    new_poly.append((nx, ny))
                r.polygon = new_poly
                try:
                    r._recompute_aabb()
                except Exception:
                    pass

            self._scaled_once = True
            logger.info(f"Regions mapped from canvas({canvas_width}x{canvas_height}, fit={fit_mode}) with bg({bg_width}x{bg_height}) to frame({frame_width}x{frame_height}).")
        except Exception as e:
            logger.warning(f"scale_from_canvas_and_bg failed: {e}")

    def reset(self):
        """重置区域管理器"""
        self.regions.clear()
        self.region_occupancy.clear()
        self.track_regions.clear()
        logger.info("RegionManager reset")
