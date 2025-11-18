-- 添加 cameras 表的缺失列（status 和 region_id）
-- Add missing columns to cameras table if they don't exist

-- 检查并添加 status 列
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name = 'cameras'
        AND column_name = 'status'
    ) THEN
        ALTER TABLE cameras
        ADD COLUMN status VARCHAR(20) DEFAULT 'inactive';
        
        UPDATE cameras
        SET status = 'inactive'
        WHERE status IS NULL;
        
        RAISE NOTICE '已添加 status 列到 cameras 表';
    ELSE
        RAISE NOTICE 'status 列已存在，跳过';
    END IF;
END $$;

-- 检查并添加 region_id 列
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name = 'cameras'
        AND column_name = 'region_id'
    ) THEN
        ALTER TABLE cameras
        ADD COLUMN region_id VARCHAR(100);
        
        RAISE NOTICE '已添加 region_id 列到 cameras 表';
    ELSE
        RAISE NOTICE 'region_id 列已存在，跳过';
    END IF;
END $$;

-- 检查并添加 metadata 列
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name = 'cameras'
        AND column_name = 'metadata'
    ) THEN
        ALTER TABLE cameras
        ADD COLUMN metadata JSONB DEFAULT '{}'::jsonb;
        
        UPDATE cameras
        SET metadata = '{}'::jsonb
        WHERE metadata IS NULL;
        
        RAISE NOTICE '已添加 metadata 列到 cameras 表';
    ELSE
        RAISE NOTICE 'metadata 列已存在，跳过';
    END IF;
END $$;

