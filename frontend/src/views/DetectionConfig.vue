<template>
  <div class="detection-config">
    <n-card title="检测配置管理" class="config-card">
      <template #header-extra>
        <n-space>
          <n-button @click="loadConfig" :loading="loading">刷新</n-button>
          <n-button type="primary" @click="saveConfig" :loading="saving">保存配置</n-button>
        </n-space>
      </template>

      <n-space vertical :size="24">
        <!-- 人体检测配置 -->
        <n-card title="人体检测配置" size="small">
          <n-form :model="formData.human_detection" label-placement="left" label-width="180">
            <n-grid :cols="2" :x-gap="24">
              <n-grid-item>
                <n-form-item label="置信度阈值">
                  <n-slider
                    v-model:value="formData.human_detection.confidence_threshold"
                    :min="0.1"
                    :max="0.9"
                    :step="0.05"
                    :marks="confidenceMarks"
                    :tooltip="false"
                  />
                  <n-input-number
                    v-model:value="formData.human_detection.confidence_threshold"
                    :min="0.1"
                    :max="0.9"
                    :step="0.05"
                    :precision="2"
                    style="width: 100px; margin-left: 12px"
                  />
                </n-form-item>
              </n-grid-item>

              <n-grid-item>
                <n-form-item label="IoU阈值">
                  <n-slider
                    v-model:value="formData.human_detection.iou_threshold"
                    :min="0.1"
                    :max="1.0"
                    :step="0.05"
                    :tooltip="false"
                  />
                  <n-input-number
                    v-model:value="formData.human_detection.iou_threshold"
                    :min="0.1"
                    :max="1.0"
                    :step="0.05"
                    :precision="2"
                    style="width: 100px; margin-left: 12px"
                  />
                </n-form-item>
              </n-grid-item>

              <n-grid-item>
                <n-form-item label="最小检测框面积">
                  <n-input-number
                    v-model:value="formData.human_detection.min_box_area"
                    :min="100"
                    :max="10000"
                    :step="100"
                    style="width: 150px"
                  />
                  <span style="margin-left: 8px; color: #666">像素²</span>
                </n-form-item>
              </n-grid-item>

              <n-grid-item>
                <n-form-item label="最大检测数量">
                  <n-input-number
                    v-model:value="formData.human_detection.max_detections"
                    :min="1"
                    :max="50"
                    :step="1"
                    style="width: 150px"
                  />
                </n-form-item>
              </n-grid-item>

              <n-grid-item>
                <n-form-item label="最小宽度">
                  <n-input-number
                    v-model:value="formData.human_detection.min_width"
                    :min="20"
                    :max="200"
                    :step="5"
                    style="width: 150px"
                  />
                  <span style="margin-left: 8px; color: #666">像素</span>
                </n-form-item>
              </n-grid-item>

              <n-grid-item>
                <n-form-item label="最小高度">
                  <n-input-number
                    v-model:value="formData.human_detection.min_height"
                    :min="30"
                    :max="300"
                    :step="5"
                    style="width: 150px"
                  />
                  <span style="margin-left: 8px; color: #666">像素</span>
                </n-form-item>
              </n-grid-item>
            </n-grid>
          </n-form>
        </n-card>

        <!-- 发网检测配置 -->
        <n-card title="发网检测配置" size="small">
          <n-form :model="formData.hairnet_detection" label-placement="left" label-width="180">
            <n-grid :cols="2" :x-gap="24">
              <n-grid-item>
                <n-form-item label="置信度阈值">
                  <n-slider
                    v-model:value="formData.hairnet_detection.confidence_threshold"
                    :min="0.3"
                    :max="0.9"
                    :step="0.05"
                    :marks="confidenceMarks"
                    :tooltip="false"
                  />
                  <n-input-number
                    v-model:value="formData.hairnet_detection.confidence_threshold"
                    :min="0.3"
                    :max="0.9"
                    :step="0.05"
                    :precision="2"
                    style="width: 100px; margin-left: 12px"
                  />
                  <n-text depth="3" style="margin-left: 8px">
                    (建议: 0.3-0.5，如果检测不到发网可降低)
                  </n-text>
                </n-form-item>
              </n-grid-item>

              <n-grid-item>
                <n-form-item label="总分数阈值">
                  <n-slider
                    v-model:value="formData.hairnet_detection.total_score_threshold"
                    :min="0.5"
                    :max="1.0"
                    :step="0.05"
                    :tooltip="false"
                  />
                  <n-input-number
                    v-model:value="formData.hairnet_detection.total_score_threshold"
                    :min="0.5"
                    :max="1.0"
                    :step="0.05"
                    :precision="2"
                    style="width: 100px; margin-left: 12px"
                  />
                </n-form-item>
              </n-grid-item>
            </n-grid>
          </n-form>
        </n-card>

        <!-- 行为识别配置 -->
        <n-card title="行为识别配置" size="small">
          <n-form :model="formData.behavior_recognition" label-placement="left" label-width="200">
            <n-grid :cols="2" :x-gap="24">
              <n-grid-item>
                <n-form-item label="置信度阈值">
                  <n-slider
                    v-model:value="formData.behavior_recognition.confidence_threshold"
                    :min="0.3"
                    :max="0.9"
                    :step="0.05"
                    :marks="confidenceMarks"
                    :tooltip="false"
                  />
                  <n-input-number
                    v-model:value="formData.behavior_recognition.confidence_threshold"
                    :min="0.3"
                    :max="0.9"
                    :step="0.05"
                    :precision="2"
                    style="width: 100px; margin-left: 12px"
                  />
                </n-form-item>
              </n-grid-item>

              <n-grid-item>
                <n-form-item label="洗手稳定性帧数">
                  <n-input-number
                    v-model:value="formData.behavior_recognition.handwashing_stability_frames"
                    :min="1"
                    :max="10"
                    :step="1"
                    style="width: 150px"
                  />
                  <span style="margin-left: 8px; color: #666">
                    (需要连续N帧检测到洗手才确认)
                  </span>
                </n-form-item>
              </n-grid-item>

              <n-grid-item>
                <n-form-item label="消毒稳定性帧数">
                  <n-input-number
                    v-model:value="formData.behavior_recognition.sanitizing_stability_frames"
                    :min="1"
                    :max="10"
                    :step="1"
                    style="width: 150px"
                  />
                  <span style="margin-left: 8px; color: #666">
                    (需要连续N帧检测到消毒才确认)
                  </span>
                </n-form-item>
              </n-grid-item>
            </n-grid>
          </n-form>
        </n-card>

        <!-- 提示信息 -->
        <n-alert type="info" title="配置说明">
          <ul style="margin: 0; padding-left: 20px">
            <li>配置保存后会写入到 <code>config/unified_params.yaml</code> 文件</li>
            <li>配置修改后需要<strong>重启检测服务</strong>才能生效</li>
            <li>建议先在小范围内测试，确认效果后再应用到生产环境</li>
            <li>降低置信度阈值可以提高检测敏感度，但可能增加误检</li>
            <li>提高稳定性帧数可以减少误报，但可能延迟检测响应</li>
          </ul>
        </n-alert>
      </n-space>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { NCard, NButton, NSpace, NForm, NFormItem, NGrid, NGridItem, NInputNumber, NSlider, NText, NAlert, useMessage } from 'naive-ui'
import { detectionConfigApi, type DetectionConfig, type DetectionConfigRequest } from '@/api/detectionConfig'

const message = useMessage()
const loading = ref(false)
const saving = ref(false)

const formData = ref<DetectionConfigRequest>({
  human_detection: {
    confidence_threshold: 0.5,
    iou_threshold: 0.6,
    min_box_area: 1500,
    min_width: 50,
    min_height: 80,
    max_detections: 15,
  },
  hairnet_detection: {
    confidence_threshold: 0.65,
    total_score_threshold: 0.85,
  },
  behavior_recognition: {
    confidence_threshold: 0.65,
    handwashing_stability_frames: 3,
    sanitizing_stability_frames: 3,
  },
})

const confidenceMarks = computed(() => ({
  0.3: '0.3',
  0.5: '0.5',
  0.7: '0.7',
  0.9: '0.9',
}))

const loadConfig = async () => {
  loading.value = true
  try {
    const config = await detectionConfigApi.getConfig()
    formData.value = {
      human_detection: config.human_detection,
      hairnet_detection: config.hairnet_detection,
      behavior_recognition: config.behavior_recognition,
    }
    message.success('配置加载成功')
  } catch (error: any) {
    message.error(`加载配置失败: ${error.message || '未知错误'}`)
  } finally {
    loading.value = false
  }
}

const saveConfig = async () => {
  saving.value = true
  try {
    const response = await detectionConfigApi.updateConfig(formData.value, false)
    message.success(response.message || '配置保存成功')
    if (response.note) {
      message.warning(response.note)
    }
  } catch (error: any) {
    message.error(`保存配置失败: ${error.message || '未知错误'}`)
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  loadConfig()
})
</script>

<style scoped>
.detection-config {
  padding: 20px;
}

.config-card {
  max-width: 1200px;
  margin: 0 auto;
}

code {
  background: #f5f5f5;
  padding: 2px 6px;
  border-radius: 3px;
  font-family: 'Courier New', monospace;
}
</style>
