(function () {
    'use strict';

    function initVercelAnalytics() {
        if (typeof window === 'undefined') return;
        var isVercel = window.location.hostname.endsWith('.vercel.app') ||
            document.querySelector('meta[name="x-vercel-deployment-url"]') !== null;
        if (!isVercel) return;

        import('@vercel/analytics').then(function (module) {
            if (module.inject && typeof module.inject === 'function') {
                module.inject();
            }
        }).catch(function () {});
    }

    function loadGemSentinel() {
        if (typeof window === 'undefined' || document.querySelector('script[data-gem-sentinel]')) return;

        var css = document.createElement('link');
        css.rel = 'stylesheet';
        css.href = '/static/css/gem-sentinel.css';
        css.setAttribute('data-gem-sentinel', 'styles');
        document.head.appendChild(css);

        var script = document.createElement('script');
        script.type = 'module';
        script.src = '/static/js/gem-sentinel.js';
        script.setAttribute('data-gem-sentinel', 'module');
        document.body.appendChild(script);
    }

    function initialize() {
        initVercelAnalytics();
        loadGemSentinel();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initialize, { once: true });
    } else {
        initialize();
    }
})();
