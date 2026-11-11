const CACHE_NAME = 'zani-digjital-v3';
const OFFLINE_PAGE = '/offline.html';
const CORE = [OFFLINE_PAGE, '/site.css', '/site.js', '/news-feed.js', '/site-widgets.js', '/zanidigjitalfavicon.png'];

self.addEventListener('install', event => {
    event.waitUntil(caches.open(CACHE_NAME).then(cache => cache.addAll(CORE)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', event => {
    event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(key => key.startsWith('zani-digjital-') && key !== CACHE_NAME).map(key => caches.delete(key)))).then(() => self.clients.claim()));
});

self.addEventListener('fetch', event => {
    const url = new URL(event.request.url);
    if (event.request.method !== 'GET' || url.origin !== self.location.origin || url.pathname === '/admin.html') return;
    const cacheable = event.request.mode === 'navigate' || CORE.includes(url.pathname) || url.pathname === '/ballina.json';
    if (!cacheable) return;
    event.respondWith((async () => {
        const cache = await caches.open(CACHE_NAME);
        try {
            const response = await fetch(event.request);
            if (response.ok && response.type === 'basic') {
                await cache.put(event.request, response.clone());
                const keys = await cache.keys();
                const pages = keys.filter(key => !CORE.includes(new URL(key.url).pathname));
                for (const key of pages.slice(0, Math.max(0, pages.length - 40))) await cache.delete(key);
            }
            return response;
        } catch {
            const cached = await cache.match(event.request);
            if (cached) return cached;
            if (event.request.mode === 'navigate') return (await cache.match(OFFLINE_PAGE)) || Response.error();
            return Response.error();
        }
    })());
});
