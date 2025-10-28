import { useMessage } from 'naive-ui'
import { onMounted, onUnmounted, ref } from 'vue'

export interface StatusUpdate {
    type: 'status_update'
    camera_id?: string
    data: Record<string, any>
    timestamp: number
}

export function useWebSocket() {
    const message = useMessage()
    const connected = ref(false)
    const ws = ref<WebSocket | null>(null)
    const statusData = ref<Record<string, any>>({})
    const reconnectAttempts = ref(0)
    const maxReconnectAttempts = 5
    const reconnectDelay = 3000

    const connect = () => {
        try {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
            const host = window.location.host
            const wsUrl = `${protocol}//${host}/ws/status`

            console.log('连接状态WebSocket:', wsUrl)

            ws.value = new WebSocket(wsUrl)

            ws.value.onopen = () => {
                connected.value = true
                reconnectAttempts.value = 0
                console.log('状态WebSocket连接成功')
            }

            ws.value.onmessage = (event) => {
                try {
                    const data: StatusUpdate = JSON.parse(event.data)

                    if (data.type === 'status_update') {
                        if (data.camera_id) {
                            // 单个摄像头状态更新
                            statusData.value[data.camera_id] = data.data
                        } else if (data.data) {
                            // 所有摄像头状态更新
                            statusData.value = { ...statusData.value, ...data.data }
                        }
                    }
                } catch (error) {
                    console.error('解析WebSocket消息失败:', error)
                }
            }

            ws.value.onerror = (error) => {
                console.error('状态WebSocket错误:', error)
                connected.value = false
            }

            ws.value.onclose = () => {
                connected.value = false
                console.log('状态WebSocket连接关闭')

                // 自动重连
                if (reconnectAttempts.value < maxReconnectAttempts) {
                    setTimeout(() => {
                        reconnectAttempts.value++
                        console.log(`尝试重连状态WebSocket (${reconnectAttempts.value}/${maxReconnectAttempts})`)
                        connect()
                    }, reconnectDelay)
                }
            }
        } catch (error) {
            console.error('创建状态WebSocket连接失败:', error)
        }
    }

    const disconnect = () => {
        if (ws.value) {
            ws.value.close()
            ws.value = null
        }
        connected.value = false
    }

    const sendPing = () => {
        if (ws.value && connected.value) {
            ws.value.send(JSON.stringify({ type: 'ping' }))
        }
    }

    onMounted(() => {
        connect()
    })

    onUnmounted(() => {
        disconnect()
    })

    return {
        connected,
        statusData,
        connect,
        disconnect,
        sendPing
    }
}
