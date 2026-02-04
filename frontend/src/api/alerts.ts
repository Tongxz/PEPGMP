import { http } from '@/lib/http'

export interface AlertHistoryItem {
    id: number
    rule_id?: number | null
    camera_id: string
    alert_type: string
    message: string
    details?: any
    notification_sent?: boolean
    notification_channels_used?: string[] | null
    timestamp: string
    status?: 'pending' | 'confirmed' | 'false_positive' | 'resolved'
    handled_at?: string
    handled_by?: string
}

export interface AlertRuleItem {
    id: number
    name: string
    camera_id?: string | null
    rule_type: string
    conditions: any
    notification_channels?: string[]
    recipients?: string[]
    enabled: boolean
    priority?: string
    created_at?: string
    updated_at?: string
}

export const alertsApi = {
    async getHistory(params?: {
        limit?: number
        offset?: number
        page?: number
        camera_id?: string
        alert_type?: string
        sort_by?: string
        sort_order?: 'asc' | 'desc'
    }) {
        const response = await http.get<{
            count: number
            total: number
            items: AlertHistoryItem[]
            limit: number
            offset: number
        }>('/alerts/history-db', { params })
        return response.data
    },

    async listRules(params?: {
        limit?: number
        offset?: number
        page?: number
        camera_id?: string
        enabled?: boolean
    }) {
        const response = await http.get<{
            count: number
            total: number
            items: AlertRuleItem[]
            limit: number
            offset: number
        }>('/alerts/rules', { params })
        return response.data
    },

    async createRule(rule: Partial<AlertRuleItem>) {
        return await http.post('/alerts/rules', rule)
    },

    async updateRule(ruleId: number, updates: Partial<AlertRuleItem>) {
        return await http.put(`/alerts/rules/${ruleId}`, updates)
    },

    async deleteRule(ruleId: number) {
        return await http.delete(`/alerts/rules/${ruleId}`)
    },

    async getRuleDetail(ruleId: number) {
        const response = await http.get<AlertRuleItem>(`/alerts/rules/${ruleId}`)
        return response.data
    },

    async updateAlertStatus(alertId: number, status: 'confirmed' | 'false_positive' | 'resolved', notes?: string) {
        const response = await http.put(`/alerts/history/${alertId}/status`, {
            status,
            notes
        })
        return response.data
    },
}
