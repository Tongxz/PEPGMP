<template>
  <section>
    <h2>首页</h2>
    <p>欢迎来到 PYT 前端迁移版。</p>

    <div style="margin-top: 16px; display: flex; gap: 8px; align-items: center; flex-wrap: wrap">
      <n-button type="primary" @click="onCheckHealth" :loading="loadingHealth">
        健康检查 /health
      </n-button>
      <n-tag v-if="healthStatus" type="success" size="small">{{ healthStatus }}</n-tag>
      <n-tag v-if="healthError" type="error" size="small">{{ healthError }}</n-tag>
    </div>

    <div style="margin-top: 8px; display: flex; gap: 8px; align-items: center; flex-wrap: wrap">
      <n-button @click="onGetSystemInfo" :loading="loadingSysInfo">
        获取系统信息 /system/info
      </n-button>
      <n-tag v-if="sysInfoOk" type="success" size="small">OK</n-tag>
      <n-tag v-if="sysInfoError" type="error" size="small">{{ sysInfoError }}</n-tag>
    </div>

    <n-card v-if="sysInfo" title="系统信息" size="small" style="margin-top: 8px">
      <pre style="max-width: 100%; overflow: auto; margin: 0">{{ formattedSysInfo }}</pre>
    </n-card>
  </section>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useMessage, NButton, NTag, NCard } from 'naive-ui'
import { getHealth, getSystemInfo } from '@/api/system'

const message = useMessage()

const loadingHealth = ref(false)
const healthStatus = ref('')
const healthError = ref('')

const loadingSysInfo = ref(false)
const sysInfo = ref<unknown>(null)
const sysInfoOk = ref(false)
const sysInfoError = ref('')

const formattedSysInfo = computed(() => {
  try {
    return JSON.stringify(sysInfo.value, null, 2)
  } catch {
    return String(sysInfo.value)
  }
})

type WithMessage = { message?: string }
type WithResponse = { response?: { data?: { detail?: string } } }
function getErrMsg(e: unknown): string {
  if (typeof e === 'string') return e
  if (e && typeof e === 'object') {
    const detail = (e as WithResponse).response?.data?.detail
    const msg = (e as WithMessage).message
    return (detail as string | undefined) || (msg as string | undefined) || '请求失败'
  }
  return '请求失败'
}

async function onCheckHealth() {
  loadingHealth.value = true
  healthStatus.value = ''
  healthError.value = ''
  try {
    const data = await getHealth()
    healthStatus.value = typeof data === 'string' ? data : 'OK'
    message.success('健康检查成功')
  } catch (e: unknown) {
    const err = getErrMsg(e)
    healthError.value = err
    message.error(`健康检查失败：${err}`)
  } finally {
    loadingHealth.value = false
  }
}

async function onGetSystemInfo() {
  loadingSysInfo.value = true
  sysInfo.value = null
  sysInfoOk.value = false
  sysInfoError.value = ''
  try {
    const data = await getSystemInfo()
    sysInfo.value = data
    sysInfoOk.value = true
    message.success('系统信息已获取')
  } catch (e: unknown) {
    const err = getErrMsg(e)
    sysInfoError.value = err
    message.error(`获取系统信息失败：${err}`)
  } finally {
    loadingSysInfo.value = false
  }
}
</script>
