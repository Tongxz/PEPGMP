-- ============================================================================
-- 区域数据审计和修复脚本
-- 目的：确保regions表的polygon/points字段数据完整性
-- 创建时间：2026-01-26
-- ============================================================================

-- 注意：此脚本使用polygon字段（不是points），根据export_regions_to_json.py

BEGIN;

-- ============================================================================
-- Phase 1: 数据审计
-- ============================================================================

\echo ''
\echo '============================================================'
\echo 'Phase 1: 数据审计'
\echo '============================================================'
\echo ''

-- 1.1 统计总体情况
\echo '1. 统计regions表总体情况...'
SELECT
    COUNT(*) as total_regions,
    COUNT(*) FILTER (WHERE polygon IS NULL) as null_polygon,
    COUNT(*) FILTER (WHERE jsonb_typeof(polygon) != 'array') as invalid_type,
    COUNT(*) FILTER (WHERE jsonb_typeof(polygon) = 'array' AND jsonb_array_length(polygon) < 3) as insufficient_points,
    COUNT(*) FILTER (WHERE polygon IS NOT NULL AND jsonb_typeof(polygon) = 'array' AND jsonb_array_length(polygon) >= 3) as valid_regions
FROM regions;

\echo ''
\echo '2. 异常数据详情（前20条）...'
SELECT
    region_id,
    name,
    region_type,
    CASE
        WHEN polygon IS NULL THEN 'NULL'
        WHEN jsonb_typeof(polygon) != 'array' THEN 'INVALID_TYPE: ' || jsonb_typeof(polygon)
        WHEN jsonb_array_length(polygon) < 3 THEN 'INSUFFICIENT: ' || jsonb_array_length(polygon)::text || ' points'
        ELSE 'UNKNOWN'
    END as issue,
    polygon
FROM regions
WHERE polygon IS NULL
   OR jsonb_typeof(polygon) != 'array'
   OR jsonb_array_length(polygon) < 3
LIMIT 20;

\echo ''
\echo '3. 按camera_id统计异常区域...'
SELECT
    camera_id,
    COUNT(*) as total_regions,
    COUNT(*) FILTER (WHERE polygon IS NULL OR jsonb_typeof(polygon) != 'array' OR jsonb_array_length(polygon) < 3) as invalid_regions
FROM regions
GROUP BY camera_id
HAVING COUNT(*) FILTER (WHERE polygon IS NULL OR jsonb_typeof(polygon) != 'array' OR jsonb_array_length(polygon) < 3) > 0
ORDER BY invalid_regions DESC;

-- ============================================================================
-- Phase 2: 数据备份
-- ============================================================================

\echo ''
\echo '============================================================'
\echo 'Phase 2: 数据备份'
\echo '============================================================'
\echo ''

-- 2.1 创建备份表
DROP TABLE IF EXISTS regions_backup_before_fix_20260126;
CREATE TABLE regions_backup_before_fix_20260126 AS
SELECT * FROM regions
WHERE polygon IS NULL
   OR jsonb_typeof(polygon) != 'array'
   OR jsonb_array_length(polygon) < 3;

\echo '✓ 已备份异常数据到 regions_backup_before_fix_20260126'

SELECT
    COUNT(*) as backed_up_count,
    MIN(region_id) as first_region_id,
    MAX(region_id) as last_region_id
FROM regions_backup_before_fix_20260126;

-- ============================================================================
-- Phase 3: 数据修复
-- ============================================================================

\echo ''
\echo '============================================================'
\echo 'Phase 3: 数据修复'
\echo '============================================================'
\echo ''

-- 3.1 选择修复策略
-- 策略A：删除异常数据（推荐：如果异常数据不多且可以重新创建）
-- 策略B：修复异常数据（设置默认矩形区域）

-- 显示待修复的数据数量
SELECT
    COUNT(*) as to_fix_count,
    COUNT(*) FILTER (WHERE polygon IS NULL) as null_count,
    COUNT(*) FILTER (WHERE jsonb_array_length(polygon) < 3) as insufficient_count
FROM regions
WHERE polygon IS NULL
   OR jsonb_typeof(polygon) != 'array'
   OR jsonb_array_length(polygon) < 3;

-- ====================================
-- 方案A：删除异常数据（取消注释以启用）
-- ====================================
-- \echo ''
-- \echo '执行方案A：删除异常数据...'
-- DELETE FROM regions
-- WHERE polygon IS NULL
--    OR jsonb_typeof(polygon) != 'array'
--    OR jsonb_array_length(polygon) < 3;
-- \echo '✓ 异常数据已删除'

-- ====================================
-- 方案B：修复异常数据（设置默认矩形 - 推荐）
-- ====================================
\echo ''
\echo '执行方案B：修复异常数据（设置默认矩形）...'

-- 3.2 修复NULL或invalid type的polygon
UPDATE regions
SET
    polygon = '[[0,0], [640,0], [640,480], [0,480]]'::jsonb,
    name = name || ' [自动修复]',
    is_active = false  -- 标记为非活跃，让用户重新配置
WHERE polygon IS NULL
   OR jsonb_typeof(polygon) != 'array';

\echo '✓ 已修复NULL或invalid type的polygon'

-- 3.3 修复点数不足的polygon
UPDATE regions
SET
    polygon = polygon || '[[0,0]]'::jsonb,  -- 添加一个默认点
    name = name || ' [需要重新配置]',
    is_active = false
WHERE jsonb_typeof(polygon) = 'array'
  AND jsonb_array_length(polygon) < 3
  AND jsonb_array_length(polygon) > 0;

-- 3.4 对于空数组，设置默认矩形
UPDATE regions
SET
    polygon = '[[0,0], [640,0], [640,480], [0,480]]'::jsonb,
    name = name || ' [需要重新配置]',
    is_active = false
WHERE jsonb_typeof(polygon) = 'array'
  AND jsonb_array_length(polygon) = 0;

\echo '✓ 已修复点数不足的polygon'

-- ============================================================================
-- Phase 4: 验证修复结果
-- ============================================================================

\echo ''
\echo '============================================================'
\echo 'Phase 4: 验证修复结果'
\echo '============================================================'
\echo ''

-- 4.1 再次统计
\echo '1. 修复后的统计...'
SELECT
    COUNT(*) as total_regions,
    COUNT(*) FILTER (WHERE polygon IS NULL) as null_polygon,
    COUNT(*) FILTER (WHERE jsonb_typeof(polygon) != 'array') as invalid_type,
    COUNT(*) FILTER (WHERE jsonb_array_length(polygon) < 3) as insufficient_points,
    COUNT(*) FILTER (WHERE polygon IS NOT NULL AND jsonb_typeof(polygon) = 'array' AND jsonb_array_length(polygon) >= 3) as valid_regions
FROM regions;

-- 4.2 应该没有异常数据
\echo ''
\echo '2. 检查是否还有异常数据（应该为0）...'
SELECT COUNT(*) as remaining_invalid_count
FROM regions
WHERE polygon IS NULL
   OR jsonb_typeof(polygon) != 'array'
   OR jsonb_array_length(polygon) < 3;

-- 4.3 显示修复的区域
\echo ''
\echo '3. 已修复的区域列表...'
SELECT
    region_id,
    name,
    region_type,
    jsonb_array_length(polygon) as point_count,
    is_active
FROM regions
WHERE name LIKE '%自动修复%' OR name LIKE '%需要重新配置%'
ORDER BY name
LIMIT 20;

-- ============================================================================
-- Phase 5: 添加数据库约束（可选 - 取消注释以启用）
-- ============================================================================

\echo ''
\echo '============================================================'
\echo 'Phase 5: 添加数据库约束（可选）'
\echo '============================================================'
\echo ''

-- 注意：只有在确认所有数据都已修复后才启用约束

-- 5.1 设置polygon字段为NOT NULL
-- \echo '1. 设置polygon为NOT NULL...'
-- ALTER TABLE regions
-- ALTER COLUMN polygon SET NOT NULL;
-- \echo '✓ polygon字段已设置为NOT NULL'

-- 5.2 添加CHECK约束：至少3个点
-- \echo ''
-- \echo '2. 添加CHECK约束：至少3个点...'
-- ALTER TABLE regions
-- ADD CONSTRAINT check_polygon_min_length
-- CHECK (jsonb_array_length(polygon) >= 3);
-- \echo '✓ 已添加CHECK约束：polygon至少3个点'

-- 5.3 添加CHECK约束：polygon必须是数组
-- \echo ''
-- \echo '3. 添加CHECK约束：polygon必须是数组...'
-- ALTER TABLE regions
-- ADD CONSTRAINT check_polygon_is_array
-- CHECK (jsonb_typeof(polygon) = 'array');
-- \echo '✓ 已添加CHECK约束：polygon必须是数组'

-- ============================================================================
-- 提交事务
-- ============================================================================

-- 如果一切正常，提交事务
COMMIT;

\echo ''
\echo '============================================================'
\echo '✓ 数据审计和修复完成'
\echo '============================================================'
\echo ''
\echo '后续步骤：'
\echo '1. 检查修复后的数据是否符合预期'
\echo '2. 通知用户重新配置被标记为[需要重新配置]的区域'
\echo '3. 如果一切正常，可以启用Phase 5的约束（取消注释并重新运行）'
\echo ''
