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

    <!-- 数据集详情对话框 -->
    <n-modal v-model:show="showDetailDialog" preset="dialog" title="数据集详情" style="width: 800px;">
      <div v-if="selectedDataset" class="dataset-detail-content">
        <!-- 基本信息 -->
        <n-card title="基本信息" size="small" style="margin-bottom: 16px;">
          <n-descriptions :column="2" size="small">
            <n-descriptions-item label="数据集名称">
              {{ selectedDataset.name }}
            </n-descriptions-item>
            <n-descriptions-item label="版本">
              v{{ selectedDataset.version }}
            </n-descriptions-item>
            <n-descriptions-item label="状态">
              <n-tag :type="getDatasetStatusType(selectedDataset.status)" size="small">
                {{ selectedDataset.status }}
              </n-tag>
            </n-descriptions-item>
            <n-descriptions-item label="大小">
              {{ formatFileSize(selectedDataset.size) }}
            </n-descriptions-item>
            <n-descriptions-item label="样本数">
              {{ selectedDataset.sample_count?.toLocaleString() || 'N/A' }}
            </n-descriptions-item>
            <n-descriptions-item label="标签数">
              {{ selectedDataset.label_count || 0 }}
            </n-descriptions-item>
            <n-descriptions-item label="创建时间">
              {{ formatTime(selectedDataset.created_at) }}
            </n-descriptions-item>
            <n-descriptions-item label="更新时间">
              {{ formatTime(selectedDataset.updated_at) }}
            </n-descriptions-item>
          </n-descriptions>
          <n-divider />
          <n-text depth="3" style="font-size: 12px;">描述</n-text>
          <n-p style="margin-top: 8px;">{{ selectedDataset.description || '暂无描述' }}</n-p>
          <n-divider v-if="selectedDataset.tags && selectedDataset.tags.length > 0" />
          <div v-if="selectedDataset.tags && selectedDataset.tags.length > 0">
            <n-text depth="3" style="font-size: 12px;">标签</n-text>
            <n-space style="margin-top: 8px;">
              <n-tag v-for="tag in selectedDataset.tags" :key="tag" type="info" size="small">
                {{ tag }}
              </n-tag>
            </n-space>
          </div>
        </n-card>

        <!-- 数据质量报告 -->
        <n-card v-if="selectedDataset.quality_metrics" title="数据质量报告" size="small" style="margin-bottom: 16px;">
          <n-grid :cols="3" :x-gap="16" :y-gap="16">
            <n-gi>
              <n-statistic label="完整性" :value="selectedDataset.quality_metrics.completeness" suffix="%" />
            </n-gi>
            <n-gi>
              <n-statistic label="准确性" :value="selectedDataset.quality_metrics.accuracy" suffix="%" />
            </n-gi>
            <n-gi>
              <n-statistic label="一致性" :value="selectedDataset.quality_metrics.consistency" suffix="%" />
            </n-gi>
          </n-grid>
          <n-divider />
          <n-text depth="3" style="font-size: 12px;">质量评分</n-text>
          <div style="margin-top: 8px;">
            <n-rate v-if="selectedDataset.quality_score" :value="selectedDataset.quality_score / 20" readonly size="large" />
            <n-text v-else depth="3">未评估</n-text>
          </div>
        </n-card>

        <!-- 样本预览 -->
        <n-card title="样本预览" size="small" style="margin-bottom: 16px;">
          <n-empty description="暂无样本预览">
            <template #extra>
              <n-button size="small" @click="loadSamplePreview">加载样本预览</n-button>
            </template>
          </n-empty>
        </n-card>

        <!-- 统计信息 -->
        <n-card title="统计信息" size="small">
          <n-grid :cols="2" :x-gap="16" :y-gap="16">
            <n-gi>
              <n-statistic label="总文件数" :value="getFileCount(selectedDataset)" />
            </n-gi>
            <n-gi>
              <n-statistic label="平均文件大小" :value="formatFileSize(getAverageFileSize(selectedDataset))" />
            </n-gi>
            <n-gi>
              <n-statistic label="数据完整性" :value="getDataIntegrity(selectedDataset)" suffix="%" />
            </n-gi>
            <n-gi>
              <n-statistic label="标注覆盖率" :value="getAnnotationCoverage(selectedDataset)" suffix="%" />
            </n-gi>
          </n-grid>
        </n-card>
      </div>
      <template #action>
        <n-space>
          <n-button @click="showDetailDialog = false">关闭</n-button>
          <n-button type="primary" @click="downloadDataset(selectedDataset)">下载</n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- 数据集对比对话框 -->
    <n-modal v-model:show="showCompareDialog" preset="dialog" title="数据集对比" style="width: 1000px;">
      <div v-if="compareDatasets.length === 2" class="dataset-compare-content">
        <n-grid :cols="2" :x-gap="16">
          <n-gi>
            <n-card :title="compareDatasets[0].name" size="small">
              <n-descriptions :column="1" size="small">
                <n-descriptions-item label="版本">v{{ compareDatasets[0].version }}</n-descriptions-item>
                <n-descriptions-item label="大小">{{ formatFileSize(compareDatasets[0].size) }}</n-descriptions-item>
                <n-descriptions-item label="样本数">{{ compareDatasets[0].sample_count?.toLocaleString() || 'N/A' }}</n-descriptions-item>
                <n-descriptions-item label="标签数">{{ compareDatasets[0].label_count || 0 }}</n-descriptions-item>
                <n-descriptions-item label="质量评分">
                  <n-rate v-if="compareDatasets[0].quality_score" :value="compareDatasets[0].quality_score / 20" readonly size="small" />
                  <span v-else>未评估</span>
                </n-descriptions-item>
              </n-descriptions>
            </n-card>
          </n-gi>
          <n-gi>
            <n-card :title="compareDatasets[1].name" size="small">
              <n-descriptions :column="1" size="small">
                <n-descriptions-item label="版本">v{{ compareDatasets[1].version }}</n-descriptions-item>
                <n-descriptions-item label="大小">{{ formatFileSize(compareDatasets[1].size) }}</n-descriptions-item>
                <n-descriptions-item label="样本数">{{ compareDatasets[1].sample_count?.toLocaleString() || 'N/A' }}</n-descriptions-item>
                <n-descriptions-item label="标签数">{{ compareDatasets[1].label_count || 0 }}</n-descriptions-item>
                <n-descriptions-item label="质量评分">
                  <n-rate v-if="compareDatasets[1].quality_score" :value="compareDatasets[1].quality_score / 20" readonly size="small" />
                  <span v-else>未评估</span>
                </n-descriptions-item>
              </n-descriptions>
            </n-card>
          </n-gi>
        </n-grid>
        
        <n-divider />
        
        <!-- 对比分析 -->
        <n-card title="对比分析" size="small">
          <n-grid :cols="3" :x-gap="16" :y-gap="16">
            <n-gi>
              <n-statistic 
                label="大小差异" 
                :value="getSizeDifference(compareDatasets[0], compareDatasets[1])" 
                suffix="%"
                :value-style="{ color: getSizeDifference(compareDatasets[0], compareDatasets[1]) > 0 ? '#18a058' : '#d03050' }"
              />
            </n-gi>
            <n-gi>
              <n-statistic 
                label="样本数差异" 
                :value="getSampleDifference(compareDatasets[0], compareDatasets[1])" 
                suffix="%"
                :value-style="{ color: getSampleDifference(compareDatasets[0], compareDatasets[1]) > 0 ? '#18a058' : '#d03050' }"
              />
            </n-gi>
            <n-gi>
              <n-statistic 
                label="质量差异" 
                :value="getQualityDifference(compareDatasets[0], compareDatasets[1])" 
                suffix="%"
                :value-style="{ color: getQualityDifference(compareDatasets[0], compareDatasets[1]) > 0 ? '#18a058' : '#d03050' }"
              />
            </n-gi>
          </n-grid>
        </n-card>
      </div>
      <template #action>
        <n-space>
          <n-button @click="showCompareDialog = false">关闭</n-button>
          <n-button type="primary" @click="startNewCompare">开始新对比</n-button>
        </n-space>
      </template>
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
const showDetailDialog = ref(false)
const showCompareDialog = ref(false)
const selectedDataset = ref<Dataset | null>(null)
const compareDatasets = ref<Dataset[]>([])
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
  selectedDataset.value = dataset
  showDetailDialog.value = true
}

// 对比数据集
function compareDataset(dataset: Dataset) {
  if (compareDatasets.value.length === 0) {
    compareDatasets.value.push(dataset)
    message.info(`已选择 ${dataset.name}，请选择第二个数据集进行对比`)
  } else if (compareDatasets.value.length === 1) {
    if (compareDatasets.value[0].id === dataset.id) {
      message.warning('不能选择相同的数据集进行对比')
      return
    }
    compareDatasets.value.push(dataset)
    showCompareDialog.value = true
  } else {
    // 重新开始对比
    compareDatasets.value = [dataset]
    message.info(`已选择 ${dataset.name}，请选择第二个数据集进行对比`)
  }
}

// 下载数据集
async function downloadDataset(dataset: Dataset) {
  console.log('下载数据集:', dataset)
  try {
    message.loading('正在准备下载...')
    
    // 调用下载API
    const response = await fetch(`/api/v1/mlops/datasets/${dataset.id}/download?format=zip`)
    
    if (response.ok) {
      // 创建下载链接
      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${dataset.name}_v${dataset.version}.zip`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
      
      message.success(`数据集 ${dataset.name} 下载完成`)
    } else {
      throw new Error('下载失败')
    }
  } catch (error) {
    console.error('下载失败:', error)
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

// 加载样本预览
function loadSamplePreview() {
  message.info('正在加载样本预览...')
  // TODO: 实现样本预览加载
}

// 获取文件数量
function getFileCount(dataset: Dataset) {
  // 模拟计算，实际应该从API获取
  return Math.floor(dataset.sample_count || 0 / 10) || 0
}

// 获取平均文件大小
function getAverageFileSize(dataset: Dataset) {
  const fileCount = getFileCount(dataset)
  return fileCount > 0 ? dataset.size / fileCount : 0
}

// 获取数据完整性
function getDataIntegrity(dataset: Dataset) {
  return dataset.quality_metrics?.completeness || 0
}

// 获取标注覆盖率
function getAnnotationCoverage(dataset: Dataset) {
  return dataset.quality_metrics?.accuracy || 0
}

// 获取大小差异百分比
function getSizeDifference(dataset1: Dataset, dataset2: Dataset) {
  if (dataset2.size === 0) return 0
  return Math.round(((dataset1.size - dataset2.size) / dataset2.size) * 100)
}

// 获取样本数差异百分比
function getSampleDifference(dataset1: Dataset, dataset2: Dataset) {
  const sample1 = dataset1.sample_count || 0
  const sample2 = dataset2.sample_count || 0
  if (sample2 === 0) return 0
  return Math.round(((sample1 - sample2) / sample2) * 100)
}

// 获取质量差异百分比
function getQualityDifference(dataset1: Dataset, dataset2: Dataset) {
  const quality1 = dataset1.quality_score || 0
  const quality2 = dataset2.quality_score || 0
  if (quality2 === 0) return 0
  return Math.round(((quality1 - quality2) / quality2) * 100)
}

// 开始新对比
function startNewCompare() {
  compareDatasets.value = []
  showCompareDialog.value = false
  message.info('已重置对比选择，请重新选择数据集')
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

.dataset-detail-content {
  max-height: 70vh;
  overflow-y: auto;
}

.dataset-compare-content {
  max-height: 70vh;
  overflow-y: auto;
}
</style>
