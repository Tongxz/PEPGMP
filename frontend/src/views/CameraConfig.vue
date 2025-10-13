<template>
  <div class="camera-config-page">
    <!-- 页面头部 -->
    <PageHeader
      title="摄像头配置管理"
      description="管理摄像头参数、进程状态与区域文件映射"
      icon="📷"
    >
      <template #extra>
        <n-space>
          <n-button type="primary" @click="openCreateModal">
            <template #icon>
              <n-icon><AddOutline /></n-icon>
            </template>
            新增摄像头
          </n-button>
          <n-button @click="refreshCameras" :loading="loading">
            <template #icon>
              <n-icon><RefreshOutline /></n-icon>
            </template>
            刷新列表
          </n-button>
        </n-space>
      </template>
    </PageHeader>

    <!-- 主要内容区 -->
    <div class="camera-content">
      <!-- 双栏布局：配置表单 & 摄像头列表 -->
      <div class="camera-layout">
        <!-- 配置表单 - 固定宽度 -->
        <div class="camera-form-section" v-if="false">
          <DataCard title="添加/编辑摄像头" class="form-card">
            <n-form ref="formRef" :model="formData" :rules="formRules" label-placement="top" size="medium">
              <n-form-item label="ID（唯一标识）" path="id">
                <n-input
                  v-model:value="formData.id"
                  placeholder="例如: cam0"
                  :input-props="{ autocomplete: 'off' }"
                />
              </n-form-item>

              <n-form-item label="名称" path="name">
                <n-input
                  v-model:value="formData.name"
                  placeholder="例如: 大门口 USB0"
                  :input-props="{ autocomplete: 'off' }"
                />
              </n-form-item>

              <n-form-item label="来源" path="source">
                <n-input
                  v-model:value="formData.source"
                  placeholder="0 或 rtsp://username:password@ip:554/stream"
                  :input-props="{ autocomplete: 'off' }"
                />
              </n-form-item>

              <n-form-item label="分辨率（可选）" path="resolution">
                <n-input
                  v-model:value="formData.resolution"
                  placeholder="1280x720"
                  :input-props="{ autocomplete: 'off' }"
                />
              </n-form-item>

              <n-form-item label="帧率（可选）" path="fps">
                <n-input-number
                  v-model:value="formData.fps"
                  :min="1"
                  :max="120"
                  placeholder="20"
                  style="width: 100%"
                />
              </n-form-item>

              <n-form-item label="区域文件（可选）" path="regions_file">
                <n-input
                  v-model:value="formData.regions_file"
                  placeholder="config/regions_site_sink.json"
                  :input-props="{ autocomplete: 'off' }"
                />
              </n-form-item>

              <div class="form-actions">
                <n-space>
                  <n-button type="primary" @click="createCamera" :loading="loading" size="medium">
                    <template #icon>
                      <n-icon><AddOutline /></n-icon>
                    </template>
                    创建
                  </n-button>
                  <n-button type="default" @click="updateCamera" :loading="loading" size="medium">
                    <template #icon>
                      <n-icon><CreateOutline /></n-icon>
                    </template>
                    更新
                  </n-button>
                  <n-button quaternary @click="resetForm" size="medium">
                    <template #icon>
                      <n-icon><RefreshOutline /></n-icon>
                    </template>
                    重置
                  </n-button>
                </n-space>
              </div>

              <n-alert type="info" class="form-tip">
                <template #icon>
                  <n-icon><InformationCircleOutline /></n-icon>
                </template>
                <strong>提示：</strong>更新时只需填写要修改的字段，未填写的字段保留原值。
              </n-alert>
            </n-form>
          </DataCard>
        </div>

        <!-- 摄像头列表 - 占满剩余空间 -->
        <div class="camera-table-section">
          <DataCard title="已配置摄像头" class="table-card">
            <template #extra>
              <n-tag type="info" size="small">
                <template #icon>
                  <n-icon><CameraOutline /></n-icon>
                </template>
                共 {{ cameras.length }} 个摄像头
              </n-tag>
            </template>

            <!-- 工具栏：搜索 / 筛选 / 刷新状态 / 自动刷新 -->
            <div class="table-toolbar">
              <n-space justify="space-between" align="center" wrap>
                <n-space align="center" wrap>
                  <n-input
                    v-model:value="searchQuery"
                    placeholder="搜索ID/名称/来源..."
                    clearable
                    style="width: 240px"
                  />
                  <n-button tertiary :type="statusFilter === 'all' ? 'primary' : 'default'" @click="statusFilter = 'all'">全部</n-button>
                  <n-button tertiary :type="statusFilter === 'enabled' ? 'primary' : 'default'" @click="statusFilter = 'enabled'">已启用</n-button>
                  <n-button tertiary :type="statusFilter === 'disabled' ? 'primary' : 'default'" @click="statusFilter = 'disabled'">已禁用</n-button>
                </n-space>
                <n-space align="center" wrap>
                  <n-switch v-model:value="autoRefresh" size="small">
                    <template #checked>自动刷新</template>
                    <template #unchecked>手动刷新</template>
                  </n-switch>
                  <n-button quaternary @click="refreshStatus" :loading="loading">
                    <template #icon>
                      <n-icon><RefreshOutline /></n-icon>
                    </template>
                    刷新状态
                  </n-button>
                </n-space>
              </n-space>
            </div>

            <n-data-table
              :columns="columns"
              :data="filteredCameras"
              :loading="loading"
              :pagination="false"
              :bordered="false"
              size="medium"
              :scroll-x="800"
              class="camera-table"
            />

            <div class="config-info">
              <n-space align="center">
                <n-icon size="16" color="var(--text-color-disabled)">
                  <DocumentTextOutline />
                </n-icon>
                <n-text depth="3">
                  <strong>配置文件：</strong>
                  <n-text code>config/cameras.yaml</n-text>
                </n-text>
              </n-space>
            </div>
          </DataCard>
        </div>
      </div>

      <!-- 编辑/新增 弹窗 -->
      <n-modal v-model:show="modalVisible" :mask-closable="false" :closable="false" transform-origin="center">
        <n-card :title="modalTitle" size="small" style="width: 720px; max-width: 90vw;">
          <n-form ref="formRef" :model="formData" :rules="formRulesComputed" label-placement="top" size="medium">
            <n-form-item label="ID（唯一标识）" path="id">
              <n-input
                v-model:value="formData.id"
                placeholder="例如: cam0"
                :input-props="{ autocomplete: 'off' }"
                :disabled="mode === 'edit'"
              />
            </n-form-item>

            <n-form-item label="名称" path="name" v-if="mode === 'create'">
              <n-input
                v-model:value="formData.name"
                placeholder="例如: 大门口 USB0"
                :input-props="{ autocomplete: 'off' }"
              />
            </n-form-item>

            <n-form-item label="来源" path="source" v-if="mode === 'create'">
              <n-input
                v-model:value="formData.source"
                placeholder="0 或 rtsp://username:password@ip:554/stream"
                :input-props="{ autocomplete: 'off' }"
              />
            </n-form-item>

            <n-form-item label="分辨率（可选）" path="resolution">
              <n-input
                v-model:value="formData.resolution"
                placeholder="1280x720"
                :input-props="{ autocomplete: 'off' }"
              />
            </n-form-item>

            <n-form-item label="帧率（可选）" path="fps">
              <n-input-number
                v-model:value="formData.fps"
                :min="1"
                :max="120"
                placeholder="20"
                style="width: 100%"
              />
            </n-form-item>

            <n-form-item label="区域文件（可选）" path="regions_file">
              <n-input
                v-model:value="formData.regions_file"
                placeholder="config/regions_site_sink.json"
                :input-props="{ autocomplete: 'off' }"
              />
            </n-form-item>

            <div class="form-actions">
              <n-space>
                <n-button type="primary" @click="onSubmitModal" :loading="loading">
                  <template #icon>
                    <n-icon><CreateOutline /></n-icon>
                  </template>
                  {{ submitLabel }}
                </n-button>
                <n-button quaternary @click="onCloseModal">取消</n-button>
              </n-space>
            </div>

            <n-alert type="info" class="form-tip">
              <template #icon>
                <n-icon><InformationCircleOutline /></n-icon>
              </template>
              <strong>提示：</strong>更新时只需填写要修改的字段，未填写的字段保留原值。
            </n-alert>
          </n-form>
        </n-card>
      </n-modal>

      <!-- 统计监控模态框 -->
      <CameraStatsModal
        v-model="statsModalVisible"
        :camera-id="currentStatsCamera"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted, h, computed, watch } from 'vue'
import {
  NCard, NForm, NFormItem, NInput, NInputNumber, NButton, NAlert,
  NDataTable, NText, NTag, NSpace, NPopconfirm, NIcon, NSwitch, NModal, useMessage
} from 'naive-ui'
import type { DataTableColumns, FormInst, FormRules } from 'naive-ui'
import {
  RefreshOutline,
  AddOutline,
  CreateOutline,
  CameraOutline,
  DocumentTextOutline,
  InformationCircleOutline,
  PlayOutline,
  StopOutline,
  TrashOutline
} from '@vicons/ionicons5'
import { useCameraStore } from '@/stores/camera'
import { PageHeader, DataCard } from '@/components/common'
import CameraStatsModal from '@/components/CameraStatsModal.vue'

// 使用 Pinia store
const cameraStore = useCameraStore()
const message = useMessage()

// 统计模态框状态
const statsModalVisible = ref(false)
const currentStatsCamera = ref('')

// 表单相关
const formRef = ref<FormInst | null>(null)
const loading = ref(false)
let statusInterval: number | null = null

// 弹窗状态
const modalVisible = ref(false)
const mode = ref<'create' | 'edit'>('create')
const modalTitle = computed(() => (mode.value === 'create' ? '新增摄像头' : '编辑摄像头'))
const submitLabel = computed(() => (mode.value === 'create' ? '创建' : '更新'))

// 表单数据
const formData = reactive({
  id: '',
  name: '',
  source: '',
  resolution: '',
  fps: null as number | null,
  regions_file: ''
})

// 表单验证规则
const formRules: FormRules = {
  id: [
    { required: true, message: 'ID 不能为空', trigger: 'blur' }
  ],
  name: [
    { required: true, message: '名称 不能为空', trigger: 'blur' }
  ],
  source: [
    { required: true, message: '来源 不能为空', trigger: 'blur' }
  ]
}

// 根据模式动态调整规则
const formRulesComputed = computed<FormRules>(() => {
  return mode.value === 'create' ? formRules : { id: formRules.id }
})

// 计算属性
const cameras = computed(() => cameraStore.cameras)

// 过滤与搜索
const searchQuery = ref('')
const statusFilter = ref<'all' | 'enabled' | 'disabled'>('all')
const autoRefresh = ref(true)

const filteredCameras = computed(() => {
  let data = cameraStore.cameras
  if (statusFilter.value === 'enabled') data = data.filter(c => c.enabled)
  else if (statusFilter.value === 'disabled') data = data.filter(c => !c.enabled)
  const q = searchQuery.value.trim().toLowerCase()
  if (q) {
    data = data.filter(c =>
      (c.id || '').toLowerCase().includes(q) ||
      (c.name || '').toLowerCase().includes(q) ||
      (c.source || '').toLowerCase().includes(q) ||
      (c.resolution || '').toLowerCase().includes(q)
    )
  }
  return data
})

// 表格列定义
const columns: DataTableColumns = [
  {
    title: 'ID',
    key: 'id',
    width: 100,
    render: (row: any) => h(NText, { style: { fontFamily: 'monospace', fontSize: '12px' } }, { default: () => row.id })
  },
  {
    title: '名称',
    key: 'name',
    width: 150
  },
  {
    title: '来源',
    key: 'source',
    width: 200,
    render: (row: any) => h(NText, {
      style: { fontFamily: 'monospace', fontSize: '11px', color: '#666' },
      title: row.source
    }, { default: () => row.source })
  },
  {
    title: '分辨率',
    key: 'resolution',
    width: 100,
    render: (row: any) => row.resolution || '-'
  },
  {
    title: 'FPS',
    key: 'fps',
    width: 80,
    render: (row: any) => row.fps || '-'
  },
  // 新增启用开关列
  {
    title: '启用',
    key: 'enabled',
    width: 100,
    render: (row: any) => h(NSwitch, {
      value: !!row.enabled,
      size: 'small',
      loading: loading.value,
      'onUpdate:value': (val: boolean) => toggleEnabled(row.id, val)
    })
  },
  {
    title: '状态',
    key: 'status',
    width: 120,
    render: (row: any) => {
      // 简化状态显示，基于enabled字段
      if (row.enabled) {
        return h(NTag, { type: 'success', size: 'small' }, { default: () => '已启用' })
      } else {
        return h(NTag, { type: 'default', size: 'small' }, { default: () => '已禁用' })
      }
    }
  },
  {
    title: '操作',
    key: 'actions',
    width: 350,
    render: (row: any) => {
      return h(NSpace, { size: 'small' }, {
        default: () => [
          h(NButton, {
            size: 'small',
            type: 'info',
            onClick: () => openStatsModal(row.id)
          }, { default: () => '查看统计' }),
          h(NButton, {
            size: 'small',
            type: 'default',
            onClick: () => openEditModal(row)
          }, { default: () => '编辑' }),
          h(NButton, {
            size: 'small',
            type: 'primary',
            loading: loading.value,
            onClick: () => startCamera(row.id)
          }, { default: () => '启动' }),
          h(NButton, {
            size: 'small',
            type: 'default',
            loading: loading.value,
            onClick: () => stopCamera(row.id)
          }, { default: () => '停止' }),
          h(NPopconfirm, {
            onPositiveClick: () => deleteCamera(row.id)
          }, {
            trigger: () => h(NButton, {
              size: 'small',
              type: 'error',
              loading: loading.value
            }, { default: () => '删除' }),
            default: () => `确认删除摄像头 ${row.id} ?`
          })
        ]
      })
    }
  }
]

// 创建摄像头
async function createCamera(): Promise<boolean> {
  if (!formRef.value) return false

  try {
    await formRef.value.validate()
    loading.value = true

    const payload = collectFormData(true)
    await cameraStore.createCamera(payload)

    clearForm()
    message.success('摄像头创建成功')
    return true
  } catch (error: any) {
    message.error('创建失败: ' + (error.message || error))
    return false
  } finally {
    loading.value = false
  }
}

// 更新摄像头
async function updateCamera(): Promise<boolean> {
  try {
    const id = formData.id.trim()
    if (!id) {
      message.error('请先填写 ID')
      return false
    }

    loading.value = true
    const payload = collectFormData(false)
    await cameraStore.updateCamera(id, payload)

    clearForm()
    message.success('摄像头更新成功')
    return true
  } catch (error: any) {
    message.error('更新失败: ' + (error.message || error))
    return false
  } finally {
    loading.value = false
  }
}

// 删除摄像头
async function deleteCamera(id: string) {
  try {
    loading.value = true
    await cameraStore.deleteCamera(id)
    message.success('摄像头删除成功')
  } catch (error: any) {
    message.error('删除失败: ' + (error.message || error))
  } finally {
    loading.value = false
  }
}

// 启动摄像头
async function startCamera(id: string) {
  try {
    loading.value = true
    await cameraStore.startCamera(id)
    message.success('摄像头启动成功')
  } catch (error: any) {
    message.error('启动失败: ' + (error.message || error))
  } finally {
    loading.value = false
  }
}

// 停止摄像头
async function stopCamera(id: string) {
  try {
    loading.value = true
    await cameraStore.stopCamera(id)
    message.success('摄像头停止成功')
  } catch (error: any) {
    message.error('停止失败: ' + (error.message || error))
  } finally {
    loading.value = false
  }
}

// 启用/禁用摄像头
async function toggleEnabled(id: string, enabled: boolean) {
  try {
    loading.value = true
    await cameraStore.updateCamera(id, { enabled })
    message.success(`已${enabled ? '启用' : '禁用'}摄像头`)
  } catch (error: any) {
    message.error(error.message || '操作失败')
  } finally {
    loading.value = false
  }
}

// 状态刷新
async function refreshStatus() {
  try {
    loading.value = true
    await cameraStore.refreshAllStatus()
  } catch (error) {
    // ignore
  } finally {
    loading.value = false
  }
}

function startStatusInterval() {
  if (statusInterval) window.clearInterval(statusInterval)
  statusInterval = window.setInterval(() => {
    cameraStore.refreshAllStatus().catch(() => {})
  }, 10000)
}

// 弹窗控制
function openCreateModal() {
  mode.value = 'create'
  clearForm()
  modalVisible.value = true
}

function openEditModal(camera: any) {
  mode.value = 'edit'
  fillForm(camera)
  modalVisible.value = true
}

function openStatsModal(cameraId: string) {
  currentStatsCamera.value = cameraId
  statsModalVisible.value = true
}

function onCloseModal() {
  modalVisible.value = false
  formRef.value?.restoreValidation()
}

async function onSubmitModal() {
  const ok = mode.value === 'create' ? await createCamera() : await updateCamera()
  if (ok) {
    modalVisible.value = false
  }
}

// 填充表单
function fillForm(camera: any) {
  formData.id = camera.id || ''
  formData.name = camera.name || ''
  formData.source = camera.source || ''
  formData.resolution = camera.resolution || ''
  formData.fps = camera.fps || null
  formData.regions_file = camera.regions_file || ''
}

// 收集表单数据
function collectFormData(includeEmpty: boolean) {
  const payload: any = {}

  if (includeEmpty || formData.id.trim()) payload.id = formData.id.trim()
  if (includeEmpty || formData.name.trim()) payload.name = formData.name.trim()
  if (includeEmpty || formData.source.trim()) payload.source = formData.source.trim()
  if (includeEmpty || formData.resolution.trim()) payload.resolution = formData.resolution.trim()
  if (includeEmpty || formData.fps !== null) payload.fps = formData.fps
  if (includeEmpty || formData.regions_file.trim()) payload.regions_file = formData.regions_file.trim()

  return payload
}

// 清空表单
function clearForm() {
  formData.id = ''
  formData.name = ''
  formData.source = ''
  formData.resolution = ''
  formData.fps = null
  formData.regions_file = ''
}

// 重置表单
function resetForm() {
  clearForm()
  formRef.value?.restoreValidation()
}

const refreshCameras = async () => {
  try {
    await cameraStore.fetchCameras()
  } catch (error) {
    console.error('刷新摄像头列表失败:', error)
  }
}

onMounted(async () => {
  await cameraStore.fetchCameras()
  if (autoRefresh.value) startStatusInterval()
})

onUnmounted(() => {
  if (statusInterval) window.clearInterval(statusInterval)
  statusInterval = null
})

watch(autoRefresh, (val) => {
  if (val) {
    startStatusInterval()
  } else if (statusInterval) {
    window.clearInterval(statusInterval)
    statusInterval = null
  }
})
</script>

<style scoped>
.camera-config-page {
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: var(--space-large);
}

.camera-content {
  flex: 1;
  overflow: hidden;
}

.camera-layout {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--space-large);
  height: 100%;
}

.camera-form-section {
  display: flex;
  flex-direction: column;
}

.form-card {
  height: fit-content;
  max-height: calc(100vh - 200px);
  overflow-y: auto;
}

.camera-table-section {
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.table-card {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.table-toolbar {
  margin-bottom: var(--space-medium);
}

.camera-table {
  flex: 1;
}

.form-actions {
  margin: var(--space-large) 0 var(--space-medium) 0;
}

.form-tip {
  margin-top: var(--space-medium);
}

.config-info {
  margin-top: var(--space-medium);
  padding-top: var(--space-medium);
  border-top: 1px solid var(--border-color);
}

/* 响应式设计 */
@media (max-width: 1200px) {
  .camera-layout {
    grid-template-columns: 1fr;
    grid-template-rows: auto 1fr;
  }

  .form-card {
    max-height: none;
  }
}

@media (max-width: 768px) {
  .camera-layout {
    gap: var(--space-medium);
  }

  .form-actions {
    margin: var(--space-medium) 0;
  }
}
</style>
