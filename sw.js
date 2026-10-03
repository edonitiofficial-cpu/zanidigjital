const CACHE_NAME = 'zani-digjital-v1';

// Instalohet aplikacioni në sfond
self.addEventListener('install', (event) => {
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    event.waitUntil(clients.claim());
});

// Lexon lajmet direkt nga rrjeti për t'i pasur gjithmonë të freskëta
self.addEventListener('fetch', (event) => {
    event.respondWith(
        fetch(event.request).catch(() => {
            return caches.match(event.request);
        })
    );
});
