const CACHE_VERSION = "3";
const CACHE_NAME = `sporo-cache-${CACHE_VERSION}`;
const MAP_TILE_CACHE = "sporo-map-tiles";

// Core assets to pre-cache for offline availability
const PRECACHE_ASSETS = [
    "/",
    "/login",
    "/farmer",
    "/onboarding",
    "/static/css/styles.css?v=3",
    "/static/js/translations.js?v=3",
    "/static/js/main.js?v=3",
    "/static/js/map_handler.js",
    "/static/manifest.json",
    "/static/images/icon-192.png",
    "/static/images/icon-512.png",
    "/static/images/sample_strip.png",
    "/static/images/sample_strip_safe.png",
    "/static/images/sample_strip_monitor.png",
    "/static/images/sample_strip_caution.png",
    "/static/images/sample_strip_critical.png",
    "/static/regional_map.pmtiles",
    // Cache map engines locally so map loads offline
    "https://unpkg.com/maplibre-gl@3.6.2/dist/maplibre-gl.js",
    "https://unpkg.com/maplibre-gl@3.6.2/dist/maplibre-gl.css",
    "https://unpkg.com/pmtiles@2.11.0/dist/index.js"
];

// Install Event
self.addEventListener("install", (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            return cache.addAll(PRECACHE_ASSETS);
        }).then(() => self.skipWaiting())
    );
});

// Activate Event
self.addEventListener("activate", (event) => {
    event.waitUntil(
        caches.keys().then((keys) => {
            return Promise.all(
                keys.map((key) => {
                    if (key !== CACHE_NAME && key !== MAP_TILE_CACHE) {
                        return caches.delete(key);
                    }
                })
            );
        }).then(() => self.clients.claim())
    );
});

// Fetch Event Interceptor
self.addEventListener("fetch", (event) => {
    // Only intercept GET requests. POST requests (e.g. logins, scan uploads) must bypass service worker caching.
    if (event.request.method !== "GET") {
        return;
    }

    const url = new URL(event.request.url);

    // 1. Special handling for map tiles (OpenStreetMap / MapLibre)
    if (url.hostname.includes("tile.openstreetmap.org") || url.pathname.endsWith(".pbf") || url.pathname.includes("/tiles/")) {
        event.respondWith(
            caches.open(MAP_TILE_CACHE).then((cache) => {
                return cache.match(event.request).then((cachedResponse) => {
                    // Fetch and update cache in background (Stale-While-Revalidate)
                    const fetchPromise = fetch(event.request).then((networkResponse) => {
                        cache.put(event.request, networkResponse.clone());
                        return networkResponse;
                    }).catch(() => null); // Ignore network failure when offline
                    
                    return cachedResponse || fetchPromise || new Response("Offline map tile unavailable", { status: 503 });
                });
            })
        );
        return;
    }

    // 2. Navigation requests (HTML pages) -> Network-First (always get fresh server-rendered page if online)
    if (event.request.mode === "navigate") {
        event.respondWith(
            fetch(event.request)
                .then((networkResponse) => {
                    // Cache the fresh page for offline fallback
                    if (networkResponse.status === 200) {
                        const responseClone = networkResponse.clone();
                        caches.open(CACHE_NAME).then((cache) => {
                            cache.put(event.request, responseClone);
                        });
                    }
                    return networkResponse;
                })
                .catch(() => {
                    // Fallback to cache when completely offline
                    return caches.match(event.request).then((cachedResponse) => {
                        return cachedResponse || caches.match("/farmer") || caches.match("/login");
                    });
                })
        );
        return;
    }

    // 3. Network-First strategy for local static assets (JS, CSS, JSON) to avoid stale cache issues,
    // falling back to Cache-First for external resources or images.
    const isLocalStatic = url.origin === self.location.origin && 
                          (url.pathname.endsWith(".js") || url.pathname.endsWith(".css") || url.pathname.endsWith(".json"));

    if (isLocalStatic) {
        event.respondWith(
            fetch(event.request)
                .then((networkResponse) => {
                    if (networkResponse.status === 200) {
                        const responseClone = networkResponse.clone();
                        caches.open(CACHE_NAME).then((cache) => {
                            cache.put(event.request, responseClone);
                        });
                    }
                    return networkResponse;
                })
                .catch(() => {
                    return caches.match(event.request);
                })
        );
        return;
    }

    // 4. Default Stale-While-Revalidate/Cache-First strategy for other static assets (images, external CDNs)
    event.respondWith(
        caches.match(event.request).then((cachedResponse) => {
            if (cachedResponse) {
                // Fetch in background to update cache for next time
                fetch(event.request).then((networkResponse) => {
                    if (networkResponse.status === 200) {
                        caches.open(CACHE_NAME).then((cache) => {
                            cache.put(event.request, networkResponse);
                        });
                    }
                }).catch(() => {});
                
                return cachedResponse;
            }

            return fetch(event.request);
        })
    );
});
