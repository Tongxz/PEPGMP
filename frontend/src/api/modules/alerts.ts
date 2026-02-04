/**
 * 告警管理 API
 *
 * 提供告警历史查询、规则管理、状态更新等功能
 */

import request from '../index'

/**
 * 告警级别
 */
export type AlertLevel = 'low' | 'medium' | 'high' | 'critical'

/**
 * 告警状态
 */
export type AlertStatus = 'active' | 'resolved' | 'ignored'

/**
 * 告警数据接口
 */
export interface Alert {
    id: string
    camera_id: string
    camera_name?: string
    type: string  // 告警类型：violation, intrusion, etc.
    level: AlertLevel
    status: AlertStatus
    message: string
    description?: string
    timestamp: string
    resolved_at?: string
    resolved_by?: string
    image_url?: string
    video_url?: string
    metadata?: Record<string, any>
}

/**
 * 告警规则接口
 */
export interface AlertRule {
    id: string
    name: string
    type: string
    level: AlertLevel
    enabled: boolean
    conditions: Record<string, any>
    actions: Array<{
        type: string
        config: Record<string, any>
    }>
    created_at?: string
    updated_at?: string
}

/**
 * 告警规则创建请求
 */
export interface AlertRuleCreateRequest {
    name: string
    type: string
    level: AlertLevel
    enabled?: boolean
    conditions: Record<string, any>
    actions: Array<{
        type: string
        config: Record<string, any>
    }>
}

/**
 * 告警规则更新请求
 */
export interface AlertRuleUpdateRequest {
    name?: string
    type?: string
    level?: AlertLevel
    enabled?: boolean
    conditions?: Record<string, any>
    actions?: Array<{
        type: string
        config: Record<string, any>
    }>
}

/**
 * 告警查询参数
 */
export interface AlertQueryParams {
    camera_id?: string
    type?: string
    level?: AlertLevel
    status?: AlertStatus
    start_time?: string
    end_time?: string
    limit?: number
    offset?: number
}

/**
 * 告警统计数据
 */
export interface AlertStatistics {
    total: number
    active: number
    resolved: number
    ignored: number
    by_level: {
        low: number
        medium: number
        high: number
        critical: number
    }
    by_type: Record<string, number>
}

/**
 * 获取活跃告警列表
 *
 * @param params 查询参数
 * @returns 告警列表
 */
export const getActiveAlerts = (params?: AlertQueryParams): Promise<Alert[]> => {
    // 使用 monitoring 前缀（与后端 error_monitoring.py 路由匹配）
    return request.get('/api/v1/monitoring/alerts/active', { params })
}

/**
 * 获取告警历史
 *
 * @param params 查询参数
 * @returns 告警历史列表
 */
export const getAlertHistory = (params?: AlertQueryParams): Promise<Alert[]> => {
    // 使用 history-db 路由（后端实际提供的路由）
    return request.get('/api/v1/alerts/history-db', { params })
}

/**
 * 获取告警历史（从数据库）
 *
 * @param params 查询参数
 * @returns 告警历史列表
 */
export const getAlertHistoryFromDB = (params?: AlertQueryParams): Promise<Alert[]> => {
    return request.get('/api/v1/alerts/history-db', { params })
}

/**
 * 获取单个告警详情
 *
 * @param alertId 告警ID
 * @returns 告警详情
 */
export const getAlert = (alertId: string): Promise<Alert> => {
    return request.get(`/api/v1/alerts/${alertId}`)
}

/**
 * 解决告警
 *
 * @param alertId 告警ID
 * @param resolvedBy 解决人
 * @returns 更新后的告警
 */
export const resolveAlert = (alertId: string, resolvedBy?: string): Promise<Alert> => {
    // 使用 monitoring 前缀（与后端 error_monitoring.py 路由匹配）
    return request.post(`/api/v1/monitoring/alerts/${alertId}/resolve`, { resolved_by: resolvedBy })
}

/**
 * 更新告警状态
 *
 * @param alertId 告警ID
 * @param status 新状态
 * @returns 更新后的告警
 */
export const updateAlertStatus = (alertId: string, status: AlertStatus): Promise<Alert> => {
    return request.put(`/api/v1/alerts/history/${alertId}/status`, { status })
}

/**
 * 批量更新告警状态
 *
 * @param alertIds 告警ID列表
 * @param status 新状态
 * @returns 更新结果
 */
export const batchUpdateAlertStatus = (
    alertIds: string[],
    status: AlertStatus
): Promise<{ success: number; failed: number }> => {
    return request.post('/api/v1/alerts/batch-update-status', { alert_ids: alertIds, status })
}

/**
 * 获取告警规则列表
 *
 * @returns 规则列表
 */
export const getAlertRules = (): Promise<AlertRule[]> => {
    return request.get('/api/v1/alerts/rules')
}

/**
 * 获取单个告警规则
 *
 * @param ruleId 规则ID
 * @returns 规则详情
 */
export const getAlertRule = (ruleId: string): Promise<AlertRule> => {
    return request.get(`/api/v1/alerts/rules/${ruleId}`)
}

/**
 * 创建告警规则
 *
 * @param data 规则数据
 * @returns 创建的规则
 */
export const createAlertRule = (data: AlertRuleCreateRequest): Promise<AlertRule> => {
    return request.post('/api/v1/alerts/rules', data)
}

/**
 * 更新告警规则
 *
 * @param ruleId 规则ID
 * @param data 更新数据
 * @returns 更新后的规则
 */
export const updateAlertRule = (ruleId: string, data: AlertRuleUpdateRequest): Promise<AlertRule> => {
    return request.put(`/api/v1/alerts/rules/${ruleId}`, data)
}

/**
 * 删除告警规则
 *
 * @param ruleId 规则ID
 */
export const deleteAlertRule = (ruleId: string): Promise<void> => {
    return request.delete(`/api/v1/alerts/rules/${ruleId}`)
}

/**
 * 启用/禁用告警规则
 *
 * @param ruleId 规则ID
 * @param enabled 是否启用
 * @returns 更新后的规则
 */
export const toggleAlertRule = (ruleId: string, enabled: boolean): Promise<AlertRule> => {
    return request.put(`/api/v1/alerts/rules/${ruleId}`, { enabled })
}

/**
 * 获取告警级别列表
 *
 * @returns 级别列表
 */
export const getAlertLevels = (): Promise<Array<{ label: string; value: AlertLevel; color: string }>> => {
    // 使用 monitoring 前缀（与后端 error_monitoring.py 路由匹配）
    return request.get('/api/v1/monitoring/alerts/levels')
}

/**
 * 获取告警统计数据
 *
 * @param params 查询参数
 * @returns 统计数据
 */
export const getAlertStatistics = (params?: {
    start_time?: string
    end_time?: string
    camera_id?: string
}): Promise<AlertStatistics> => {
    return request.get('/api/v1/alerts/statistics', { params })
}

/**
 * 导出告警数据
 *
 * @param params 查询参数
 * @returns 导出文件Blob
 */
export const exportAlerts = (params?: AlertQueryParams & { format?: string }): Promise<Blob> => {
    return request.get('/api/v1/export/alerts', {
        params,
        responseType: 'blob'
    })
}
