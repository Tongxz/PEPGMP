<template>
  <div class="professional-camera-config">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">相机配置</h1>
        <p class="page-subtitle">管理摄像头设备，配置视频流参数</p>
      </div>
      <div class="header-actions">
        <n-button type="primary" @click="handleAdd">
          <template #icon><n-icon><AddOutline /></n-icon></template>
          添加摄像头
        </n-button>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-cards">
      <div class="stat-card">
        <div class="stat-icon stat-icon-total">
          <n-icon size="24"><VideocamOutline /></n-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ totalCameras }}</div>
          <div class="stat-label">总摄像头数</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon stat-icon-online">
          <n-icon size="24"><CheckmarkCircleOutline /></n-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ onlineCameras }}</div>
          <div class="stat-label">在线</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon stat-icon-offline">
          <n-icon size="24"><CloseCircleOutline /></n-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ offlineCameras }}</div>
          <div class="stat-label">离线</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon stat-icon-fps">
          <n-icon size="24"><SpeedometerOutline /></n-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ avgFps }}fps</div>
          <div class="stat-label">平均帧率</div>
        </div>
      </div>
    </div>

    <!-- 摄像头列表 -->
    <div class="cameras-card">
      <div class="card-toolbar">
        <n-input
          v-model:value="searchText"
          placeholder="搜索摄像头名称或位置"
          clearable
          style="width: 300px"
        >
          <template #prefix>
            <n-icon><SearchOutline /></n-icon>
          </template>
        </n-input>
        <n-select
          v-model:value="filterStatus"
          :options="statusOptions"
          placeholder="筛选状态"
          clearable
          style="width: 150px"
        />
      </div>

      <div class="cameras-grid">
        <div
          v-for="camera in filteredCameras"
          :key="camera.id"
          class="camera-card"
          :class="{ 'camera-offline': camera.status === 'offline' }"
        >
          <div class="camera-preview">
            <img v-if="camera.thumbnail" :src="camera.thumbnail" alt="预览" />
            <div v-else class="preview-placeholder">
              <n-icon size="48" color="#8C9BAB"><VideocamOffOutline /></n-icon>
            </div>
            <div class="camera-status-badge" :class="camera.status">
              <div class="status-dot"></div>
              {{ camera.status === 'online' ? '在线' : '离线' }}
            </div>
          </div>

          <div class="camera-info">
            <h4 class="camera-name">{{ camera.name }}</h4>
            <p class="camera-location">
              <n-icon size="14"><LocationOutline /></n-icon>
              {{ camera.location }}
            </p>

            <div class="camera-details">
              <div class="detail-item">
                <span class="detail-label">IP地址</span>
                <span class="detail-value">{{ camera.ip }}</span>
              </div>
              <div class="detail-item">
                <span class="detail-label">分辨率</span>
                <span class="detail-value">{{ camera.resolution }}</span>
              </div>
              <div class="detail-item">
                <span class="detail-label">帧率</span>
                <span class="detail-value">{{ camera.fps }}fps</span>
              </div>
            </div>

            <div class="camera-actions">
              <n-button size="small" @click="handleEdit(camera)">
                <template #icon><n-icon><CreateOutline /></n-icon></template>
                编辑
              </n-button>
              <n-button size="small" @click="handleTest(camera)">
                <template #icon><n-icon><PlayOutline /></n-icon></template>
                测试
              </n-button>
              <n-button size="small" type="error" @click="handleDelete(camera)">
                <template #icon><n-icon><TrashOutline /></n-icon></template>
                删除
              </n-button>
            </div>
          </div>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-if="filteredCameras.length === 0" class="empty-state">
        <n-icon size="64" color="#8C9BAB"><VideocamOffOutline /></n-icon>
        <p class="empty-text">暂无摄像头数据</p>
        <n-button type="primary" @click="handleAdd">添加摄像头</n-button>
      </div>
    </div>

    <!-- 添加/编辑对话框 -->
    <n-modal v-model:show="showAddDialog" preset="card" :title="isEditMode ? '编辑摄像头' : '添加摄像头'" style="width: 600px">
      <n-form :model="formData" label-placement="left" label-width="100px">
        <n-form-item label="摄像头名称" required>
          <n-input v-model:value="formData.name" placeholder="请输入摄像头名称" />
        </n-form-item>
        <n-form-item label="安装位置" required>
          <n-input v-model:value="formData.location" placeholder="请输入安装位置" />
        </n-form-item>
        <n-form-item label="IP地址" required>
          <n-input v-model:value="formData.ip" placeholder="192.168.1.100" />
        </n-form-item>
        <n-form-item label="RTSP地址" required>
          <n-input v-model:value="formData.rtsp_url" placeholder="rtsp://..." />
        </n-form-item>
        <n-form-item label="分辨率">
          <n-select v-model:value="formData.resolution" :options="resolutionOptions" />
        </n-form-item>
        <n-form-item label="帧率">
          <n-input-number v-model:value="formData.fps" :min="1" :max="60" />
        </n-form-item>
      </n-form>
      <template #footer>
        <div style="display: flex; justify-content: flex-end; gap: 12px">
          <n-button @click="showAddDialog = false">取消</n-button>
          <n-button type="primary" @click="handleSave">保存</n-button>
        </div>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { NButton, NIcon, NInput, NSelect, NModal, NForm, NFormItem, NInputNumber, useMessage } from 'naive-ui'
import {
  AddOutline,
  VideocamOutline,
  VideocamOffOutline,
  CheckmarkCircleOutline,
  CloseCircleOutline,
  SpeedometerOutline,
  SearchOutline,
  LocationOutline,
  CreateOutline,
  PlayOutline,
  TrashOutline
} from '@vicons/ionicons5'

// 导入 API
import {
  getCameras,
  createCamera,
  updateCamera,
  deleteCamera
} from '@/api/modules/cameras'
import { http } from '@/lib/http'

const message = useMessage()

// 统计数据
const totalCameras = ref(0)
const onlineCameras = ref(0)
const offlineCameras = ref(0)
const avgFps = ref(0)
const loading = ref(false)

// 筛选
const searchText = ref('')
const filterStatus = ref<string | null>(null)

const statusOptions = [
  { label: '在线', value: 'online' },
  { label: '离线', value: 'offline' }
]

const resolutionOptions = [
  { label: '1920x1080', value: '1920x1080' },
  { label: '1280x720', value: '1280x720' },
  { label: '640x480', value: '640x480' }
]

// 摄像头数据
const cameras = ref<any[]>([])

const filteredCameras = computed(() => {
  let result = cameras.value

  if (searchText.value) {
    result = result.filter(c =>
      c.name.toLowerCase().includes(searchText.value.toLowerCase()) ||
      c.location.toLowerCase().includes(searchText.value.toLowerCase())
    )
  }

  if (filterStatus.value) {
    result = result.filter(c => c.status === filterStatus.value)
  }

  return result
})

// 获取摄像头数据
const fetchCameras = async () => {
  if (loading.value) return

  loading.value = true
  try {
    const response = await getCameras()

    // 更新统计数据
    totalCameras.value = response.total
    onlineCameras.value = response.online
    offlineCameras.value = response.offline
    avgFps.value = response.avg_fps

    // 更新摄像头列表
    cameras.value = response.cameras

    console.log('摄像头数据加载成功:', {
      total: totalCameras.value,
      online: onlineCameras.value,
      offline: offlineCameras.value,
      avgFps: avgFps.value,
      cameras: cameras.value.length
    })
  } catch (error: any) {
    console.error('获取摄像头数据失败:', error)
    message.error(error.message || '获取摄像头数据失败，请稍后重试')

    // 使用默认值
    totalCameras.value = 0
    onlineCameras.value = 0
    offlineCameras.value = 0
    avgFps.value = 0
    cameras.value = []
  } finally {
    loading.value = false
  }
}

// 对话框
const showAddDialog = ref(false)
const isEditMode = ref(false)
const editingCameraId = ref<string | null>(null)
const formData = ref({
  name: '',
  location: '',
  ip: '',
  rtsp_url: '',
  resolution: '1920x1080',
  fps: 30
})

// 重置表单
const resetForm = () => {
  formData.value = {
    name: '',
    location: '',
    ip: '',
    rtsp_url: '',
    resolution: '1920x1080',
    fps: 30
  }
  isEditMode.value = false
  editingCameraId.value = null
}

// 添加摄像头
const handleAdd = () => {
  resetForm()
  showAddDialog.value = true
}

// 编辑摄像头
const handleEdit = (camera: any) => {
  isEditMode.value = true
  editingCameraId.value = camera.id
  formData.value = {
    name: camera.name,
    location: camera.location,
    ip: camera.ip,
    rtsp_url: camera.rtsp_url,
    resolution: camera.resolution,
    fps: camera.fps
  }
  showAddDialog.value = true
}

// 测试摄像头
const handleTest = async (camera: any) => {
  try {
    loading.value = true
    message.loading('正在测试摄像头连接...', { duration: 0 })

    const response = await http.post(`/cameras/${camera.id}/test`)
    const result = response.data

    message.destroyAll()

    if (result.success) {
      message.success(result.message)
      if (result.details) {
        const details = result.details
        message.info(
          `分辨率: ${details.resolution}, FPS: ${details.fps}`,
          { duration: 5000 }
        )
      }
    } else {
      message.error(result.message)
      if (result.details && result.details.error) {
        message.warning(result.details.error, { duration: 5000 })
      }
    }
  } catch (error: any) {
    message.destroyAll()
    console.error('测试摄像头失败:', error)
    message.error(error.message || '测试摄像头失败')
  } finally {
    loading.value = false
  }
}

// 删除摄像头
const handleDelete = async (camera: any) => {
  // 确认对话框
  const confirmed = confirm(`确定要删除摄像头"${camera.name}"吗？此操作不可恢复。`)
  if (!confirmed) return

  try {
    message.loading('正在删除...')
    await deleteCamera(camera.id)
    message.success('删除成功')

    // 刷新列表
    await fetchCameras()
  } catch (error: any) {
    console.error('删除摄像头失败:', error)
    message.error(error.message || '删除摄像头失败')
  }
}

// 保存摄像头
const handleSave = async () => {
  // 验证表单
  if (!formData.value.name) {
    message.warning('请输入摄像头名称')
    return
  }
  if (!formData.value.location) {
    message.warning('请输入摄像头位置')
    return
  }
  if (!formData.value.rtsp_url) {
    message.warning('请输入RTSP地址')
    return
  }

  try {
    message.loading(isEditMode.value ? '正在更新...' : '正在创建...')

    if (isEditMode.value && editingCameraId.value) {
      // 更新摄像头
      await updateCamera(editingCameraId.value, {
        name: formData.value.name,
        location: formData.value.location,
        rtsp_url: formData.value.rtsp_url,
        resolution: formData.value.resolution,
        fps: formData.value.fps
      })
      message.success('更新成功')
    } else {
      // 创建摄像头
      await createCamera({
        name: formData.value.name,
        location: formData.value.location,
        ip: formData.value.ip,
        rtsp_url: formData.value.rtsp_url,
        resolution: formData.value.resolution,
        fps: formData.value.fps
      })
      message.success('创建成功')
    }

    // 关闭对话框并刷新列表
    showAddDialog.value = false
    resetForm()
    await fetchCameras()
  } catch (error: any) {
    console.error('保存摄像头失败:', error)
    message.error(error.message || '保存摄像头失败')
  }
}

// 初始化
onMounted(() => {
  fetchCameras()
})
</script>

<style scoped lang="scss">
/**
 * 相机配置页面 - 专业版
 */

// 颜色变量
$color-bg: #F7FAFC;
$color-white: #FFFFFF;
$color-border: #E6EDF5;
$color-text-primary: #1F2D3D;
$color-text-secondary: #6B778C;
$color-text-tertiary: #8C9BAB;

$color-online: #52C41A;
$color-offline: #FF4D4F;

.professional-camera-config {
  padding: 24px;
  background: $color-bg;
  min-height: 100vh;
}

// ===== 页面头部 =====
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
  padding: 20px 24px;
  background: $color-white;
  border-radius: 12px;
  border: 1px solid $color-border;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.header-left {
  flex: 1;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: $color-text-primary;
  margin: 0 0 4px 0;
}

.page-subtitle {
  font-size: 14px;
  color: $color-text-secondary;
  margin: 0;
}

// ===== 统计卡片 =====
.stats-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  background: $color-white;
  border-radius: 12px;
  border: 1px solid $color-border;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  transition: all 0.2s ease;

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  }
}

.stat-icon {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  flex-shrink: 0;

  &.stat-icon-total {
    background: rgba(30, 159, 255, 0.1);
    color: #1E9FFF;
  }

  &.stat-icon-online {
    background: rgba(82, 196, 26, 0.1);
    color: $color-online;
  }

  &.stat-icon-offline {
    background: rgba(255, 77, 79, 0.1);
    color: $color-offline;
  }

  &.stat-icon-fps {
    background: rgba(43, 201, 201, 0.1);
    color: #2BC9C9;
  }
}

.stat-content {
  flex: 1;
}

.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: $color-text-primary;
  line-height: 1.2;
  margin-bottom: 4px;
  font-variant-numeric: tabular-nums;
}

.stat-label {
  font-size: 13px;
  color: $color-text-secondary;
}

// ===== 摄像头列表 =====
.cameras-card {
  background: $color-white;
  border-radius: 12px;
  border: 1px solid $color-border;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  padding: 24px;
}

.card-toolbar {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
}

.cameras-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
}

.camera-card {
  border: 1px solid $color-border;
  border-radius: 12px;
  overflow: hidden;
  transition: all 0.2s ease;

  &:hover {
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
    transform: translateY(-2px);
  }

  &.camera-offline {
    opacity: 0.6;
  }
}

.camera-preview {
  position: relative;
  width: 100%;
  padding-top: 56.25%;
  background: #000;
  overflow: hidden;

  img {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
}

.preview-placeholder {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.05);
}

.camera-status-badge {
  position: absolute;
  top: 12px;
  right: 12px;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  backdrop-filter: blur(10px);

  &.online {
    background: rgba(82, 196, 26, 0.9);
    color: #FFFFFF;

    .status-dot {
      background: #FFFFFF;
    }
  }

  &.offline {
    background: rgba(255, 77, 79, 0.9);
    color: #FFFFFF;

    .status-dot {
      background: #FFFFFF;
    }
  }
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.camera-info {
  padding: 16px;
}

.camera-name {
  font-size: 16px;
  font-weight: 600;
  color: $color-text-primary;
  margin: 0 0 8px 0;
}

.camera-location {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: $color-text-secondary;
  margin: 0 0 16px 0;
}

.camera-details {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 16px;
  padding: 12px;
  background: rgba(0, 0, 0, 0.02);
  border-radius: 8px;
}

.detail-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.detail-label {
  font-size: 12px;
  color: $color-text-tertiary;
}

.detail-value {
  font-size: 13px;
  font-weight: 500;
  color: $color-text-primary;
  font-variant-numeric: tabular-nums;
}

.camera-actions {
  display: flex;
  gap: 8px;
}

// ===== 空状态 =====
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 20px;
}

.empty-text {
  margin: 16px 0 24px 0;
  font-size: 16px;
  color: $color-text-secondary;
}

// ===== 响应式 =====
@media (max-width: 1200px) {
  .stats-cards {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .professional-camera-config {
    padding: 16px;
  }

  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }

  .stats-cards {
    grid-template-columns: 1fr;
  }

  .card-toolbar {
    flex-direction: column;

    :deep(.n-input),
    :deep(.n-select) {
      width: 100% !important;
    }
  }

  .cameras-grid {
    grid-template-columns: 1fr;
  }
}
</style>
