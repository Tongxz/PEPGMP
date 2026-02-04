import { createDiscreteApi } from 'naive-ui'
import { readonly, ref } from 'vue'

// 导入必要的工具
import { downloadBlob, exportApi, type ExportParams } from '@/api/export'
import { useErrorHandler } from './useErrorHandler'
import { useLoading } from './useLoading'

// 创建离散的 Naive UI API 实例
const { message, dialog } = createDiscreteApi(['message', 'dialog'])

// 导出类型定义
export interface ExportOptions {
  filename?: string
  format?: 'csv' | 'excel'
  confirmBeforeExport?: boolean
  confirmMessage?: string
  successMessage?: string
  onProgress?: (progress: number) => void
  onSuccess?: (blob: Blob) => void
  onError?: (error: unknown) => void
}

export interface ExportTask {
  id: string
  type: 'detection-records' | 'violations' | 'statistics' | 'regions' | 'config'
  params: ExportParams
  options: ExportOptions
  status: 'pending' | 'running' | 'completed' | 'failed'
  progress: number
  startTime: number
  endTime?: number
  error?: string
}

// 导出状态管理
const exportTasks = ref<Map<string, ExportTask>>(new Map())

export function useExport() {
  const { handleError } = useErrorHandler()
  const { withLoading } = useLoading()

  /**
   * 生成默认文件名
   */
  const generateFilename = (type: string, params: ExportParams, format: string = 'csv'): string => {
    const timestamp = new Date().toISOString().slice(0, 19).replace(/[:-]/g, '')
    const cameraSuffix = params.camera_id ? `_${params.camera_id}` : ''
    const timeRange = params.start_time && params.end_time
      ? `_${params.start_time.slice(0, 10)}_${params.end_time.slice(0, 10)}`
      : ''

    return `${type}${cameraSuffix}${timeRange}_${timestamp}.${format}`
  }

  /**
   * 创建导出任务
   */
  const createExportTask = (
    type: ExportTask['type'],
    params: ExportParams,
    options: ExportOptions = {}
  ): string => {
    const taskId = `${type}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`

    const task: ExportTask = {
      id: taskId,
      type,
      params,
      options: {
        filename: options.filename || generateFilename(type, params, options.format),
        format: options.format || 'csv',
        confirmBeforeExport: options.confirmBeforeExport ?? true,
        confirmMessage: options.confirmMessage || `确定要导出${getTypeLabel(type)}吗？`,
        successMessage: options.successMessage || '导出成功',
        ...options
      },
      status: 'pending',
      progress: 0,
      startTime: Date.now()
    }

    exportTasks.value.set(taskId, task)
    return taskId
  }

  /**
   * 执行导出
   */
  const executeExport = async (taskId: string): Promise<boolean> => {
    const task = exportTasks.value.get(taskId)
    if (!task) {
      handleError(new Error('导出任务不存在'), { showMessage: true })
      return false
    }

    // 确认导出
    if (task.options.confirmBeforeExport) {
      try {
        await dialog.warning({
          title: '确认导出',
          content: task.options.confirmMessage,
          positiveText: '确认导出',
          negativeText: '取消'
        })
      } catch {
        // 用户取消导出
        return false
      }
    }

    // 更新任务状态
    task.status = 'running'
    task.progress = 0

    try {
      // 执行导出
      const blob = await withLoading(
        async () => {
          task.progress = 50
          task.options.onProgress?.(50)

          switch (task.type) {
            case 'detection-records':
              return await exportApi.exportDetectionRecords(task.params)
            case 'violations':
              return await exportApi.exportViolations(task.params)
            case 'statistics':
              return await exportApi.exportStatistics(task.params)
            default:
              throw new Error(`不支持的导出类型: ${task.type}`)
          }
        },
        `export-${taskId}`,
        {
          message: `正在导出${getTypeLabel(task.type)}...`,
          timeout: 300000, // 5分钟超时
          onTimeout: () => {
            handleError(new Error('导出超时，请稍后重试'), { showMessage: true })
          }
        }
      )

      // 下载文件
      task.progress = 100
      task.options.onProgress?.(100)

      downloadBlob(blob, task.options.filename!)
      task.options.onSuccess?.(blob)

      // 更新任务状态
      task.status = 'completed'
      task.endTime = Date.now()

      message.success(task.options.successMessage)
      return true

    } catch (error) {
      task.status = 'failed'
      task.endTime = Date.now()
      task.error = error instanceof Error ? error.message : String(error)

      task.options.onError?.(error)
      handleError(error, {
        customMessage: `${getTypeLabel(task.type)}导出失败`,
        showMessage: true
      })
      return false
    }
  }

  /**
   * 快速导出方法
   */
  const quickExport = async (
    type: ExportTask['type'],
    params: ExportParams,
    options: ExportOptions = {}
  ): Promise<boolean> => {
    const taskId = createExportTask(type, params, options)
    return await executeExport(taskId)
  }

  /**
   * 导出检测记录
   */
  const exportDetectionRecords = async (
    params: ExportParams,
    options: ExportOptions = {}
  ): Promise<boolean> => {
    return await quickExport('detection-records', params, {
      ...options,
      confirmMessage: '确定要导出检测记录吗？这可能需要一些时间。',
      successMessage: '检测记录导出成功'
    })
  }

  /**
   * 导出违规记录
   */
  const exportViolations = async (
    params: ExportParams,
    options: ExportOptions = {}
  ): Promise<boolean> => {
    return await quickExport('violations', params, {
      ...options,
      confirmMessage: '确定要导出违规记录吗？这可能需要一些时间。',
      successMessage: '违规记录导出成功'
    })
  }

  /**
   * 导出统计数据
   */
  const exportStatistics = async (
    params: ExportParams,
    options: ExportOptions = {}
  ): Promise<boolean> => {
    return await quickExport('statistics', params, {
      ...options,
      confirmMessage: '确定要导出统计数据吗？这可能需要一些时间。',
      successMessage: '统计数据导出成功'
    })
  }

  /**
   * 导出区域配置
   */
  const exportRegionConfig = async (
    regions: any[],
    options: ExportOptions = {}
  ): Promise<boolean> => {
    try {
      const config = {
        regions,
        camera: options.filename?.includes('camera') ? options.filename.split('_')[1] : undefined,
        timestamp: new Date().toISOString()
      }

      const blob = new Blob([JSON.stringify(config, null, 2)], {
        type: 'application/json'
      })

      downloadBlob(blob, options.filename || `region-config-${Date.now()}.json`)

      options.onSuccess?.(blob)
      message.success(options.successMessage || '配置导出成功')
      return true
    } catch (error) {
      handleError(error, {
        customMessage: '配置导出失败',
        showMessage: true
      })
      options.onError?.(error)
      return false
    }
  }

  /**
   * 获取任务状态
   */
  const getTaskStatus = (taskId: string): ExportTask | undefined => {
    return exportTasks.value.get(taskId)
  }

  /**
   * 清理已完成的旧任务
   */
  const cleanupOldTasks = (maxAge: number = 3600000) => { // 默认1小时
    const now = Date.now()
    for (const [taskId, task] of exportTasks.value.entries()) {
      if (task.endTime && (now - task.endTime) > maxAge) {
        exportTasks.value.delete(taskId)
      }
    }
  }

  /**
   * 获取活跃任务
   */
  const getActiveTasks = (): ExportTask[] => {
    return Array.from(exportTasks.value.values()).filter(
      task => task.status === 'running' || task.status === 'pending'
    )
  }

  /**
   * 取消任务
   */
  const cancelTask = (taskId: string): boolean => {
    const task = exportTasks.value.get(taskId)
    if (task && (task.status === 'pending' || task.status === 'running')) {
      task.status = 'failed'
      task.error = '用户取消'
      task.endTime = Date.now()
      return true
    }
    return false
  }

  // 辅助函数
  const getTypeLabel = (type: ExportTask['type']): string => {
    const labels: Record<ExportTask['type'], string> = {
      'detection-records': '检测记录',
      'violations': '违规记录',
      'statistics': '统计数据',
      'regions': '区域配置',
      'config': '系统配置'
    }
    return labels[type] || type
  }

  return {
    // 任务管理
    createExportTask,
    executeExport,
    getTaskStatus,
    getActiveTasks,
    cancelTask,
    cleanupOldTasks,

    // 快速导出方法
    quickExport,
    exportDetectionRecords,
    exportViolations,
    exportStatistics,
    exportRegionConfig,

    // 状态
    exportTasks: readonly(exportTasks)
  }
}

// 导出类型
export type { ExportOptions, ExportTask }
