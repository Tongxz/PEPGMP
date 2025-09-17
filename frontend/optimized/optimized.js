/**
 * 优化的JavaScript文件 - 企业级前端交互
 * Optimized JavaScript for Enterprise Frontend
 */

// 全局配置
const CONFIG = {
    API_BASE_URL: '/api/v1',
    REFRESH_INTERVAL: 5000,
    MAX_RETRIES: 3,
    RETRY_DELAY: 1000,
    CACHE_DURATION: 30000, // 30秒缓存
    WEBSOCKET_RECONNECT_DELAY: 5000
};

// 状态管理
class StateManager {
    constructor() {
        this.state = {
            connectionStatus: 'connecting',
            cameras: {},
            statistics: {},
            systemMetrics: {},
            recentEvents: [],
            lastUpdate: null
        };
        this.listeners = new Map();
        this.cache = new Map();
    }

    // 订阅状态变化
    subscribe(key, callback) {
        if (!this.listeners.has(key)) {
            this.listeners.set(key, new Set());
        }
        this.listeners.get(key).add(callback);

        // 立即执行一次回调
        callback(this.state[key]);
    }

    // 取消订阅
    unsubscribe(key, callback) {
        if (this.listeners.has(key)) {
            this.listeners.get(key).delete(callback);
        }
    }

    // 更新状态
    setState(key, value) {
        const oldValue = this.state[key];
        this.state[key] = value;
        this.state.lastUpdate = Date.now();

        // 通知订阅者
        if (this.listeners.has(key)) {
            this.listeners.get(key).forEach(callback => {
                try {
                    callback(value, oldValue);
                } catch (error) {
                    console.error('State listener error:', error);
                }
            });
        }
    }

    // 获取状态
    getState(key) {
        return this.state[key];
    }
}

// HTTP客户端
class HttpClient {
    constructor() {
        this.cache = new Map();
        this.requestQueue = new Map();
    }

    async request(url, options = {}) {
        const cacheKey = `${url}_${JSON.stringify(options)}`;
        const now = Date.now();

        // 检查缓存
        if (this.cache.has(cacheKey)) {
            const cached = this.cache.get(cacheKey);
            if (now - cached.timestamp < CONFIG.CACHE_DURATION) {
                return cached.data;
            }
        }

        // 防止重复请求
        if (this.requestQueue.has(cacheKey)) {
            return this.requestQueue.get(cacheKey);
        }

        const requestPromise = this._makeRequest(url, options);
        this.requestQueue.set(cacheKey, requestPromise);

        try {
            const data = await requestPromise;

            // 缓存结果
            this.cache.set(cacheKey, {
                data,
                timestamp: now
            });

            return data;
        } finally {
            this.requestQueue.delete(cacheKey);
        }
    }

    async _makeRequest(url, options = {}) {
        const defaultOptions = {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            timeout: 10000
        };

        const finalOptions = { ...defaultOptions, ...options };

        for (let attempt = 1; attempt <= CONFIG.MAX_RETRIES; attempt++) {
            try {
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), finalOptions.timeout);

                const response = await fetch(url, {
                    ...finalOptions,
                    signal: controller.signal
                });

                clearTimeout(timeoutId);

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }

                const data = await response.json();
                return data;
            } catch (error) {
                console.warn(`Request attempt ${attempt} failed:`, error.message);

                if (attempt === CONFIG.MAX_RETRIES) {
                    throw error;
                }

                // 指数退避
                await this._delay(CONFIG.RETRY_DELAY * Math.pow(2, attempt - 1));
            }
        }
    }

    _delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    // 清理缓存
    clearCache() {
        this.cache.clear();
    }
}

// WebSocket管理器
class WebSocketManager {
    constructor() {
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 10;
        this.reconnectDelay = CONFIG.WEBSOCKET_RECONNECT_DELAY;
        this.listeners = new Map();
        this.isConnecting = false;
    }

    connect() {
        if (this.isConnecting || (this.ws && this.ws.readyState === WebSocket.OPEN)) {
            return;
        }

        this.isConnecting = true;
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;

        try {
            this.ws = new WebSocket(wsUrl);
            this._setupEventHandlers();
        } catch (error) {
            console.error('WebSocket connection failed:', error);
            this.isConnecting = false;
            this._scheduleReconnect();
        }
    }

    _setupEventHandlers() {
        this.ws.onopen = () => {
            console.log('WebSocket connected');
            this.isConnecting = false;
            this.reconnectAttempts = 0;
            this.emit('connection', { status: 'connected' });
        };

        this.ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.emit('message', data);
            } catch (error) {
                console.error('WebSocket message parse error:', error);
            }
        };

        this.ws.onclose = (event) => {
            console.log('WebSocket disconnected:', event.code, event.reason);
            this.isConnecting = false;
            this.emit('connection', { status: 'disconnected' });

            if (!event.wasClean) {
                this._scheduleReconnect();
            }
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.isConnecting = false;
            this.emit('connection', { status: 'error' });
        };
    }

    _scheduleReconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error('Max reconnection attempts reached');
            return;
        }

        this.reconnectAttempts++;
        const delay = this.reconnectDelay * Math.pow(1.5, this.reconnectAttempts - 1);

        console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);

        setTimeout(() => {
            this.connect();
        }, delay);
    }

    // 事件监听
    on(event, callback) {
        if (!this.listeners.has(event)) {
            this.listeners.set(event, new Set());
        }
        this.listeners.get(event).add(callback);
    }

    off(event, callback) {
        if (this.listeners.has(event)) {
            this.listeners.get(event).delete(callback);
        }
    }

    emit(event, data) {
        if (this.listeners.has(event)) {
            this.listeners.get(event).forEach(callback => {
                try {
                    callback(data);
                } catch (error) {
                    console.error('WebSocket listener error:', error);
                }
            });
        }
    }

    send(data) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(data));
        }
    }

    disconnect() {
        if (this.ws) {
            this.ws.close(1000, 'Client disconnect');
            this.ws = null;
        }
    }
}

// 性能监控
class PerformanceMonitor {
    constructor() {
        this.metrics = {
            fcp: null,
            lcp: null,
            fid: null,
            cls: null,
            ttfb: null
        };
        this.observers = new Map();
        this.init();
    }

    init() {
        if ('PerformanceObserver' in window) {
            this._observePaint();
            this._observeLCP();
            this._observeFID();
            this._observeCLS();
            this._observeNavigation();
        }
    }

    _observePaint() {
        const observer = new PerformanceObserver((list) => {
            for (const entry of list.getEntries()) {
                if (entry.name === 'first-contentful-paint') {
                    this.metrics.fcp = entry.startTime;
                    this._reportMetric('fcp', entry.startTime);
                }
            }
        });
        observer.observe({ entryTypes: ['paint'] });
        this.observers.set('paint', observer);
    }

    _observeLCP() {
        const observer = new PerformanceObserver((list) => {
            const entries = list.getEntries();
            const lastEntry = entries[entries.length - 1];
            this.metrics.lcp = lastEntry.startTime;
            this._reportMetric('lcp', lastEntry.startTime);
        });
        observer.observe({ entryTypes: ['largest-contentful-paint'] });
        this.observers.set('lcp', observer);
    }

    _observeFID() {
        const observer = new PerformanceObserver((list) => {
            for (const entry of list.getEntries()) {
                const fid = entry.processingStart - entry.startTime;
                this.metrics.fid = fid;
                this._reportMetric('fid', fid);
            }
        });
        observer.observe({ entryTypes: ['first-input'] });
        this.observers.set('fid', observer);
    }

    _observeCLS() {
        let clsValue = 0;
        const observer = new PerformanceObserver((list) => {
            for (const entry of list.getEntries()) {
                if (!entry.hadRecentInput) {
                    clsValue += entry.value;
                    this.metrics.cls = clsValue;
                    this._reportMetric('cls', clsValue);
                }
            }
        });
        observer.observe({ entryTypes: ['layout-shift'] });
        this.observers.set('cls', observer);
    }

    _observeNavigation() {
        const observer = new PerformanceObserver((list) => {
            for (const entry of list.getEntries()) {
                if (entry.entryType === 'navigation') {
                    this.metrics.ttfb = entry.responseStart - entry.requestStart;
                    this._reportMetric('ttfb', this.metrics.ttfb);
                }
            }
        });
        observer.observe({ entryTypes: ['navigation'] });
        this.observers.set('navigation', observer);
    }

    _reportMetric(name, value) {
        console.log(`Performance metric ${name}:`, value);

        // 发送到分析服务
        if (window.gtag) {
            window.gtag('event', 'web_vitals', {
                name,
                value: Math.round(value),
                event_category: 'Performance'
            });
        }
    }

    getMetrics() {
        return { ...this.metrics };
    }

    disconnect() {
        this.observers.forEach(observer => observer.disconnect());
        this.observers.clear();
    }
}

// 错误处理
class ErrorHandler {
    constructor() {
        this.errorCount = 0;
        this.maxErrors = 10;
        this.errorWindow = 60000; // 1分钟
        this.errors = [];
        this.init();
    }

    init() {
        // 全局错误处理
        window.addEventListener('error', (event) => {
            this.handleError({
                type: 'javascript',
                message: event.message,
                filename: event.filename,
                lineno: event.lineno,
                colno: event.colno,
                stack: event.error?.stack
            });
        });

        // Promise rejection处理
        window.addEventListener('unhandledrejection', (event) => {
            this.handleError({
                type: 'promise',
                message: event.reason?.message || 'Unhandled promise rejection',
                stack: event.reason?.stack
            });
        });
    }

    handleError(error) {
        const timestamp = Date.now();
        const errorWithTimestamp = { ...error, timestamp };

        // 添加到错误列表
        this.errors.push(errorWithTimestamp);

        // 清理过期错误
        this.errors = this.errors.filter(
            err => timestamp - err.timestamp < this.errorWindow
        );

        this.errorCount = this.errors.length;

        // 记录错误
        console.error('Application error:', errorWithTimestamp);

        // 发送错误报告
        this._reportError(errorWithTimestamp);

        // 检查错误阈值
        if (this.errorCount >= this.maxErrors) {
            this._handleErrorThreshold();
        }
    }

    _reportError(error) {
        // 发送到错误监控服务
        if (window.Sentry) {
            window.Sentry.captureException(new Error(error.message), {
                extra: error
            });
        }

        // 发送到自定义API
        fetch('/api/v1/errors', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(error)
        }).catch(err => console.error('Error reporting failed:', err));
    }

    _handleErrorThreshold() {
        console.error('Error threshold exceeded, showing error boundary');
        const errorBoundary = document.getElementById('errorBoundary');
        if (errorBoundary) {
            errorBoundary.style.display = 'block';
        }
    }

    getErrorStats() {
        return {
            count: this.errorCount,
            recent: this.errors.slice(-5),
            window: this.errorWindow
        };
    }
}

// 主应用类
class OptimizedApp {
    constructor() {
        this.stateManager = new StateManager();
        this.httpClient = new HttpClient();
        this.wsManager = new WebSocketManager();
        this.performanceMonitor = new PerformanceMonitor();
        this.errorHandler = new ErrorHandler();

        this.refreshInterval = null;
        this.isInitialized = false;
    }

    async init() {
        if (this.isInitialized) return;

        console.log('Initializing optimized app...');

        try {
            // 隐藏加载屏幕
            this._hideLoadingScreen();

            // 设置事件监听
            this._setupEventListeners();

            // 初始化WebSocket连接
            this.wsManager.connect();

            // 开始数据刷新
            this._startDataRefresh();

            // 初始化状态订阅
            this._setupStateSubscriptions();

            this.isInitialized = true;
            console.log('App initialized successfully');
        } catch (error) {
            console.error('App initialization failed:', error);
            this.errorHandler.handleError({
                type: 'initialization',
                message: error.message,
                stack: error.stack
            });
        }
    }

    _hideLoadingScreen() {
        const loadingScreen = document.getElementById('loadingScreen');
        const mainContainer = document.getElementById('mainContainer');

        if (loadingScreen && mainContainer) {
            setTimeout(() => {
                loadingScreen.style.opacity = '0';
                setTimeout(() => {
                    loadingScreen.style.display = 'none';
                    mainContainer.classList.add('loaded');
                }, 500);
            }, 1000);
        }
    }

    _setupEventListeners() {
        // 刷新按钮
        const refreshBtn = document.getElementById('refreshBtn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this.refreshData();
            });
        }

        // 设置按钮
        const settingsBtn = document.getElementById('settingsBtn');
        if (settingsBtn) {
            settingsBtn.addEventListener('click', () => {
                this.showSettings();
            });
        }

        // WebSocket连接状态
        this.wsManager.on('connection', (data) => {
            this.stateManager.setState('connectionStatus', data.status);
        });

        // WebSocket消息
        this.wsManager.on('message', (data) => {
            this._handleWebSocketMessage(data);
        });
    }

    _setupStateSubscriptions() {
        // 连接状态
        this.stateManager.subscribe('connectionStatus', (status) => {
            this._updateConnectionStatus(status);
        });

        // 相机状态
        this.stateManager.subscribe('cameras', (cameras) => {
            this._updateCameraStatus(cameras);
        });

        // 统计数据
        this.stateManager.subscribe('statistics', (stats) => {
            this._updateStatistics(stats);
        });

        // 系统指标
        this.stateManager.subscribe('systemMetrics', (metrics) => {
            this._updateSystemMetrics(metrics);
        });

        // 最近事件
        this.stateManager.subscribe('recentEvents', (events) => {
            this._updateRecentEvents(events);
        });
    }

    async refreshData() {
        try {
            // 并行获取数据
            const [cameras, statistics, systemInfo] = await Promise.allSettled([
                this.httpClient.request(`${CONFIG.API_BASE_URL}/cameras`),
                this.httpClient.request(`${CONFIG.API_BASE_URL}/statistics/summary`),
                this.httpClient.request(`${CONFIG.API_BASE_URL}/system/info`)
            ]);

            // 更新相机状态
            if (cameras.status === 'fulfilled') {
                this.stateManager.setState('cameras', cameras.value);
            }

            // 更新统计数据
            if (statistics.status === 'fulfilled') {
                this.stateManager.setState('statistics', statistics.value);
            }

            // 更新系统指标
            if (systemInfo.status === 'fulfilled') {
                this.stateManager.setState('systemMetrics', systemInfo.value);
            }

        } catch (error) {
            console.error('Data refresh failed:', error);
            this.errorHandler.handleError({
                type: 'data_refresh',
                message: error.message
            });
        }
    }

    _startDataRefresh() {
        // 立即刷新一次
        this.refreshData();

        // 设置定时刷新
        this.refreshInterval = setInterval(() => {
            this.refreshData();
        }, CONFIG.REFRESH_INTERVAL);
    }

    _handleWebSocketMessage(data) {
        switch (data.type) {
            case 'camera_status':
                this.stateManager.setState('cameras', data.cameras);
                break;
            case 'statistics_update':
                this.stateManager.setState('statistics', data.statistics);
                break;
            case 'system_metrics':
                this.stateManager.setState('systemMetrics', data.metrics);
                break;
            case 'event':
                this._addRecentEvent(data.event);
                break;
        }
    }

    _updateConnectionStatus(status) {
        const statusElement = document.getElementById('connectionStatus');
        if (statusElement) {
            statusElement.textContent = status === 'connected' ? '已连接' : '连接中...';
            statusElement.className = `status-indicator ${status === 'connected' ? 'connected' : 'disconnected'}`;
        }
    }

    _updateCameraStatus(cameras) {
        if (!cameras || typeof cameras !== 'object') return;

        Object.entries(cameras).forEach(([cameraId, status]) => {
            const statusElement = document.getElementById(`${cameraId}Status`);
            if (statusElement) {
                statusElement.textContent = status === 'online' ? '在线' : '离线';
                statusElement.className = `status-value ${status === 'online' ? 'online' : 'offline'}`;
            }
        });

        // 更新相机状态徽章
        const onlineCount = Object.values(cameras).filter(s => s === 'online').length;
        const totalCount = Object.keys(cameras).length;
        const badgeElement = document.getElementById('cameraStatusBadge');
        if (badgeElement) {
            badgeElement.textContent = `${onlineCount}/${totalCount}`;
            badgeElement.className = `card-badge ${onlineCount === totalCount ? 'realtime' : 'warning'}`;
        }
    }

    _updateStatistics(stats) {
        if (!stats) return;

        const elements = {
            totalDetections: document.getElementById('totalDetections'),
            violations: document.getElementById('violations'),
            accuracy: document.getElementById('accuracy')
        };

        if (elements.totalDetections) {
            elements.totalDetections.textContent = stats.total_detections || 0;
        }
        if (elements.violations) {
            elements.violations.textContent = stats.violations || 0;
        }
        if (elements.accuracy) {
            elements.accuracy.textContent = `${Math.round((stats.accuracy || 0) * 100)}%`;
        }

        // 更新统计徽章
        const badgeElement = document.getElementById('detectionStatsBadge');
        if (badgeElement) {
            badgeElement.textContent = '实时';
            badgeElement.className = 'card-badge realtime';
        }
    }

    _updateSystemMetrics(metrics) {
        if (!metrics) return;

        const elements = {
            cpuUsage: document.getElementById('cpuUsage'),
            cpuValue: document.getElementById('cpuValue'),
            memoryUsage: document.getElementById('memoryUsage'),
            memoryValue: document.getElementById('memoryValue'),
            gpuUsage: document.getElementById('gpuUsage'),
            gpuValue: document.getElementById('gpuValue')
        };

        // CPU使用率
        if (elements.cpuUsage && elements.cpuValue) {
            const cpuPercent = Math.round(metrics.cpu_usage || 0);
            elements.cpuUsage.style.width = `${cpuPercent}%`;
            elements.cpuValue.textContent = `${cpuPercent}%`;
        }

        // 内存使用率
        if (elements.memoryUsage && elements.memoryValue) {
            const memoryPercent = Math.round(metrics.memory_usage || 0);
            elements.memoryUsage.style.width = `${memoryPercent}%`;
            elements.memoryValue.textContent = `${memoryPercent}%`;
        }

        // GPU使用率
        if (elements.gpuUsage && elements.gpuValue) {
            const gpuPercent = Math.round(metrics.gpu_usage || 0);
            elements.gpuUsage.style.width = `${gpuPercent}%`;
            elements.gpuValue.textContent = `${gpuPercent}%`;
        }

        // 更新性能徽章
        const badgeElement = document.getElementById('systemPerformanceBadge');
        if (badgeElement) {
            const maxUsage = Math.max(
                metrics.cpu_usage || 0,
                metrics.memory_usage || 0,
                metrics.gpu_usage || 0
            );

            if (maxUsage > 80) {
                badgeElement.textContent = '警告';
                badgeElement.className = 'card-badge error';
            } else if (maxUsage > 60) {
                badgeElement.textContent = '注意';
                badgeElement.className = 'card-badge warning';
            } else {
                badgeElement.textContent = '正常';
                badgeElement.className = 'card-badge realtime';
            }
        }
    }

    _updateRecentEvents(events) {
        const eventsList = document.getElementById('recentEventsList');
        if (!eventsList || !Array.isArray(events)) return;

        eventsList.innerHTML = events.slice(0, 5).map(event => `
            <div class="event-item">
                <span class="event-time">${this._formatTime(event.timestamp)}</span>
                <span class="event-message">${event.message}</span>
            </div>
        `).join('');

        // 更新事件徽章
        const badgeElement = document.getElementById('recentEventsBadge');
        if (badgeElement) {
            badgeElement.textContent = '实时';
            badgeElement.className = 'card-badge realtime';
        }
    }

    _addRecentEvent(event) {
        const currentEvents = this.stateManager.getState('recentEvents') || [];
        const newEvents = [event, ...currentEvents].slice(0, 10);
        this.stateManager.setState('recentEvents', newEvents);
    }

    _formatTime(timestamp) {
        const date = new Date(timestamp);
        return date.toLocaleTimeString('zh-CN', {
            hour12: false,
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
    }

    showSettings() {
        // 实现设置对话框
        console.log('Settings dialog not implemented yet');
    }

    destroy() {
        // 清理资源
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }

        this.wsManager.disconnect();
        this.performanceMonitor.disconnect();
        this.httpClient.clearCache();

        console.log('App destroyed');
    }
}

// 初始化应用
document.addEventListener('DOMContentLoaded', () => {
    const app = new OptimizedApp();
    app.init();

    // 全局错误处理
    window.addEventListener('beforeunload', () => {
        app.destroy();
    });

    // 页面可见性变化
    document.addEventListener('visibilitychange', () => {
        if (document.hidden) {
            // 页面隐藏时暂停刷新
            if (app.refreshInterval) {
                clearInterval(app.refreshInterval);
            }
        } else {
            // 页面显示时恢复刷新
            app._startDataRefresh();
        }
    });
});

// 导出供其他模块使用
window.OptimizedApp = OptimizedApp;
