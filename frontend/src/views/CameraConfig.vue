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
              <div class="header-extra-container">
                <n-tag type="info" size="small">
                  <template #icon>
                    <n-icon><CameraOutline /></n-icon>
                  </template>
                  共 {{ cameras.length }} 个摄像头
                </n-tag>
              </div>
            </template>

            <!-- 工具栏：搜索 / 筛选 / 刷新状态 / 自动刷新 -->
            <div class="table-toolbar">
              <div class="toolbar-wrap-container">
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
              </div>
            </div>

            <n-data-table
              :columns="columns"
              :data="filteredCameras"
              :loading="loading"
              :pagination="false"
              :bordered="false"
              size="medium"
              :scroll-x="1250"
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
            <!-- 编辑模式下显示ID（只读） -->
            <n-form-item v-if="mode === 'edit'" label="ID（系统自动生成）" path="id">
              <n-input
                v-model:value="formData.id"
                :input-props="{ autocomplete: 'off' }"
                disabled
                placeholder="系统自动生成的唯一标识"
              />
              <n-text depth="3" style="margin-left: 12px; font-size: 12px">
                ID由系统自动生成，不可修改
              </n-text>
            </n-form-item>

            <n-form-item label="名称" path="name">
              <n-input
                v-model:value="formData.name"
                placeholder="例如: 大门口 USB0"
                :input-props="{ autocomplete: 'off' }"
              />
              <n-text depth="3" style="margin-left: 12px; font-size: 12px" v-if="mode === 'create'">
                名称用于识别摄像头，建议使用有意义的名称
              </n-text>
            </n-form-item>

            <n-form-item label="来源" path="source">
              <n-input
                v-model:value="formData.source"
                placeholder="0 或 rtsp://username:password@ip:554/stream"
                :input-props="{ autocomplete: 'off' }"
              />
            </n-form-item>

            <n-form-item label="位置（可选）" path="location">
              <n-input
                v-model:value="formData.location"
                placeholder="例如: 大门口、车间1号"
                :input-props="{ autocomplete: 'off' }"
              />
            </n-form-item>

            <n-form-item label="摄像头类型（可选）" path="camera_type">
              <n-select
                v-model:value="formData.camera_type"
                placeholder="选择摄像头类型"
                :options="cameraTypeOptions"
                clearable
              />
            </n-form-item>

            <n-form-item label="配置状态（可选）" path="status">
              <n-select
                v-model:value="formData.status"
                placeholder="选择配置状态"
                :options="statusOptions"
              />
              <n-text depth="3" style="margin-left: 12px; font-size: 12px">
                激活：允许启动检测；停用：禁止启动检测
              </n-text>
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

            <!-- 视频流配置 -->
            <n-divider style="margin: 16px 0">检测与视频流配置</n-divider>

            <n-form-item label="检测频率" path="log_interval">
              <n-input-number
                v-model:value="formData.log_interval"
                :min="1"
                :max="1000"
                :step="10"
                style="width: 100%"
              />
              <n-text depth="3" style="margin-left: 12px; font-size: 12px">
                每 {{ formData.log_interval }} 帧检测一次，视频流将同步显示检测结果
              </n-text>
            </n-form-item>

            <n-alert type="info" style="margin-top: 8px">
              <template #icon>
                <n-icon><InformationCircleOutline /></n-icon>
              </template>
              <strong>说明：</strong>检测频率同时控制检测和视频流推送的频率。视频流将显示检测后的结果（带标注的帧）。
            </n-alert>

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

      <!-- 视频流弹窗 -->
      <VideoStreamModal
        v-if="videoStreamVisible && currentStreamCamera"
        :camera-id="currentStreamCamera.id"
        :camera-name="currentStreamCamera.name"
        @close="closeVideoStream"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted, h, computed, watch } from 'vue'
import {
  NCard, NForm, NFormItem, NInput, NInputNumber, NButton, NAlert,
  NDataTable, NText, NTag, NSpace, NPopconfirm, NIcon, NSwitch, NModal, NSlider, NDivider, NSelect, useMessage
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
  TrashOutline,
  EyeOutline,
  PencilOutline,
  PowerOutline,
  VideocamOutline,
  CheckmarkCircleOutline,
  CloseCircleOutline
} from '@vicons/ionicons5'
import { useCameraStore } from '@/stores/camera'
import { PageHeader, DataCard } from '@/components/common'
import CameraStatsModal from '@/components/CameraStatsModal.vue'
import VideoStreamModal from '@/components/VideoStreamModal.vue'

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

// 视频流弹窗状态
const videoStreamVisible = ref(false)
const currentStreamCamera = ref<{id: string, name: string} | null>(null)

// 表单数据
const formData = reactive({
  id: '',  // 编辑模式下使用，创建模式下不需要
  name: '',
  source: '',
  location: '',  // 摄像头位置（可选）
  camera_type: 'fixed',  // 摄像头类型（可选，默认fixed）
  status: 'inactive',  // 配置状态（可选，默认inactive）
  resolution: '',
  fps: null as number | null,
  regions_file: '',
  // 检测与视频流配置（简化：只保留检测频率）
  log_interval: 120,
})

// 摄像头类型选项
const cameraTypeOptions = [
  { label: '固定摄像头', value: 'fixed' },
  { label: 'PTZ摄像头', value: 'ptz' },
  { label: '移动摄像头', value: 'mobile' },
  { label: '热成像摄像头', value: 'thermal' },
]

// 配置状态选项
const statusOptions = [
  { label: '激活（允许启动检测）', value: 'active' },
  { label: '停用（禁止启动检测）', value: 'inactive' },
  { label: '维护中', value: 'maintenance' },
  { label: '错误', value: 'error' },
]

// 表单验证规则
const formRules: FormRules = {
  // id 不再是必填字段，由系统自动生成
  name: [
    { required: true, message: '名称 不能为空', trigger: 'blur' }
  ],
  source: [
    { required: true, message: '来源 不能为空', trigger: 'blur' }
  ]
}

// 根据模式动态调整规则
const formRulesComputed = computed<FormRules>(() => {
  // 创建和编辑模式都使用相同的规则（id不需要验证）
  return formRules
})

// 计算属性
const cameras = computed(() => cameraStore.cameras)

// 过滤与搜索
const searchQuery = ref('')
const statusFilter = ref<'all' | 'enabled' | 'disabled'>('all')
const autoRefresh = ref(true)

const filteredCameras = computed(() => {
  let data = cameraStore.camerasWithStatus  // ← 使用带运行状态的列表
  // 兼容 enabled 和 active 字段
  if (statusFilter.value === 'enabled') data = data.filter(c => c.enabled === true || c.active === true)
  else if (statusFilter.value === 'disabled') data = data.filter(c => !(c.enabled === true || c.active === true))
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
    // 💡 优化：合并名称和ID列，垂直显示
    title: '名称 (含 ID)',
    key: 'name',
    width: 180,  // 略微减少宽度（从200px减少到180px），为其他列让出空间
    render: (row: any) => {
      return h(NSpace, { vertical: true, size: 2 }, {
        default: () => [
          h(NText, { strong: true }, { default: () => row.name || '-' }),
          h(NText, {
            style: { fontFamily: 'monospace', fontSize: '11px', color: '#999' }
          }, { default: () => row.id })
        ]
      })
    }
  },
  {
    title: '来源',
    key: 'source',
    width: 180,  // 略微减少宽度（从200px减少到180px），为其他列让出空间
    render: (row: any) => h(NText, {
      style: { fontFamily: 'monospace', fontSize: '11px', color: '#666' },
      title: row.source
    }, { default: () => row.source })
  },
  {
    // 💡 优化：新增位置列（固定宽度）
    title: '位置',
    key: 'location',
    width: 100,  // 固定宽度，确保表头不换行
    render: (row: any) => h(NText, { depth: 3 }, { default: () => row.location || '-' })
  },
  {
    title: '分辨率',
    key: 'resolution',
    width: 110,  // 💡 优化：改为固定宽度，确保表头不换行（"分辨率"三个字需要更多空间）
    render: (row: any) => row.resolution || '-'
  },
  {
    title: 'FPS',
    key: 'fps',
    width: 70,  // 固定宽度，FPS三个字母足够
    render: (row: any) => row.fps || '-'
  },
  // 配置状态列
  {
    title: '配置状态',
    key: 'config_status',
    width: 110,  // 💡 优化：改为固定宽度，确保表头不换行（"配置状态"四个字需要更多空间）
    render: (row: any) => {
      const isActive = row.active ?? row.enabled ?? true
      if (isActive) {
        return h(NTag, { type: 'success', size: 'small' }, { default: () => '●激活' })
      } else {
        return h(NTag, { type: 'default', size: 'small' }, { default: () => '○停用' })
      }
    }
  },
  // 自动启动列
  {
    title: '自动启动',
    key: 'auto_start',
    width: 110,  // 💡 优化：改为固定宽度，确保表头不换行（"自动启动"四个字需要更多空间）
    render: (row: any) => {
      const isActive = row.active ?? row.enabled ?? true
      if (!isActive) {
        return h(NText, { depth: 3 }, { default: () => '-' })
      }
      return h(NSwitch, {
        value: !!row.auto_start,
        size: 'small',
        loading: loading.value,
        'onUpdate:value': (val: boolean) => toggleAutoStartHandler(row.id, val)
      })
    }
  },
  // 运行状态列（实时查询）
  {
    title: '运行状态',
    key: 'runtime_status',
    width: 120,  // 💡 优化：减少宽度（从170px减少到120px），避免挤压其他列
    render: (row: any) => {
      const isActive = row.active ?? row.enabled ?? true
      if (!isActive) {
        // 简化显示，节省空间
        return h(NTag, { type: 'default', size: 'small' }, { default: () => '🚫 禁止' })
      }

      // ✅ 显示实时运行状态（简化显示）
      const status = row.runtime_status
      if (status?.running) {
        // 简化显示：只显示状态标签，PID信息通过tooltip显示
        return h(NTag, {
          type: 'success',
          size: 'small',
          title: status.pid ? `PID: ${status.pid}` : '运行中'
        }, { default: () => '🟢 运行中' })
      } else {
        return h(NTag, { type: 'default', size: 'small' }, { default: () => '⚪ 已停止' })
      }
    }
  },
  {
    title: '操作',
    key: 'actions',
    width: 250,  // 💡 优化：进一步减少宽度（从280px减少到250px），使用图标按钮更紧凑
    render: (row: any) => {
      const isActive = row.active ?? row.enabled ?? true
      const buttons: any[] = []

      // 💡 优化：使用图标按钮，节省空间
      // 详情按钮（始终显示）
      buttons.push(
        h(NButton, {
          size: 'small',
          type: 'info',
          quaternary: true,
          circle: true,
          onClick: () => openStatsModal(row.id),
          title: '查看详情'
        }, {
          icon: () => h(NIcon, { component: EyeOutline })
        })
      )

      if (!isActive) {
        // 停用状态：激活、编辑、删除
        buttons.push(
          h(NButton, {
            size: 'small',
            type: 'success',
            quaternary: true,
            circle: true,
            loading: loading.value,
            onClick: () => activateCameraHandler(row.id),
            title: '激活'
          }, {
            icon: () => h(NIcon, { component: CheckmarkCircleOutline })
          }),
          h(NButton, {
            size: 'small',
            quaternary: true,
            circle: true,
            onClick: () => openEditModal(row),
            title: '编辑'
          }, {
            icon: () => h(NIcon, { component: PencilOutline })
          }),
          h(NPopconfirm, {
            onPositiveClick: () => deleteCamera(row.id)
          }, {
            trigger: () => h(NButton, {
              size: 'small',
              type: 'error',
              quaternary: true,
              circle: true,
              loading: loading.value,
              title: '删除'
            }, {
              icon: () => h(NIcon, { component: TrashOutline })
            }),
            default: () => `确认删除摄像头 ${row.id}?`
          })
        )
      } else {
        // 激活状态：停用、启动、停止、编辑
        buttons.push(
          h(NPopconfirm, {
            onPositiveClick: () => deactivateCameraHandler(row.id)
          }, {
            trigger: () => h(NButton, {
              size: 'small',
              type: 'warning',
              quaternary: true,
              circle: true,
              loading: loading.value,
              title: '停用'
            }, {
              icon: () => h(NIcon, { component: CloseCircleOutline })
            }),
            default: () => '停用将停止检测进程，确认?'
          }),
          h(NButton, {
            size: 'small',
            type: 'primary',
            quaternary: true,
            circle: true,
            loading: loading.value,
            onClick: () => startCamera(row.id),
            title: '启动'
          }, {
            icon: () => h(NIcon, { component: PlayOutline })
          }),
          h(NButton, {
            size: 'small',
            quaternary: true,
            circle: true,
            loading: loading.value,
            onClick: () => stopCamera(row.id),
            title: '停止'
          }, {
            icon: () => h(NIcon, { component: StopOutline })
          }),
          h(NButton, {
            size: 'small',
            quaternary: true,
            circle: true,
            onClick: () => openEditModal(row),
            title: '编辑'
          }, {
            icon: () => h(NIcon, { component: PencilOutline })
          })
        )

        // 查看视频按钮（只在运行时显示）
        const isRunning = row.runtime_status?.running ?? false
        if (isRunning) {
          buttons.push(
            h(NButton, {
              size: 'small',
              type: 'info',
              quaternary: true,
              circle: true,
              onClick: () => openVideoStream(row),
              title: '查看视频'
            }, {
              icon: () => h(NIcon, { component: VideocamOutline })
            })
          )
        }
      }

      return h(NSpace, { size: 'small' }, {
        default: () => buttons
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
    // 编辑模式：只包含非空字段，但确保 log_interval 被包含（即使未修改）
    const payload = collectFormData(false)

    // 确保 log_interval 被包含（如果表单中有值）
    if (formData.log_interval !== undefined && formData.log_interval !== null) {
      payload.log_interval = formData.log_interval
    }

    console.log('[CameraConfig] 更新摄像头:', { id, payload, formData })
    await cameraStore.updateCamera(id, payload)

    // 刷新摄像头列表以显示最新配置
    await cameraStore.fetchCameras()

    clearForm()
    message.success('摄像头更新成功')
    return true
  } catch (error: any) {
    console.error('[CameraConfig] 更新摄像头失败:', error)
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

// 启动摄像头（改进版：带验证）
async function startCamera(id: string) {
  try {
    loading.value = true
    const result = await cameraStore.startCamera(id)
    message.success(result.message)  // 显示详细消息，包含PID
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

// 激活摄像头
async function activateCameraHandler(id: string) {
  try {
    loading.value = true
    await cameraStore.activateCamera(id)
    message.success('摄像头已激活')
  } catch (error: any) {
    message.error(error.message || '激活失败')
  } finally {
    loading.value = false
  }
}

// 停用摄像头
async function deactivateCameraHandler(id: string) {
  try {
    loading.value = true
    await cameraStore.deactivateCamera(id)
    message.success('摄像头已停用')
  } catch (error: any) {
    message.error(error.message || '停用失败')
  } finally {
    loading.value = false
  }
}

// 切换自动启动
async function toggleAutoStartHandler(id: string, autoStart: boolean) {
  try {
    loading.value = true
    await cameraStore.toggleAutoStart(id, autoStart)
    message.success(`已${autoStart ? '开启' : '关闭'}自动启动`)
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
  // 如果WebSocket未连接，则使用轮询作为备用
  if (!cameraStore.wsConnected) {
    statusInterval = window.setInterval(async () => {
      await cameraStore.refreshRuntimeStatus()  // ← 只刷新运行状态，更快
    }, 5000)  // ← 5秒刷新，更及时
  }
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

// 打开视频流弹窗
function openVideoStream(camera: any) {
  currentStreamCamera.value = {
    id: camera.id,
    name: camera.name || camera.id
  }
  videoStreamVisible.value = true
}

// 关闭视频流弹窗
function closeVideoStream() {
  videoStreamVisible.value = false
  currentStreamCamera.value = null
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
  // ID：编辑模式下需要保留，用于标识要更新的摄像头
  formData.id = camera.id || ''
  formData.name = camera.name || ''
  // source 从 metadata 中获取，如果没有则从 camera.source 获取
  formData.source = camera.metadata?.source || camera.source || ''
  // location：摄像头位置
  formData.location = camera.location || ''
  // camera_type：摄像头类型
  formData.camera_type = camera.camera_type || 'fixed'
  // status：配置状态（是否允许启动检测）
  formData.status = camera.status || 'inactive'

  // resolution 字段：后端返回的是元组 [width, height]，需要转换为字符串 "widthxheight"
  if (camera.resolution) {
    if (Array.isArray(camera.resolution) && camera.resolution.length === 2) {
      // 元组格式：[1920, 1080] -> "1920x1080"
      formData.resolution = `${camera.resolution[0]}x${camera.resolution[1]}`
    } else if (typeof camera.resolution === 'string') {
      // 字符串格式：直接使用
      formData.resolution = camera.resolution
    } else {
      formData.resolution = ''
    }
  } else {
    formData.resolution = ''
  }

  formData.fps = camera.fps || null
  formData.regions_file = camera.regions_file || ''
  // 检测与视频流配置（从camera配置或默认值）
  formData.log_interval = camera.log_interval ?? 120
}

// 收集表单数据
function collectFormData(includeEmpty: boolean) {
  const payload: any = {}

  // ID处理：
  // - 创建模式：不包含 id，由后端自动生成UUID
  // - 编辑模式：包含 id（用于标识要更新的摄像头）
  if (mode.value === 'edit' && formData.id) {
    payload.id = formData.id.trim()
  }
  // 创建模式下不包含 id，让后端自动生成

  // name 字段：创建和编辑模式都需要
  if (mode.value === 'create' && (includeEmpty || formData.name.trim())) {
    payload.name = formData.name.trim()
  } else if (mode.value === 'edit' && formData.name.trim()) {
    payload.name = formData.name.trim()
  }

  // source 字段：创建模式下必填，编辑模式下允许修改
  // 在编辑模式下，source 字段总是被包含在 payload 中（如果表单中有值）
  if (mode.value === 'create') {
    // 创建模式：source 是必填的
    if (includeEmpty || formData.source.trim()) {
      payload.source = formData.source.trim()
    }
  } else {
    // 编辑模式：source 字段允许修改，如果表单中有值则包含
    // 注意：formData.source 在 fillForm 时会被填充为当前值
    // 如果用户修改了 source，新值会被包含；如果用户没有修改，原有值也会被包含
    if (formData.source !== undefined && formData.source !== null && formData.source.trim()) {
      payload.source = formData.source.trim()
    }
  }

  // resolution 字段：需要将字符串 "widthxheight" 转换为数组 [width, height]
  // 后端期望的是列表格式，如 [1920, 1080]
  if (formData.resolution) {
    // 确保 resolution 是字符串类型
    const resolutionStr = typeof formData.resolution === 'string'
      ? formData.resolution.trim()
      : String(formData.resolution || '').trim()

    if (resolutionStr) {
      // 解析 "1280x720" 格式
      if (resolutionStr.includes('x')) {
        const parts = resolutionStr.split('x')
        if (parts.length === 2) {
          const width = parseInt(parts[0].trim(), 10)
          const height = parseInt(parts[1].trim(), 10)
          if (!isNaN(width) && !isNaN(height) && width > 0 && height > 0) {
            payload.resolution = [width, height]
          }
        }
      }
      // 如果不符合格式，不包含在 payload 中（编辑模式下，不会更新该字段）
    }
  }
  // 注意：编辑模式下，如果 resolution 为空或不合法，不包含在 payload 中，保持原值

  if (includeEmpty || formData.fps !== null) payload.fps = formData.fps

  // location 字段：可选
  if (formData.location && formData.location.trim()) {
    payload.location = formData.location.trim()
  }

  // camera_type 字段：可选，默认 fixed
  if (formData.camera_type) {
    payload.camera_type = formData.camera_type
  }

  // status 字段：可选，默认 inactive
  // 注意：后端期望的是 status 字段，同时也会使用 active 标志（用于兼容）
  if (formData.status) {
    payload.status = formData.status
    // 同时设置 active 标志（用于兼容旧代码）
    payload.active = formData.status === 'active'
  }

  // regions_file 字段：确保是字符串类型
  // 编辑模式下，如果 regions_file 为空，不包含在 payload 中（保持原值）
  if (formData.regions_file !== undefined && formData.regions_file !== null) {
    const regionsFileStr = typeof formData.regions_file === 'string'
      ? formData.regions_file.trim()
      : String(formData.regions_file).trim()
    // 编辑模式下，即使为空字符串，如果用户清空了字段，也应该更新
    if (includeEmpty || regionsFileStr) {
      payload.regions_file = regionsFileStr
    }
  } else if (includeEmpty) {
    // 创建模式下，如果 regions_file 未设置，设置为空字符串
    payload.regions_file = ''
  }

  // 检测与视频流配置（简化：只保留检测频率）
  // 确保 log_interval 被包含（编辑模式下也需要）
  if (includeEmpty || (formData.log_interval !== undefined && formData.log_interval !== null)) {
    payload.log_interval = formData.log_interval
  }

  return payload
}

// 清空表单
function clearForm() {
  formData.id = ''
  formData.name = ''
  formData.source = ''
  formData.location = ''
  formData.camera_type = 'fixed'
  formData.status = 'inactive'
  formData.resolution = ''
  formData.fps = null
  formData.regions_file = ''
  // 检测与视频流配置重置为默认值
  formData.log_interval = 120
}

// 重置表单
function resetForm() {
  clearForm()
  formRef.value?.restoreValidation()
}

// 已移除逐帧模式监听（配置已简化）

const refreshCameras = async () => {
  try {
    await cameraStore.fetchCameras()
  } catch (error) {
    console.error('刷新摄像头列表失败:', error)
  }
}

onMounted(async () => {
  try {
    // 1. 先获取摄像头列表
    await cameraStore.fetchCameras()

    // 2. 立即刷新运行状态（确保状态不丢失）
    let statuses = await cameraStore.refreshRuntimeStatus()

    // 3. 如果刷新失败或返回空数据，再次尝试刷新（最多3次）
    let retryCount = 0
    const maxRetries = 3

    // 检查返回的状态数据是否有效（只要返回了数据就认为刷新成功，即使没有运行中的摄像头）
    const hasValidStatus = statuses && typeof statuses === 'object' && Object.keys(statuses).length > 0

    if (!hasValidStatus) {
      // 如果第一次刷新没有获取到有效数据，尝试重试
      while (retryCount < maxRetries) {
        retryCount++
        console.debug(`摄像头状态刷新未获取到有效数据，重试 ${retryCount}/${maxRetries}...`)
        // 等待一小段时间后重试
        await new Promise(resolve => setTimeout(resolve, 500))
        statuses = await cameraStore.refreshRuntimeStatus()

        // 再次检查是否获取到有效数据
        const retryValidStatus = statuses && typeof statuses === 'object' && Object.keys(statuses).length > 0
        if (retryValidStatus) {
          console.debug(`摄像头状态刷新成功（重试后），共 ${Object.keys(statuses).length} 个摄像头`)
          break
        }

        if (retryCount >= maxRetries) {
          console.warn('摄像头状态刷新失败，已达到最大重试次数')
        }
      }
    } else {
      // 如果第一次刷新就获取到有效数据，说明刷新成功
      const runningCount = Object.values(cameraStore.runtimeStatus).filter((s: any) => s?.running).length
      console.debug(`摄像头状态刷新成功，运行中的摄像头数: ${runningCount}/${Object.keys(statuses).length}`)
    }

    // 4. 启动自动刷新
    if (autoRefresh.value) {
      startStatusInterval()
    }
  } catch (error) {
    console.error('初始化摄像头状态失败:', error)
    // 即使失败，也启动自动刷新，让后续刷新能够恢复状态
    if (autoRefresh.value) {
      startStatusInterval()
    }
  }
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
  overflow: visible; /* 💡 优化：改为 visible，允许内容换行后显示 */
  min-width: 0; /* 允许收缩 */
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
  min-width: 0; /* 💡 优化：允许收缩 */
  overflow: visible; /* 💡 优化：允许内容换行后显示 */
}

.table-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0; /* 💡 优化：允许卡片收缩 */
  overflow: visible; /* 💡 优化：改为 visible，允许 header 和 toolbar 换行后显示 */
}

/* 💡 优化：确保 DataCard 容器宽度正确 */
.table-card :deep(.n-card) {
  min-width: 0;
  width: 100%; /* 确保占满父容器 */
  overflow: visible; /* 💡 优化：改为 visible，允许 header 换行后显示 */
}

.table-card :deep(.n-card__header) {
  min-width: 0;
  width: 100%; /* 确保占满父容器 */
  overflow: visible; /* header 允许换行 */
  box-sizing: border-box; /* 确保包含 padding */
}

.table-card :deep(.n-card__content) {
  min-width: 0;
  overflow: auto; /* content 区域可以滚动 */
}

/* 💡 优化：响应式工具栏容器，允许换行，确保右侧内容始终可见 */
.toolbar-wrap-container {
  display: flex;
  justify-content: space-between; /* 将左右两组内容推向两端 */
  align-items: center;
  flex-wrap: wrap; /* 💡 关键：允许内容在空间不足时换行 */
  gap: 12px 0; /* 水平间距 12px，垂直间距 0（换行后上下有间距） */
  min-width: 0;
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;
  overflow: visible; /* 💡 优化：确保换行后的内容可见 */
}

.table-toolbar {
  margin-bottom: var(--space-medium);
}

/* 💡 优化：头部extra区域容器，避免挤压，但允许换行 */
.header-extra-container {
  flex-shrink: 0;
  min-width: fit-content;
  /* 移除 max-width 限制，让它在空间不足时能够换行 */
  width: auto;
}

/* 💡 优化：响应式下，DataCard header 允许换行，确保右侧内容始终可见 */
:deep(.data-card-header) {
  display: flex !important;
  justify-content: space-between !important; /* 将左右两组内容推向两端 */
  align-items: center !important;
  flex-wrap: wrap !important; /* 💡 关键：允许内容在空间不足时换行 */
  gap: 12px 0 !important; /* 水平间距 12px，垂直间距 0（换行后上下有间距） */
  min-width: 0 !important;
  max-width: 100% !important;
  width: 100% !important;
  box-sizing: border-box !important;
}

/* 💡 优化：标题区域允许收缩 */
:deep(.data-card-title) {
  flex-shrink: 1;
  min-width: 0;
  flex: 0 1 auto;
  overflow: hidden; /* 标题过长时截断 */
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 💡 优化：extra区域在空间不足时能够换行 */
:deep(.data-card-extra) {
  flex-shrink: 0;
  min-width: fit-content;
  flex: 0 0 auto;
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
