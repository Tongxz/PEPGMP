<template>
  <n-card title="智能检测状态" class="intelligent-detection-panel">
    <template #header-extra>
      <n-tag type="success" size="small">
        实时连接
      </n-tag>
    </template>

    <n-grid :cols="2" :x-gap="16" :y-gap="16">
      <!-- 处理统计 -->
      <n-gi>
        <n-statistic label="处理效率" value="85" suffix="%" />
      </n-gi>
      <n-gi>
        <n-statistic label="平均FPS" value="15.2" :precision="2" />
      </n-gi>
      <n-gi>
        <n-statistic label="已处理帧" value="1250" />
      </n-gi>
      <n-gi>
        <n-statistic label="已跳过帧" value="450" />
      </n-gi>
    </n-grid>

    <!-- 场景分布 -->
    <n-divider />
    <div class="scene-distribution">
      <h4>场景分布</h4>
      <n-space>
        <n-tag type="info">静态场景: 8</n-tag>
        <n-tag type="info">动态场景: 2</n-tag>
        <n-tag type="info">关键场景: 1</n-tag>
      </n-space>
    </div>

    <!-- 性能监控 -->
    <n-divider />
    <div class="performance-monitoring">
      <h4>性能监控</h4>
      <n-grid :cols="3" :x-gap="12" :y-gap="12">
        <n-gi>
          <n-progress
            type="line"
            :percentage="65"
            color="#18a058"
            :show-indicator="false"
          />
          <div class="progress-label">CPU: 65%</div>
        </n-gi>
        <n-gi>
          <n-progress
            type="line"
            :percentage="45"
            color="#18a058"
            :show-indicator="false"
          />
          <div class="progress-label">内存: 45%</div>
        </n-gi>
        <n-gi>
          <n-progress
            type="line"
            :percentage="30"
            color="#18a058"
            :show-indicator="false"
          />
          <div class="progress-label">GPU: 30%</div>
        </n-gi>
      </n-grid>
    </div>
  </n-card>
</template>

<script setup lang="ts">
import { NCard, NTag, NGrid, NGi, NStatistic, NDivider, NSpace, NProgress } from 'naive-ui'
</script>

<style scoped>
.intelligent-detection-panel {
  margin-bottom: 16px;
}

.scene-distribution h4,
.performance-monitoring h4 {
  margin: 0 0 8px 0;
  font-size: 14px;
  font-weight: 600;
}

.progress-label {
  font-size: 12px;
  color: #666;
  margin-top: 4px;
}
</style>
