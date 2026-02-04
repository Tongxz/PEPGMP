<template>
  <div class="region-form">
    <!-- 绘制区域按钮 -->
    <div class="draw-region-section">
      <n-button
        type="primary"
        size="large"
        @click="$emit('startDrawing')"
        :disabled="isDrawing || (!selectedCamera && !backgroundImage)"
        block
      >
        <template #icon>
          <n-icon><AddOutline /></n-icon>
        </template>
        {{ isDrawing ? '正在绘制...' : '绘制新区域' }}
      </n-button>

      <n-alert v-if="isDrawing" type="info" size="small" style="margin-top: 8px;">
        <template #icon>
          <n-icon><BrushOutline /></n-icon>
        </template>
        在右侧画布上点击绘制区域，双击完成绘制
      </n-alert>

      <n-alert
        v-if="!selectedCamera && !backgroundImage"
        type="warning"
        size="small"
        style="margin-top: 8px;"
      >
        <template #icon>
          <n-icon><WarningOutline /></n-icon>
        </template>
        请先在页面顶部选择摄像头或上传图片
      </n-alert>
    </div>

    <!-- 区域配置表单 -->
    <div class="region-form-section" v-if="currentRegion.id || isDrawing">
      <n-divider>
        {{ currentRegion.id ? '编辑区域' : '新区域配置' }}
      </n-divider>

      <n-form
        ref="formRef"
        :model="currentRegion"
        :rules="formRules"
        label-placement="top"
        require-mark-placement="right-hanging"
        size="medium"
        class="region-form"
      >
        <!-- 基本信息 -->
        <n-form-item label="区域名称" path="name">
          <n-input
            v-model:value="currentRegion.name"
            placeholder="请输入区域名称"
            clearable
          />
        </n-form-item>

        <n-form-item label="区域类型" path="type">
          <n-select
            v-model:value="currentRegion.type"
            :options="regionTypeOptions"
            placeholder="选择区域类型"
          />
        </n-form-item>

        <n-form-item label="区域描述" path="description">
          <n-input
            v-model:value="currentRegion.description"
            type="textarea"
            placeholder="请输入区域描述（可选）"
            :autosize="{ minRows: 2, maxRows: 4 }"
          />
        </n-form-item>

        <!-- 检测参数 -->
        <n-divider title-placement="left">
          <n-text depth="2">检测参数</n-text>
        </n-divider>

        <n-form-item label="启用检测" path="enabled">
          <n-switch
            v-model:value="currentRegion.enabled"
            size="medium"
          />
        </n-form-item>

        <n-form-item label="检测灵敏度" path="sensitivity">
          <n-slider
            v-model:value="currentRegion.sensitivity"
            :step="0.1"
            :min="0.1"
            :max="1.0"
            :tooltip="{ formatter: (value) => `${(value * 100).toFixed(0)}%` }"
          />
        </n-form-item>

        <n-form-item label="最短停留时间（秒）" path="minDuration">
          <n-input-number
            v-model:value="currentRegion.minDuration"
            :min="1"
            :max="300"
            placeholder="5"
            style="width: 100%"
          />
        </n-form-item>

        <!-- 告警设置 -->
        <n-divider title-placement="left">
          <n-text depth="2">告警设置</n-text>
        </n-divider>

        <n-form-item label="启用告警" path="alertEnabled">
          <n-switch
            v-model:value="currentRegion.alertEnabled"
            size="medium"
          />
        </n-form-item>

        <n-form-item v-if="currentRegion.alertEnabled" label="告警级别" path="alertLevel">
          <n-select
            v-model:value="currentRegion.alertLevel"
            :options="alertLevelOptions"
            placeholder="选择告警级别"
          />
        </n-form-item>

        <!-- 操作按钮 -->
        <n-space justify="end" style="margin-top: 16px;">
          <n-button @click="$emit('cancel')">
            取消
          </n-button>
          <n-button
            type="primary"
            @click="handleSubmit"
            :loading="saving"
          >
            {{ currentRegion.id ? '更新' : '保存' }}
          </n-button>
        </n-space>
      </n-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { FormInst } from 'naive-ui'
import { h } from 'vue'
import { useErrorHandler, useLoading } from '@/composables'

// Icons
import {
  AddOutline,
  BrushOutline,
  WarningOutline,
} from '@vicons/ionicons5'

// Props
interface Props {
  currentRegion: any
  isDrawing: boolean
  selectedCamera?: string
  backgroundImage?: any
  saving: boolean
}

const props = defineProps<Props>()

// Emits
const emit = defineEmits<{
  startDrawing: []
  submit: [region: any]
  cancel: []
}>()

// Composables
const { handleError } = useErrorHandler()
const { withLoading } = useLoading()

// Refs
const formRef = ref<FormInst | null>(null)

// Form rules
const formRules = {
  name: [
    { required: true, message: '请输入区域名称', trigger: 'blur' }
  ],
  type: [
    { required: true, message: '请选择区域类型', trigger: 'change' }
  ]
}

// Region type options
const regionTypeOptions = [
  { label: '入口区域', value: 'entrance' },
  { label: '洗手区域', value: 'handwash' },
  { label: '消毒区域', value: 'sanitize' },
  { label: '工作区域', value: 'work_area' },
  { label: '限制区域', value: 'restricted' },
  { label: '监控区域', value: 'monitoring' },
  { label: '自定义区域', value: 'custom' }
]

// Alert level options
const alertLevelOptions = [
  { label: '低', value: 'low' },
  { label: '中', value: 'medium' },
  { label: '高', value: 'high' },
  { label: '紧急', value: 'critical' }
]

// Methods
const handleSubmit = async () => {
  await withLoading(async () => {
    try {
      await formRef.value?.validate()
      emit('submit', props.currentRegion)
    } catch (error) {
      if (error !== 'validation') { // 表单验证错误不需要额外处理
        handleError(error, {
          customMessage: '保存区域失败',
          showMessage: true
        })
      }
    }
  }, 'region-submit', {
    message: props.currentRegion.id ? '更新区域中...' : '保存区域中...'
  })
}
</script>

<style scoped>
.region-form {
  padding: 16px 12px;
}

.draw-region-section {
  margin-bottom: 16px;
}

.region-form-section {
  margin-top: 16px;
}

.region-form {
  /* Form styles */
}
</style>
