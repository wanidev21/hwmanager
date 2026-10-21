const CACHE = 'hwm-v5';
const SDK = [
  'https://www.gstatic.com/firebasejs/10.8.0/firebase-app-compat.js',
  'https://www.gstatic.com/firebasejs/10.8.0/firebase-auth-compat.js',
  'https://www.gstatic.com/firebasejs/10.8.0/firebase-firestore-compat.js',
];
const SHELL = [
  '/',
  '/login',
  '/firebase-config.js',
  '/static/css/app.css',
  '/static/js/firebase-service.js',
  '/static/js/parts.js',
  '/static/icons/icon-192.png',
  '/static/icons/icon-512.png',
  ...SDK,
];
// 신호가 약한 곳(전산실 등)에서 네트워크 실패를 오래 기다리지 않도록, 캐시가 있으면 이 시간 후 캐시로 응답
const NET_TIMEOUT_MS = 4000;

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
  if (e.request.method !== 'GET') return;

  // Firebase SDK (버전 고정 URL이라 내용이 바뀌지 않음) → 캐시 우선. 오프라인에서도 앱 셸이 뜨도록
  if (SDK.includes(e.request.url)) {
    e.respondWith(
      caches.match(e.request).then(hit => hit || fetch(e.request).then(res => {
        if (res.ok) { const clone = res.clone(); caches.open(CACHE).then(c => c.put(e.request, clone)); }
        return res;
      }))
    );
    return;
  }

  // 같은 출처만 처리 (Firebase / Google API 요청은 브라우저에 맡김)
  if (url.origin !== self.location.origin) return;

  // Firebase Hosting 예약 경로(/__/auth 로그인 핸들러 등)는 캐시 우회
  if (url.pathname.startsWith('/__/')) return;

  // 네트워크 우선: 배포 즉시 최신 화면 반영. 오프라인이거나 응답이 늦으면(캐시가 있을 때만) 캐시 사용
  e.respondWith((async () => {
    const network = fetch(e.request).then(res => {
      if (res.ok) {
        const clone = res.clone();
        caches.open(CACHE).then(c => c.put(e.request, clone));
      }
      return res;
    });
    const cached = await caches.match(e.request, { ignoreSearch: true });
    if (!cached) return network;
    const timeout = new Promise(resolve => setTimeout(() => resolve(cached), NET_TIMEOUT_MS));
    return Promise.race([network.catch(() => cached), timeout]);
  })());
});
