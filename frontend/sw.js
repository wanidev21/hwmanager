const CACHE = 'hwm-v2';
const SHELL = [
  '/',
  '/login',
  '/static/css/app.css',
  '/static/js/firebase-service.js',
  '/static/icons/icon-192.png',
  '/static/icons/icon-512.png',
];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);

  // GET + 같은 출처만 처리 (Firebase / Google API / CDN 요청은 브라우저에 맡김)
  if (e.request.method !== 'GET' || url.origin !== self.location.origin) return;

  // Firebase Hosting 예약 경로(/__/auth 로그인 핸들러 등)는 캐시 우회
  if (url.pathname.startsWith('/__/')) return;

  // 네트워크 우선: 배포 즉시 최신 화면 반영, 오프라인일 때만 캐시 사용
  e.respondWith(
    fetch(e.request)
      .then(res => {
        if (res.ok) {
          const clone = res.clone();
          caches.open(CACHE).then(c => c.put(e.request, clone));
        }
        return res;
      })
      .catch(() => caches.match(e.request, { ignoreSearch: true }))
  );
});
