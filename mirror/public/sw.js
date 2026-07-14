// Minimal service worker: makes Mirror installable and gives an offline shell.
//
// PRIVACY: we deliberately do NOT cache any photo bytes or signed URLs. Only
// the app shell (navigation + static assets) is cached. Photo requests always
// go to the network and are never persisted here.

const SHELL_CACHE = 'mirror-shell-v1';
const SHELL_ASSETS = ['/', '/manifest.json', '/icons/icon.svg'];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(SHELL_CACHE).then((cache) => cache.addAll(SHELL_ASSETS)),
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== SHELL_CACHE).map((k) => caches.delete(k))),
    ),
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET') return;

  const url = new URL(request.url);

  // Never touch Supabase (storage/signed URLs, auth, data). Straight to network.
  if (url.hostname.endsWith('.supabase.co')) return;

  // Network-first for navigations, falling back to the cached shell offline.
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request).catch(() => caches.match('/').then((r) => r || Response.error())),
    );
    return;
  }
});
