const CACHE_NAME = 'tendersystems-blueprint-v2';
const urlsToCache = [
    '/',
    '/index.html',
    '/manifest.json'
];

// Список URL паттернов, которые НЕ должны кэшироваться (API запросы)
const API_PATTERNS = [
    '/api/',
    'localhost:8003',
    '127.0.0.1:8003'
];

// Проверка, является ли запрос API запросом
function isApiRequest(url) {
    return API_PATTERNS.some(pattern => url.includes(pattern));
}

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => {
                return cache.addAll(urlsToCache);
            })
    );
    // Принудительно активируем новый service worker
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames
                    .filter((name) => name !== CACHE_NAME)
                    .map((name) => caches.delete(name))
            );
        })
    );
    // Берем контроль над всеми страницами
    return self.clients.claim();
});

self.addEventListener('fetch', (event) => {
    const url = event.request.url;
    
    // Пропускаем API запросы БЕЗ перехвата - пусть браузер обрабатывает их напрямую
    if (isApiRequest(url)) {
        // НЕ вызываем event.respondWith для API запросов
        // Это позволяет браузеру обрабатывать их напрямую, минуя SW
        return;
    }
    
    // Для остальных запросов используем стратегию Network First
    event.respondWith(
        fetch(event.request)
            .then((response) => {
                // Клонируем ответ, так как он может быть использован только один раз
                const responseToCache = response.clone();
                
                // Кэшируем только успешные GET запросы
                if (event.request.method === 'GET' && response.status === 200) {
                    caches.open(CACHE_NAME).then((cache) => {
                        cache.put(event.request, responseToCache);
                    });
                }
                
                return response;
            })
            .catch(() => {
                // Если сеть недоступна, пытаемся получить из кэша
                return caches.match(event.request);
            })
    );
});
