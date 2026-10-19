// Firebase Hosting 도메인에서는 authDomain을 현재 도메인으로 맞춤
// (iOS Safari 등 서드파티 저장소 차단 환경에서 리다이렉트 로그인이 동작하도록)
if (/\.(web\.app|firebaseapp\.com)$/.test(location.hostname)) {
  firebaseConfig.authDomain = location.hostname;
}

firebase.initializeApp(firebaseConfig);

const _auth = firebase.auth();
const _db   = firebase.firestore();

// 오프라인 캐시 (탭 간 동기화). 지원하지 않는 브라우저면 무시
_db.enablePersistence({ synchronizeTabs: true }).catch(() => {});

// 로그인 허용 Google 계정 (도메인 제한 없음, 사용자 추가 시 여기에 이메일 추가)
const ALLOWED_EMAILS = ['karismawan1977@gmail.com'];

const _googleProvider = new firebase.auth.GoogleAuthProvider();
_googleProvider.addScope('https://www.googleapis.com/auth/calendar');
_googleProvider.setCustomParameters({ prompt: 'select_account' });

// 모바일·홈 화면 앱(PWA)은 팝업이 불안정하므로 리다이렉트 방식 사용
function _useRedirectLogin() {
  return window.matchMedia('(display-mode: standalone)').matches ||
    navigator.standalone === true ||
    /Android|iPhone|iPad|iPod|Mobile/i.test(navigator.userAgent) ||
    (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
}

// 페이지 단위 실시간 구독 목록 (페이지 전환 시 unwatchAll로 해제)
const _watchers = new Set();

window.FS = {
  ALLOWED_EMAILS,

  onAuthChanged(cb) {
    return _auth.onAuthStateChanged(cb);
  },
  getCurrentUser() {
    return _auth.currentUser;
  },
  async logout() {
    FS._loggingOut = true;   // signOut 직후 onAuthChanged(null)이 캐시 삭제 전에 페이지를 떠나지 않도록
    FS.unwatchAll();
    await _auth.signOut();
    // 공용 기기 대비: 로그아웃 시 로컬 캐시 삭제
    try { await _db.terminate(); await _db.clearPersistence(); }
    catch (e) { console.warn('오프라인 캐시 삭제 실패 (다른 탭이 열려 있으면 실패할 수 있음)', e); }
  },

  // 로그인 화면으로 이동 (앱 화면 기록을 남기지 않음)
  // index.html은 기록마다 state.n(첫 기록 0부터)을 둠 → 첫 기록까지 되감은 뒤 그 자리를 /login으로 교체
  // 그래야 로그인 화면에서 뒤로가기로 로그인 상태 화면이 다시 보이지 않음
  toLogin() {
    if (FS._leaving) return;
    FS._leaving = true;
    document.documentElement.style.visibility = 'hidden';   // 뒤로가기 캐시(bfcache)에 화면이 남지 않도록
    const go = () => location.replace('/login');
    const n = (history.state && history.state.n) || 0;
    if (n > 0) {
      window.addEventListener('popstate', go, { once: true });
      setTimeout(go, 800);   // popstate가 오지 않는 경우 대비
      history.go(-n);
    } else {
      go();
    }
  },
  isAllowedEmail(email) {
    return typeof email === 'string' && ALLOWED_EMAILS.includes(email.toLowerCase());
  },

  // 데스크톱은 팝업 → 결과 반환, 모바일은 리다이렉트 → 페이지 이동 (결과는 handleRedirectResult에서)
  async loginWithGoogle() {
    if (_useRedirectLogin()) {
      await _auth.signInWithRedirect(_googleProvider);
      return null;
    }
    return _auth.signInWithPopup(_googleProvider);
  },
  async handleRedirectResult() {
    return _auth.getRedirectResult();
  },
  // Google Calendar 토큰 재발급 (로그인 유지한 채 재인증)
  // 데스크톱: 팝업 → 토큰 반환 / 모바일: 리다이렉트 → index.html에서 결과 저장
  async reconnectGoogle() {
    const user = _auth.currentUser;
    if (!user) throw new Error('로그인이 필요합니다');
    if (_useRedirectLogin()) {
      await user.reauthenticateWithRedirect(_googleProvider);
      return null;
    }
    const result = await user.reauthenticateWithPopup(_googleProvider);
    const token = result.credential?.accessToken;
    if (token) localStorage.setItem('gAccessToken', token);
    return token || null;
  },
  // 로그인 결과 후처리: 도메인 검증, Calendar 토큰 저장, 신규 사용자 등록
  async completeLogin(result) {
    const user = result.user;
    if (!FS.isAllowedEmail(user.email)) {
      if (result.additionalUserInfo?.isNewUser) await user.delete();
      else await _auth.signOut();
      throw Object.assign(new Error('not allowed'), { code: 'app/email-not-allowed' });
    }
    const accessToken = result.credential?.accessToken;
    if (accessToken) localStorage.setItem('gAccessToken', accessToken);

    const ref = _db.collection('users').doc(user.uid);
    const snap = await ref.get();
    if (!snap.exists) {
      await ref.set({
        displayName: user.displayName || '',
        email:       user.email || '',
        photoURL:    user.photoURL || '',
        role:        'user',
        created_at:  firebase.firestore.FieldValue.serverTimestamp(),
      });
    }
    localStorage.setItem('hw-last-active', Date.now());
  },

  async getAll(collection, conditions = []) {
    let ref = _db.collection(collection);
    for (const [field, op, value] of conditions) {
      ref = ref.where(field, op, value);
    }
    const snap = await ref.get();
    return snap.docs.map(doc => ({ id: doc.id, ...doc.data() }));
  },
  async getOne(collection, id) {
    const doc = await _db.collection(collection).doc(id).get();
    if (!doc.exists) return null;
    return { id: doc.id, ...doc.data() };
  },
  async add(collection, data) {
    const now = firebase.firestore.FieldValue.serverTimestamp();
    const ref = await _db.collection(collection).add({
      ...data,
      created_at: now,
      updated_at: now,
    });
    return ref.id;
  },
  async update(collection, id, data) {
    const now = firebase.firestore.FieldValue.serverTimestamp();
    await _db.collection(collection).doc(id).update({
      ...data,
      updated_at: now,
    });
  },
  async remove(collection, id) {
    await _db.collection(collection).doc(id).delete();
  },

  listen(collection, callback, conditions = []) {
    let ref = _db.collection(collection);
    for (const [field, op, value] of conditions) {
      ref = ref.where(field, op, value);
    }
    return ref.onSnapshot(snap => {
      const docs = snap.docs.map(doc => ({ id: doc.id, ...doc.data() }));
      callback(docs);
    });
  },

  // 여러 컬렉션 실시간 구독. 모든 컬렉션의 첫 데이터가 도착한 뒤,
  // 이후 어느 쪽이든 변경될 때마다 cb([docs, docs, ...]) 호출.
  // specs: [['customers'], ['kb_articles', [['user_id', '==', uid]]], ...]
  // 반환값(stop)으로 개별 해제 가능. 페이지 전환 시 index.html이 unwatchAll() 호출.
  watch(specs, cb) {
    const results = new Array(specs.length);
    const loaded  = new Array(specs.length).fill(false);
    let scheduled = false;

    const unsubs = specs.map(([collection, conditions = []], i) => {
      let ref = _db.collection(collection);
      for (const [field, op, value] of conditions) {
        ref = ref.where(field, op, value);
      }
      return ref.onSnapshot(snap => {
        // 로컬 쓰기 직후 serverTimestamp가 null이 되지 않도록 추정값 사용
        results[i] = snap.docs.map(doc => ({ id: doc.id, ...doc.data({ serverTimestamps: 'estimate' }) }));
        loaded[i] = true;
        if (scheduled || loaded.includes(false)) return;
        // 같은 틱에 여러 컬렉션이 바뀌어도 한 번만 렌더링
        scheduled = true;
        queueMicrotask(() => {
          scheduled = false;
          try { cb(results.slice()); } catch (e) { console.error('[FS.watch] render error', e); }
        });
      }, err => {
        console.error(`[FS.watch] ${collection}`, err);
        if (window.Toast) Toast.error('데이터 동기화 오류: ' + (err.code || err.message));
      });
    });

    const stop = () => {
      unsubs.forEach(u => u());
      _watchers.delete(stop);
    };
    _watchers.add(stop);
    return stop;
  },
  unwatchAll() {
    [..._watchers].forEach(stop => stop());
  },

  // innerHTML 템플릿에 사용자 입력값을 넣을 때 사용 (<bond0> 같은 표기가 태그로 해석되지 않도록)
  esc(value) {
    return String(value ?? '')
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  },

  // <select>의 동적 옵션만 교체 (HTML에 있던 고정 옵션은 유지, 기존 선택값 복원)
  setOptions(sel, items) {
    if (!sel) return;
    const prev = sel.value;
    sel.querySelectorAll('option[data-dyn]').forEach(o => o.remove());
    items.forEach(({ value, label }) => {
      const o = document.createElement('option');
      o.value = value;
      o.textContent = label;
      o.dataset.dyn = '1';
      sel.appendChild(o);
    });
    if ([...sel.options].some(o => o.value === prev)) sel.value = prev;
  },

  // 로컬(KST) 기준 'YYYY-MM-DD' (toISOString은 UTC라 오전 9시 전에는 하루 전 날짜가 됨)
  localDate(d = new Date()) {
    const p = n => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
  },

  // #page-content 안에서만 스크롤 (scrollIntoView는 overflow:hidden인 상위 요소까지 밀어
  // 모바일에서 화면 위쪽이 잘린 채 되돌릴 수 없게 됨)
  // block: 'start' = 요소를 맨 위로, 'nearest' = 가려진 만큼만 이동
  scrollToEl(el, block = 'start') {
    const box = document.getElementById('page-content');
    if (!el || !box) return;
    const b = box.getBoundingClientRect();
    const r = el.getBoundingClientRect();
    let delta;
    if (block === 'nearest') {
      if (r.top < b.top) delta = r.top - b.top;
      else if (r.bottom > b.bottom) delta = Math.min(r.bottom - b.bottom, r.top - b.top);
      else return;
    } else {
      delta = r.top - b.top - 8;
    }
    box.scrollTo({ top: box.scrollTop + delta, behavior: 'smooth' });
  },
  requireAuth() {
    _auth.onAuthStateChanged(async user => {
      if (!user) {
        if (!FS._loggingOut) FS.toLogin();
        return;
      }
      // 허용 도메인 아닌 계정은 강제 로그아웃
      if (!FS.isAllowedEmail(user.email)) {
        await FS.logout();
        FS.toLogin();
      }
    });
  },
  formatDate(timestamp) {
    if (!timestamp) return '';
    if (typeof timestamp === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(timestamp)) {
      return timestamp.replace(/-/g, '.');
    }
    const d = timestamp.toDate ? timestamp.toDate() : new Date(timestamp);
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}.${m}.${day}`;
  },
  formatDateTime(timestamp) {
    if (!timestamp) return '';
    const d = timestamp.toDate ? timestamp.toDate() : new Date(timestamp);
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    const h = String(d.getHours()).padStart(2, '0');
    const min = String(d.getMinutes()).padStart(2, '0');
    return `${y}.${m}.${day} ${h}:${min}`;
  },
};
