# 摄像头ID设计说明

## 设计原则

### 1. ID 自动生成（UUID）

- **唯一性**：使用 UUID 作为主键，确保全局唯一
- **自动生成**：由数据库自动生成，无需用户手动指定
- **标准化**：符合数据库设计最佳实践

### 2. 名称用户自定义

- **可读性**：用户可以为摄像头指定有意义的名称（如 `入口摄像头`, `车间监控1号` 等）
- **辨识度**：名称比UUID更易于识别和记忆
- **业务需求**：满足实际业务场景中对摄像头标识的需求

### 3. 数据库表结构

```sql
CREATE TABLE cameras (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),  -- 自动生成的UUID
    name VARCHAR(100) NOT NULL,  -- 用户自定义的名称
    location VARCHAR(200),
    status VARCHAR(20) DEFAULT 'inactive',
    camera_type VARCHAR(50) DEFAULT 'fixed',
    resolution JSONB,
    fps INTEGER,
    region_id VARCHAR(100),
    metadata JSONB DEFAULT '{}'::jsonb,
    stream_url VARCHAR(500),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
)
```

### 4. API 设计

**创建摄像头**（POST `/api/v1/cameras`）：
```json
{
  "name": "入口摄像头",  // 必填：用户自定义名称
  "source": "rtsp://...",  // 必填：视频源
  "location": "入口处",  // 可选
  "resolution": [1920, 1080],  // 可选
  // ... 其他字段
  // 注意：不需要提供 id，由数据库自动生成
}
```

**响应**：
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",  // 自动生成的UUID
  "name": "入口摄像头",
  // ... 其他字段
}
```

### 5. 优势

- ✅ **唯一性保证**：UUID 确保全局唯一，避免ID冲突
- ✅ **自动管理**：无需应用层处理ID生成逻辑
- ✅ **可读性**：用户通过名称识别摄像头，而不是UUID
- ✅ **标准化**：符合数据库设计最佳实践
- ✅ **扩展性**：支持分布式系统，无需中央ID生成器

### 6. 注意事项

- ID 由数据库自动生成，前端不需要提供
- 名称（name）是用户自定义的，用于显示和识别
- 如果需要在更新时指定ID，可以通过 `id` 字段提供（用于更新场景）
- UUID 格式：`550e8400-e29b-41d4-a716-446655440000`

