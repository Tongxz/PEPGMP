<template>
  <div class="page-header">
    <div class="page-header-content">
      <!-- 左侧标题区域 -->
      <div class="page-header-left">
        <div class="page-title">
          <span v-if="icon" class="page-icon">
            {{ icon }}
          </span>
          <h1>{{ title }}</h1>
        </div>
        <p v-if="description" class="page-description">{{ description }}</p>
      </div>

      <!-- 右侧操作区域 -->
      <div v-if="$slots.extra" class="page-header-right">
        <slot name="extra" />
      </div>
    </div>

    <!-- 标签页区域 -->
    <div v-if="$slots.tabs" class="page-header-tabs">
      <slot name="tabs" />
    </div>
  </div>
</template>

<script setup lang="ts">
interface Props {
  title: string
  description?: string
  icon?: string
}

defineProps<Props>()
</script>

<style scoped>
.page-header {
  margin-bottom: 24px;
}

.page-header-content {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
}

.page-header-left {
  flex: 1;
}

.page-title {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.page-title h1 {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
  color: var(--n-text-color);
}

.page-icon {
  font-size: 24px;
  line-height: 1;
  color: var(--n-primary-color);
}

.page-description {
  margin: 0;
  color: var(--n-text-color-disabled);
  font-size: 14px;
  line-height: 1.5;
}

.page-header-right {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-left: 24px;
}

.page-header-tabs {
  border-bottom: 1px solid var(--n-border-color);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .page-header-content {
    flex-direction: column;
    align-items: stretch;
    gap: 16px;
  }

  .page-header-right {
    margin-left: 0;
    justify-content: flex-end;
  }

  .page-title h1 {
    font-size: 20px;
  }
}
</style>
