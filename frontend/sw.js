const CACHE_NAME = 'mishkat-shell-v2';
const SHELL = [
  '/',
  '/manifest.webmanifest',
  '/assets/styles.css',
  '/assets/app.js',
  '/assets/mishkat-mark.svg',
  '/assets/mishkat-icon-192.png',
  '/assets/mishkat-icon-512.png'
];

self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE_NAME).then(cache => cache.addAll(SHELL)));
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(key => key !== CACHE_NAME).map(key => caches.delete(key)))));
  self.clients.claim();
});

self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);
  // Never cache API responses, authenticated data, uploads, or anything outside the static shell.
  if (event.request.method !== 'GET' || url.origin !== self.location.origin || url.pathname.startsWith('/api/')) return;
  if (SHELL.includes(url.pathname)) {
    event.respondWith(caches.match(event.request).then(cached => cached || fetch(event.request)));
  }
});
