(function () {
    const items = [
        { name: '首页', href: '/frontend/index.html', key: 'index' },
        { name: '摄像头配置', href: '/frontend/camera_config.html', key: 'cameras' },
        { name: '区域配置', href: '/frontend/region_config.html', key: 'regions' },
        { name: '统计看板', href: '/frontend/statistics.html', key: 'stats' },
        { name: '系统信息', href: '/frontend/system_info.html', key: 'system' },
    ];
    const rightItems = [
        { name: '下载叠加图', href: '/api/v1/download/overlay?name=overlay_debug', key: 'overlay', target: '_blank' },
        { name: 'API 文档', href: '/docs', key: 'docs', target: '_blank' },
    ];

    function isActive(href) {
        try {
            const p = location.pathname || '';
            return p.endsWith(href.split('/').pop());
        } catch (_) {
            return false;
        }
    }

    function renderNav() {
        const nav = document.createElement('div');
        nav.className = 'topnav';
        const brand = document.createElement('a');
        brand.className = 'brand';
        brand.href = '/frontend/index.html';
        brand.textContent = 'HBD';
        nav.appendChild(brand);

        items.forEach(it => {
            const a = document.createElement('a');
            a.href = it.href;
            a.textContent = it.name;
            if (isActive(it.href)) a.classList.add('active');
            nav.appendChild(a);
        });

        const spacer = document.createElement('div');
        spacer.className = 'spacer';
        nav.appendChild(spacer);

        const right = document.createElement('div');
        right.className = 'right';
        rightItems.forEach(it => {
            const a = document.createElement('a');
            a.href = it.href;
            a.textContent = it.name;
            if (it.target) a.target = it.target;
            right.appendChild(a);
        });
        nav.appendChild(right);

        document.body.insertAdjacentElement('afterbegin', nav);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', renderNav);
    } else {
        renderNav();
    }
})();


