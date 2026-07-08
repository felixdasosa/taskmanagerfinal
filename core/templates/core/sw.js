const CACHE_NAME = 'taskmanager-cache-v1';

self.addEventListener('install', event => {
    // Instalăm motorul tăcut în fundal
    self.skipWaiting();
});

self.addEventListener('fetch', event => {
    // Interceptăm doar paginile (nu și trimiterea de formulare POST)
    if (event.request.method !== 'GET') return;

    event.respondWith(
        fetch(event.request)
            .then(response => {
                // Dacă avem internet, salvăm o copie nouă în memorie
                const responseClone = response.clone();
                caches.open(CACHE_NAME).then(cache => {
                    cache.put(event.request, responseClone);
                });
                return response;
            })
            .catch(() => {
                // FĂRĂ SEMNAL: Îi dăm instant din memorie ca să meargă mai departe
                return caches.match(event.request);
            })
    );
});