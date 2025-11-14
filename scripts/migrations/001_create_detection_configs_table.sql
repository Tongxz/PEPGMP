-- 创建检测参数配置表
-- 用途：存储检测相关的参数配置，支持全局默认值和按相机覆盖
-- 创建时间：2025-11-13

-- 检测参数配置表
CREATE TABLE IF NOT EXISTS detection_configs (
    id SERIAL PRIMARY KEY,
    camera_id VARCHAR(100) NULL,  -- NULL表示全局默认值
    config_type VARCHAR(50) NOT NULL,  -- human_detection, hairnet_detection, behavior_recognition, pose_detection, detection_rules, system
    config_key VARCHAR(100) NOT NULL,  -- 配置项名称（如confidence_threshold, iou_threshold等）
    config_value JSONB NOT NULL,  -- 配置值（可以是各种类型：number, string, boolean, object, array）
    description TEXT,  -- 配置项描述
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(camera_id, config_type, config_key)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_detection_configs_camera ON detection_configs(camera_id);
CREATE INDEX IF NOT EXISTS idx_detection_configs_type ON detection_configs(config_type);
CREATE INDEX IF NOT EXISTS idx_detection_configs_camera_type ON detection_configs(camera_id, config_type);

-- 添加注释
COMMENT ON TABLE detection_configs IS '检测参数配置表，存储检测相关的参数配置';
COMMENT ON COLUMN detection_configs.camera_id IS '摄像头ID，NULL表示全局默认值';
COMMENT ON COLUMN detection_configs.config_type IS '配置类型：human_detection, hairnet_detection, behavior_recognition, pose_detection, detection_rules, system';
COMMENT ON COLUMN detection_configs.config_key IS '配置项名称（如confidence_threshold, iou_threshold等）';
COMMENT ON COLUMN detection_configs.config_value IS '配置值（JSONB格式，可以是各种类型）';
COMMENT ON COLUMN detection_configs.description IS '配置项描述';
