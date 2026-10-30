const CACHE = "allmis-v2";
const PRECACHE = [
  "./",
  "allmis.json",
  "logga.png",
  "qr.svg",
  "manifest.webmanifest",
  "icons/icon-192.png",
  "icons/icon-512.png",
  "icons/apple-touch-icon.png",
];
const FONT_HOSTS = ["fonts.googleapis.com", "fonts.gstatic.com"];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE)
      .then((cache) => cache.addAll(PRECACHE.map((url) => new Request(url, { cache: "reload" }))))
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  );
});

async function networkFirst(request) {
  const cache = await caches.open(CACHE);
  const key = request.mode === "navigate" ? new URL("./", self.registration.scope).href : request.url;
  try {
    const fresh = await fetch(request.url, { cache: "no-cache", credentials: "same-origin" });
    if (fresh.ok) await cache.put(key, fresh.clone());
    return fresh;
  } catch (err) {
    const cached = await cache.match(key, { ignoreSearch: true });
    if (!cached) throw err;
    const headers = new Headers(cached.headers);
    headers.set("X-Allmis-Offline", "1");
    return new Response(cached.body, { status: cached.status, statusText: cached.statusText, headers });
  }
}

async function staleWhileRevalidate(request) {
  const cache = await caches.open(CACHE);
  const cached = await cache.match(request);
  const network = fetch(request)
    .then((res) => {
      if (res.ok || res.type === "opaque") cache.put(request, res.clone());
      return res;
    })
    .catch(() => cached);
  return cached || network;
}

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;
  const url = new URL(request.url);
  if (url.origin === self.location.origin) {
    event.respondWith(networkFirst(request));
  } else if (FONT_HOSTS.includes(url.hostname)) {
    event.respondWith(staleWhileRevalidate(request));
  }
});
