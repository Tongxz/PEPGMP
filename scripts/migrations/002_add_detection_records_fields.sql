-- 添加检测记录表缺失字段
-- 版本: 002
-- 创建时间: 2025-12-22
-- 说明: 为 detection_records 表添加 confidence, objects, frame_id, region_id, metadata 字段

-- ============================================
-- 添加缺失字段到 detection_records 表
-- ============================================

-- 添加 confidence 字段（检测置信度）
ALTER TABLE detection_records ADD COLUMN IF NOT EXISTS confidence FLOAT;

-- 添加 objects 字段（检测到的对象列表，JSON格式）
ALTER TABLE detection_records ADD COLUMN IF NOT EXISTS objects JSONB;

-- 添加 frame_id 字段（帧ID）
ALTER TABLE detection_records ADD COLUMN IF NOT EXISTS frame_id VARCHAR(100);

-- 添加 region_id 字段（区域ID）
ALTER TABLE detection_records ADD COLUMN IF NOT EXISTS region_id VARCHAR(50);

-- 添加 metadata 字段（元数据，JSON格式）
ALTER TABLE detection_records ADD COLUMN IF NOT EXISTS metadata JSONB;

-- 添加索引以优化查询性能
CREATE INDEX IF NOT EXISTS idx_detection_records_confidence ON detection_records(confidence);
CREATE INDEX IF NOT EXISTS idx_detection_records_frame_id ON detection_records(frame_id);
CREATE INDEX IF NOT EXISTS idx_detection_records_region_id ON detection_records(region_id);
CREATE INDEX IF NOT EXISTS idx_detection_records_camera_id ON detection_records(camera_id);
CREATE INDEX IF NOT EXISTS idx_detection_records_timestamp ON detection_records(timestamp);

-- 添加注释
COMMENT ON COLUMN detection_records.confidence IS '检测置信度';
COMMENT ON COLUMN detection_records.objects IS '检测到的对象列表（JSON格式）';
COMMENT ON COLUMN detection_records.frame_id IS '帧ID';
COMMENT ON COLUMN detection_records.region_id IS '区域ID';
COMMENT ON COLUMN detection_records.metadata IS '元数据（JSON格式）';
