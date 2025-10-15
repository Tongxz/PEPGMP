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
    async getHistory(params?: { limit?: number; camera_id?: string; alert_type?: string }) {
        const response = await http.get<{ count: number; items: AlertHistoryItem[] }>(
            '/alerts/history-db',
            { params }
        )
        return response.data
    },

    async listRules(params?: { camera_id?: string; enabled?: boolean }) {
        const response = await http.get<{ count: number; items: AlertRuleItem[] }>(
            '/alerts/rules',
            { params }
        )
        return response.data
    },

    async createRule(rule: Partial<AlertRuleItem>) {
        return await http.post('/alerts/rules', rule)
    },

    async updateRule(ruleId: number, updates: Partial<AlertRuleItem>) {
        return await http.put(`/alerts/rules/${ruleId}`, updates)
    },
}
