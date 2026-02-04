/**
 * WebSocket视频流管理 Hook
 *
 * 功能：
 * - 建立WebSocket连接
 * - 接收视频帧
 * - 自动重连
 * - 连接状态管理
 */

import { onUnmounted, ref, Ref } from 'vue'

export type VideoStreamStatus = 'disconnected' | 'connecting' | 'connected' | 'error'

export interface VideoStreamOptions {
    autoConnect?: boolean
    reconnectInterval?: number
    maxReconnectAttempts?: number
}

export interface VideoFrame {
    frame: string  // base64编码的JPEG图片
    timestamp?: string
    camera_id?: string
}

export function useVideoStream(cameraId: string, options: VideoStreamOptions = {}) {
    const {
        autoConnect = false,
        reconnectInterval = 3000,
        maxReconnectAttempts = 10
    } = options

    const status: Ref<VideoStreamStatus> = ref('disconnected')
    const error: Ref<string | null> = ref(null)
    const lastFrame: Ref<string | null> = ref(null)
    const fps: Ref<number> = ref(0)

    let ws: WebSocket | null = null
    let reconnectTimer: number | null = null
    let reconnectAttempts = 0
    let frameCount = 0
    let fpsTimer: number | null = null

    const frameCallbacks: Array<(frame: string) => void> = []

    // 计算FPS
    const startFpsCounter = () => {
        if (fpsTimer) return

        fpsTimer = window.setInterval(() => {
            fps.value = frameCount
            frameCount = 0
        }, 1000)
    }

    const stopFpsCounter = () => {
        if (fpsTimer) {
            clearInterval(fpsTimer)
            fpsTimer = null
        }
        fps.value = 0
        frameCount = 0
    }

    // 建立WebSocket连接
    const connect = () => {
        if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
            console.log(`⚠️ WebSocket已连接或正在连接: ${cameraId}`)
            return
        }

        status.value = 'connecting'
        error.value = null

        // 构造WebSocket URL
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
        const host = window.location.host
        const wsUrl = `${protocol}//${host}/api/v1/video-stream/ws/${cameraId}`

        console.log(`🔌 连接WebSocket: ${wsUrl}`)

        try {
            ws = new WebSocket(wsUrl)

            ws.onopen = () => {
                console.log(`✅ WebSocket已连接: ${cameraId}`)
                status.value = 'connected'
                error.value = null
                reconnectAttempts = 0
                startFpsCounter()

                if (reconnectTimer) {
                    clearTimeout(reconnectTimer)
                    reconnectTimer = null
                }
            }

            ws.onmessage = async (event) => {
                try {
                    let frameBase64: string | null = null

                    // 处理Blob类型的数据（二进制图片数据）
                    if (event.data instanceof Blob) {
                        // 检查Blob的MIME类型
                        if (event.data.type.startsWith('image/')) {
                            // 直接是图片，转换为base64
                            const reader = new FileReader()
                            reader.onload = () => {
                                const base64 = (reader.result as string).split(',')[1]
                                if (base64) {
                                    lastFrame.value = base64
                                    frameCount++

                                    // 触发所有回调
                                    frameCallbacks.forEach(cb => {
                                        try {
                                            cb(base64)
                                        } catch (err) {
                                            console.error('帧回调执行失败:', err)
                                        }
                                    })
                                }
                            }
                            reader.readAsDataURL(event.data)
                            return
                        }

                        // 尝试解析为JSON
                        try {
                            const text = await event.data.text()
                            const data: VideoFrame = JSON.parse(text)
                            frameBase64 = data.frame
                        } catch {
                            // 如果不是JSON，可能是原始JPEG数据，转换为base64
                            const reader = new FileReader()
                            reader.onload = () => {
                                const base64 = (reader.result as string).split(',')[1]
                                if (base64) {
                                    lastFrame.value = base64
                                    frameCount++

                                    // 触发所有回调
                                    frameCallbacks.forEach(cb => {
                                        try {
                                            cb(base64)
                                        } catch (err) {
                                            console.error('帧回调执行失败:', err)
                                        }
                                    })
                                }
                            }
                            reader.readAsDataURL(event.data)
                            return
                        }
                    } else if (typeof event.data === 'string') {
                        // 处理字符串类型的数据
                        try {
                            const data: VideoFrame = JSON.parse(event.data)
                            frameBase64 = data.frame
                        } catch {
                            // 可能直接是base64字符串
                            frameBase64 = event.data
                        }
                    } else {
                        // 直接使用对象
                        const data: VideoFrame = event.data
                        frameBase64 = data.frame
                    }

                    if (frameBase64) {
                        lastFrame.value = frameBase64
                        frameCount++

                        // 触发所有回调
                        frameCallbacks.forEach(cb => {
                            try {
                                cb(frameBase64!)
                            } catch (err) {
                                console.error('帧回调执行失败:', err)
                            }
                        })
                    }
                } catch (err) {
                    console.error('解析视频帧失败:', err)
                }
            }

            ws.onerror = (event) => {
                console.error(`❌ WebSocket错误: ${cameraId}`, event)
                status.value = 'error'
                error.value = 'WebSocket连接错误'
                stopFpsCounter()
            }

            ws.onclose = (event) => {
                console.log(`🔌 WebSocket已断开: ${cameraId}, code: ${event.code}, reason: ${event.reason}`)
                status.value = 'disconnected'
                ws = null
                stopFpsCounter()

                // 自动重连
                if (reconnectAttempts < maxReconnectAttempts) {
                    reconnectAttempts++
                    console.log(`🔄 ${reconnectInterval / 1000}秒后尝试重连 (${reconnectAttempts}/${maxReconnectAttempts})`)

                    reconnectTimer = window.setTimeout(() => {
                        connect()
                    }, reconnectInterval)
                } else {
                    console.error(`❌ 达到最大重连次数 (${maxReconnectAttempts})，停止重连`)
                    error.value = '连接失败，已达到最大重连次数'
                }
            }
        } catch (err: any) {
            console.error('创建WebSocket失败:', err)
            status.value = 'error'
            error.value = err.message || '创建WebSocket失败'
        }
    }

    // 断开连接
    const disconnect = () => {
        console.log(`🔌 主动断开WebSocket: ${cameraId}`)

        if (reconnectTimer) {
            clearTimeout(reconnectTimer)
            reconnectTimer = null
        }

        stopFpsCounter()

        if (ws) {
            ws.close()
            ws = null
        }

        status.value = 'disconnected'
        reconnectAttempts = 0
    }

    // 注册帧回调
    const onFrame = (callback: (frame: string) => void) => {
        frameCallbacks.push(callback)

        // 返回取消注册函数
        return () => {
            const index = frameCallbacks.indexOf(callback)
            if (index > -1) {
                frameCallbacks.splice(index, 1)
            }
        }
    }

    // 重置重连计数
    const resetReconnectAttempts = () => {
        reconnectAttempts = 0
    }

    // 组件卸载时自动断开
    onUnmounted(() => {
        disconnect()
    })

    // 自动连接
    if (autoConnect) {
        connect()
    }

    return {
        status,
        error,
        lastFrame,
        fps,
        connect,
        disconnect,
        onFrame,
        resetReconnectAttempts
    }
}
