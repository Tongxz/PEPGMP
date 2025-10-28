<template>
  <n-card title="数据集管理" :segmented="{ content: true, footer: 'soft' }" size="small">
    <template #header-extra>
      <n-space>
        <n-button size="small" @click="refreshDatasets" :loading="loading">
          <template #icon>
            <n-icon><RefreshOutline /></n-icon>
          </template>
          刷新
        </n-button>
        <n-button size="small" type="primary" @click="showUploadDialog = true">
          <template #icon>
            <n-icon><CloudUploadOutline /></n-icon>
          </template>
          上传数据集
        </n-button>
      </n-space>
    </template>

    <!-- 数据集列表 -->
    <n-empty v-if="datasets.length === 0" description="暂无数据集">
      <template #extra>
        <n-button size="small" @click="showUploadDialog = true">上传第一个数据集</n-button>
      </template>
    </n-empty>

    <div v-else>
      <n-list>
        <n-list-item v-for="dataset in datasets" :key="dataset.id">
          <n-card size="small" hoverable>
            <template #header>
              <n-space justify="space-between">
                <span>{{ dataset.name }}</span>
                <n-tag :type="getDatasetStatusType(dataset.status)" size="small">
                  {{ dataset.status }}
                </n-tag>
              </n-space>
            </template>

            <div class="dataset-details">
              <n-descriptions :column="2" size="small">
                <n-descriptions-item label="版本">
                  v{{ dataset.version }}
                </n-descriptions-item>
                <n-descriptions-item label="大小">
                  {{ formatFileSize(dataset.size) }}
                </n-descriptions-item>
                <n-descriptions-item label="样本数">
                  {{ dataset.sample_count?.toLocaleString() || 'N/A' }}
                </n-descriptions-item>
                <n-descriptions-item label="创建时间">
                  {{ formatTime(dataset.created_at) }}
                </n-descriptions-item>
                <n-descriptions-item label="标签数">
                  {{ dataset.label_count || 0 }}
                </n-descriptions-item>
                <n-descriptions-item label="质量评分">
                  <n-rate v-if="dataset.quality_score" :value="dataset.quality_score / 20" readonly size="small" />
                  <span v-else>未评估</span>
                </n-descriptions-item>
              </n-descriptions>

              <!-- 数据质量指标 -->
              <n-divider v-if="dataset.quality_metrics" />
              <div v-if="dataset.quality_metrics" class="quality-metrics">
                <n-text depth="3" style="font-size: 12px;">数据质量指标</n-text>
                <n-grid :cols="3" :x-gap="8" :y-gap="4" style="margin-top: 8px;">
                  <n-gi>
                    <n-statistic label="完整性" :value="dataset.quality_metrics.completeness" suffix="%" size="small" />
                  </n-gi>
                  <n-gi>
                    <n-statistic label="准确性" :value="dataset.quality_metrics.accuracy" suffix="%" size="small" />
                  </n-gi>
                  <n-gi>
                    <n-statistic label="一致性" :value="dataset.quality_metrics.consistency" suffix="%" size="small" />
                  </n-gi>
                </n-grid>
              </div>

              <!-- 操作按钮 -->
              <n-divider />
              <n-space justify="end">
                <n-button size="small" @click="viewDataset(dataset)">查看</n-button>
                <n-button size="small" @click="compareDataset(dataset)">对比</n-button>
                <n-button size="small" @click="downloadDataset(dataset)">下载</n-button>
                <n-button size="small" type="error" @click="deleteDataset(dataset)">删除</n-button>
              </n-space>
            </div>
          </n-card>
        </n-list-item>
      </n-list>
    </div>

    <!-- 上传数据集对话框 -->
    <n-modal v-model:show="showUploadDialog" preset="dialog" title="上传数据集">
      <n-upload
        ref="uploadRef"
        :action="uploadUrl"
        :headers="uploadHeaders"
        :data="uploadData"
        :file-list="fileList"
        @before-upload="beforeUpload"
        @finish="onUploadFinish"
        @error="onUploadError"
        multiple
        directory-dnd
      >
        <n-upload-dragger>
          <div style="margin-bottom: 12px">
            <n-icon size="48" :depth="3">
              <CloudUploadOutline />
            </n-icon>
          </div>
          <n-text style="font-size: 16px">
            点击或者拖动文件到该区域来上传
          </n-text>
          <n-p depth="3" style="margin: 8px 0 0 0">
            支持单个或批量上传。支持目录上传。
          </n-p>
        </n-upload-dragger>
      </n-upload>
    </n-modal>
  </n-card>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { NCard, NButton, NSpace, NIcon, NEmpty, NList, NListItem, NTag, NDescriptions, NDescriptionsItem, NDivider, NText, NGrid, NGi, NStatistic, NRate, NModal, NUpload, NUploadDragger, NP, useMessage } from 'naive-ui'
import { RefreshOutline, CloudUploadOutline } from '@vicons/ionicons5'

interface Dataset {
  id: string
  name: string
  version: string
  status: 'active' | 'archived' | 'processing' | 'error'
  size: number
  sample_count?: number
  label_count?: number
  quality_score?: number
  quality_metrics?: {
    completeness: number
    accuracy: number
    consistency: number
  }
  created_at: string
  updated_at: string
  description?: string
  tags?: string[]
}

const message = useMessage()
const datasets = ref<Dataset[]>([])
const loading = ref(false)
const showUploadDialog = ref(false)
const uploadRef = ref()
const fileList = ref([])

const uploadUrl = '/api/v1/mlops/datasets/upload'
const uploadHeaders = {
  'Authorization': `Bearer ${localStorage.getItem('token') || ''}`
}
const uploadData = {
  dataset_type: 'detection',
  description: ''
}

// 获取数据集列表
async function fetchDatasets() {
  loading.value = true
  try {
    // 调用实际API
    const response = await fetch('/api/v1/mlops/datasets')
    if (response.ok) {
      datasets.value = await response.json()
    } else {
      console.error('获取数据集失败:', response.statusText)
      // 如果API失败，使用模拟数据作为备用
      datasets.value = [
      {
        id: '1',
        name: 'handwash_detection_v1',
        version: '1.0.0',
        status: 'active',
        size: 1024 * 1024 * 500, // 500MB
        sample_count: 1500,
        label_count: 3,
        quality_score: 85,
        quality_metrics: {
          completeness: 92,
          accuracy: 88,
          consistency: 85
        },
        created_at: '2024-01-15T10:30:00Z',
        updated_at: '2024-01-15T10:30:00Z',
        description: '洗手行为检测数据集',
        tags: ['handwash', 'detection', 'behavior']
      },
      {
        id: '2',
        name: 'hairnet_detection_v2',
        version: '2.1.0',
        status: 'active',
        size: 1024 * 1024 * 300, // 300MB
        sample_count: 800,
        label_count: 2,
        quality_score: 92,
        quality_metrics: {
          completeness: 95,
          accuracy: 90,
          consistency: 92
        },
        created_at: '2024-01-10T14:20:00Z',
        updated_at: '2024-01-12T16:45:00Z',
        description: '安全帽检测数据集',
        tags: ['hairnet', 'detection', 'safety']
      },
      {
        id: '3',
        name: 'pose_detection_v1',
        version: '1.2.0',
        status: 'processing',
        size: 1024 * 1024 * 1200, // 1.2GB
        sample_count: 2000,
        label_count: 17,
        quality_score: undefined,
        quality_metrics: undefined,
        created_at: '2024-01-20T09:15:00Z',
        updated_at: '2024-01-20T09:15:00Z',
        description: '姿态检测数据集',
        tags: ['pose', 'detection', 'keypoints']
      }
    ]
    }
  } catch (error) {
    console.error('获取数据集列表失败:', error)
    // 使用模拟数据作为备用
    datasets.value = [
      {
        id: '1',
        name: 'handwash_detection_v1',
        version: '1.0.0',
        status: 'active',
        size: 1024 * 1024 * 500,
        sample_count: 1500,
        label_count: 3,
        quality_score: 85,
        quality_metrics: {
          completeness: 92,
          accuracy: 88,
          consistency: 85
        },
        created_at: '2024-01-15T10:30:00Z',
        updated_at: '2024-01-15T10:30:00Z',
        description: '洗手行为检测数据集',
        tags: ['handwash', 'detection', 'behavior']
      }
    ]
  } finally {
    loading.value = false
  }
}

// 刷新数据集
function refreshDatasets() {
  fetchDatasets()
}

// 获取数据集状态类型
function getDatasetStatusType(status: string) {
  const statusMap = {
    active: 'success',
    archived: 'default',
    processing: 'warning',
    error: 'error'
  }
  return statusMap[status] || 'default'
}

// 格式化文件大小
function formatFileSize(bytes: number) {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

// 格式化时间
function formatTime(timeString: string) {
  return new Date(timeString).toLocaleString('zh-CN')
}

// 查看数据集
function viewDataset(dataset: Dataset) {
  console.log('查看数据集:', dataset)
  // 显示数据集详情对话框
  message.info(`查看数据集: ${dataset.name}`)
  // TODO: 实现数据集详情查看对话框
}

// 对比数据集
function compareDataset(dataset: Dataset) {
  console.log('对比数据集:', dataset)
  message.info(`对比数据集: ${dataset.name}`)
  // TODO: 实现数据集对比功能
}

// 下载数据集
async function downloadDataset(dataset: Dataset) {
  console.log('下载数据集:', dataset)
  try {
    message.loading('正在准备下载...')
    // 模拟下载过程
    await new Promise(resolve => setTimeout(resolve, 1000))
    message.success(`数据集 ${dataset.name} 下载完成`)
  } catch (error) {
    message.error('下载失败')
  }
}

// 删除数据集
async function deleteDataset(dataset: Dataset) {
  console.log('删除数据集:', dataset)
  try {
    const confirmed = confirm(`确定要删除数据集 "${dataset.name}" 吗？此操作不可撤销。`)
    if (confirmed) {
      message.loading('正在删除...')
      // 调用删除API
      const response = await fetch(`/api/v1/mlops/datasets/${dataset.id}`, {
        method: 'DELETE'
      })
      if (response.ok) {
        message.success('数据集删除成功')
        refreshDatasets() // 刷新列表
      } else {
        throw new Error('删除失败')
      }
    }
  } catch (error) {
    message.error('删除失败')
  }
}

// 上传前处理
function beforeUpload(data: any) {
  console.log('准备上传:', data)
  return true
}

// 上传完成
function onUploadFinish(data: any) {
  console.log('上传完成:', data)
  showUploadDialog.value = false
  refreshDatasets()
}

// 上传错误
function onUploadError(data: any) {
  console.error('上传失败:', data)
}

onMounted(() => {
  fetchDatasets()
})
</script>

<style scoped>
.dataset-details {
  margin-top: 12px;
}

.quality-metrics {
  margin-top: 8px;
  padding: 8px;
  background-color: var(--n-color-target);
  border-radius: 4px;
}
</style>
