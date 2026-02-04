/**
 * API 服务层
 * 统一管理所有后端 API 调用
 */

import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios'

// API 基础配置
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
const API_TIMEOUT = 30000 // 30秒超时

// 创建 axios 实例
const apiClient: AxiosInstance = axios.create({
    baseURL: API_BASE_URL,
    timeout: API_TIMEOUT,
    headers: {
        'Content-Type': 'application/json'
    }
})

// 请求拦截器
apiClient.interceptors.request.use(
    (config) => {
        // 可以在这里添加 token
        const token = localStorage.getItem('token')
        if (token) {
            config.headers.Authorization = `Bearer ${token}`
        }
        return config
    },
    (error) => {
        return Promise.reject(error)
    }
)

// 响应拦截器
apiClient.interceptors.response.use(
    (response: AxiosResponse) => {
        return response.data
    },
    (error) => {
        // 统一错误处理
        if (error.response) {
            const { status, data } = error.response
            switch (status) {
                case 401:
                    // 未授权，跳转登录
                    console.error('未授权，请登录')
                    break
                case 403:
                    console.error('无权限访问')
                    break
                case 404:
                    console.error('请求的资源不存在')
                    break
                case 500:
                    console.error('服务器错误')
                    break
                case 503:
                    console.error('服务不可用:', data.detail || '服务暂时不可用')
                    break
                default:
                    console.error('请求失败:', data.detail || error.message)
            }
        } else if (error.request) {
            console.error('网络错误，请检查网络连接')
        } else {
            console.error('请求配置错误:', error.message)
        }
        return Promise.reject(error)
    }
)

// 通用请求方法
const request = {
    get: <T = any>(url: string, config?: AxiosRequestConfig): Promise<T> => {
        return apiClient.get(url, config)
    },
    post: <T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> => {
        return apiClient.post(url, data, config)
    },
    put: <T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> => {
        return apiClient.put(url, data, config)
    },
    delete: <T = any>(url: string, config?: AxiosRequestConfig): Promise<T> => {
        return apiClient.delete(url, config)
    },
    patch: <T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> => {
        return apiClient.patch(url, data, config)
    }
}

export { apiClient, request }
export default request
