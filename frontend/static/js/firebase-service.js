// 운영 Hosting 도메인에서는 authDomain을 현재 도메인으로 맞춤
// (iOS Safari 등 서드파티 저장소 차단 환경에서 리다이렉트 로그인이 동작하도록)
// 미리보기 채널(프로젝트--채널-xxxx.web.app)은 OAuth 리디렉션 URI에 등록되어 있지 않아
// redirect_uri_mismatch가 나므로 기본 authDomain(firebaseapp.com) 사용
if (/^[^.]+\.(web\.app|firebaseapp\.com)$/.test(location.hostname) && !location.hostname.includes('--')) {
  firebaseConfig.authDomain = location.hostname;
}

firebase.initializeApp(firebaseConfig);

function _writeFailed(e) {
  console.error('[FS] write failed', e);
  if (window.Toast) Toast.error('저장 실패: ' + (e.code || e.message));
}

// FS.icon()용 SVG 경로 (24×24, stroke)
const _ICONS = {
  home:     '<path d="M3 11l9-7 9 7"/><path d="M5 10v10h14V10"/>',
  server:   '<rect x="3" y="4" width="18" height="7" rx="1"/><rect x="3" y="13" width="18" height="7" rx="1"/><path d="M7 7.5h.01M7 16.5h.01"/>',
  building: '<path d="M4 21V5a1 1 0 011-1h9a1 1 0 011 1v16"/><path d="M15 9h4a1 1 0 011 1v11"/><path d="M8 8h3M8 12h3M8 16h3M3 21h18"/>',
  alert:    '<path d="M12 3l9.5 17h-19z"/><path d="M12 10v4M12 17h.01"/>',
  shield:   '<path d="M12 3l8 3v6c0 4.5-3.4 8-8 9-4.6-1-8-4.5-8-9V6z"/>',
  calendar: '<rect x="3" y="5" width="18" height="16" rx="1"/><path d="M3 10h18M8 3v4M16 3v4"/>',
  book:     '<path d="M4 4h6a2 2 0 012 2v14a2 2 0 00-2-2H4z"/><path d="M20 4h-6a2 2 0 00-2 2v14a2 2 0 012-2h6z"/>',
  notes:    '<rect x="5" y="3" width="14" height="18" rx="1"/><path d="M9 8h6M9 12h6M9 16h3"/>',
  clipboard:'<rect x="5" y="4" width="14" height="17" rx="1"/><path d="M9 4V3h6v1M9 10h6M9 14h6M9 18h3"/>',
  user:     '<circle cx="12" cy="8" r="4"/><path d="M4 21c0-4 3.6-6 8-6s8 2 8 6"/>',
  users:    '<circle cx="9" cy="8" r="3.5"/><path d="M2 20c0-3.5 3-5.5 7-5.5s7 2 7 5.5"/><path d="M16 4.5a3.5 3.5 0 010 7M18 14.5c2.4.6 4 2.4 4 5.5"/>',
  phone:    '<path d="M5 4h4l2 5-2.5 1.5a11 11 0 005 5L15 13l5 2v4a1 1 0 01-1 1A17 17 0 014 5a1 1 0 011-1z"/>',
  mail:     '<rect x="3" y="5" width="18" height="14" rx="1"/><path d="M3 7l9 6 9-6"/>',
  pin:      '<path d="M12 21s7-6.2 7-11.5A7 7 0 005 9.5C5 14.8 12 21 12 21z"/><circle cx="12" cy="9.5" r="2.5"/>',
  edit:     '<path d="M4 20h4L19 9l-4-4L4 16z"/><path d="M13.5 6.5l4 4"/>',
  trash:    '<path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13"/>',
  close:    '<path d="M6 6l12 12M18 6L6 18"/>',
  plus:     '<path d="M12 5v14M5 12h14"/>',
  check:    '<path d="M5 12.5l4.5 4.5L19 7"/>',
  search:   '<circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/>',
  scan:     '<path d="M4 7V5a1 1 0 011-1h2M17 4h2a1 1 0 011 1v2M20 17v2a1 1 0 01-1 1h-2M7 20H5a1 1 0 01-1-1v-2"/><path d="M8 8v8M11 8v8M14 8v8M17 8v8"/>',
  menu:     '<path d="M4 6h16M4 12h16M4 18h16"/>',
  more:     '<circle cx="5" cy="12" r="1.3"/><circle cx="12" cy="12" r="1.3"/><circle cx="19" cy="12" r="1.3"/>',
  logout:   '<path d="M15 4h4a1 1 0 011 1v14a1 1 0 01-1 1h-4"/><path d="M10 8l-4 4 4 4M6 12h11"/>',
  sun:      '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
  moon:     '<path d="M20 14.5A8 8 0 019.5 4a8 8 0 1010.5 10.5z"/>',
  refresh:  '<path d="M20 11a8 8 0 10-2.3 5.7"/><path d="M20 4v7h-7"/>',
  lock:     '<rect x="5" y="11" width="14" height="10" rx="1"/><path d="M8 11V7a4 4 0 018 0v4"/>',
  printer:  '<path d="M7 9V3h10v6"/><rect x="3" y="9" width="18" height="8" rx="1"/><path d="M7 14h10v7H7z"/>',
  eye:      '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
  box:      '<path d="M3 7l9-4 9 4v10l-9 4-9-4z"/><path d="M3 7l9 4 9-4M12 11v10"/>',
  flag:     '<path d="M5 21V4M5 4h11l-2 4 2 4H5"/>',
  wrench:   '<path d="M14.5 6.5a4 4 0 00-5.4 5.2L3 17.8V21h3.2l6.1-6.1a4 4 0 005.2-5.4l-2.6 2.6-2.4-2.4z"/>',
  bolt:     '<path d="M13 2L4 14h7l-1 8 9-12h-7z"/>',
  qr:       '<rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><path d="M14 14h3v3M21 14v7h-4M17 21h.01"/>',
  chevron:  '<path d="M9 6l6 6-6 6"/>',
  back:     '<path d="M15 6l-6 6 6 6"/>',
  tasks:    '<rect x="4" y="3" width="16" height="18" rx="1"/><path d="M7.5 8.5l1.5 1.5 2.5-2.5M7.5 15l1.5 1.5 2.5-2.5M14 9h3M14 15.5h3"/>',
  copy:     '<rect x="9" y="9" width="11" height="11" rx="1"/><path d="M5 15V5a1 1 0 011-1h10"/>',
};

const _auth = firebase.auth();
const _db   = firebase.firestore();

// 오프라인 캐시 (탭 간 동기화). 지원하지 않는 브라우저면 무시
_db.enablePersistence({ synchronizeTabs: true }).catch(() => {});

// 로그인 허용 계정은 Firestore config/access(emails)에서 관리 — 보안 규칙이 이 목록으로 접근을 막음.
// 앱은 그 문서를 읽어 보고(허용 계정만 읽기 가능) 허용 여부를 판단

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
  // true: 허용 / false: 목록에 없음 / null: 확인 불가(오프라인 등 — 로그아웃시키지 않음)
  async checkAccess() {
    try {
      await _db.collection('config').doc('access').get({ source: 'server' });
      return true;
    } catch (e) {
      if (e.code === 'permission-denied') return false;
      return null;
    }
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
    if (await FS.checkAccess() === false) {
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
  // 변경 이력 (누가·언제·무엇을). 추가 전용 — 규칙상 수정·삭제 불가. 서버 응답을 기다리지 않음
  // action: '등록'|'수정'|'삭제', entity: '티켓'|'장비'|'고객사'|'프로젝트', label: 화면 표시용 이름
  audit(action, entity, entityId, label, detail = '') {
    const u = _auth.currentUser;
    if (!u) return;
    _db.collection('audit_logs').add({
      action, entity, entity_id: entityId || '', label: String(label || '').slice(0, 200),
      detail: String(detail || '').slice(0, 500),
      by: u.uid, by_name: u.displayName || u.email || '',
      at: firebase.firestore.Timestamp.now(),   // 작업한 순간 (오프라인이어도 정확)
      created_at: firebase.firestore.FieldValue.serverTimestamp(),
    }).catch(e => console.warn('변경 이력 기록 실패', e));
  },
  // 등록자 정보 (문서에 함께 저장)
  creator() {
    const u = _auth.currentUser;
    return u ? { created_by: u.uid, created_by_name: u.displayName || u.email || '' } : {};
  },

  // 서버 응답을 기다리지 않는 쓰기 (전산실 등 오프라인에서도 화면이 멈추지 않도록).
  // 로컬 캐시에 즉시 반영되고 연결되면 동기화. 실패는 토스트로 알림. 새 문서 id를 바로 반환
  addNow(collection, data) {
    const now = firebase.firestore.FieldValue.serverTimestamp();
    const ref = _db.collection(collection).doc();
    ref.set({ ...data, created_at: now, updated_at: now }).catch(_writeFailed);
    return ref.id;
  },
  updateNow(collection, id, data) {
    const now = firebase.firestore.FieldValue.serverTimestamp();
    _db.collection(collection).doc(id).update({ ...data, updated_at: now }).catch(_writeFailed);
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

  // 선 아이콘 (이모지 대신 사용 — OS마다 모양이 달라지지 않도록). 색은 currentColor
  // 템플릿: ${FS.icon('edit')} / 정적 HTML: <i data-icon="edit"></i> (loadPage가 FS.hydrateIcons로 변환)
  icon(name, size = 18) {
    const p = _ICONS[name];
    if (!p) return '';
    return `<svg class="ico" width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${p}</svg>`;
  },
  hydrateIcons(root = document) {
    root.querySelectorAll('i[data-icon]').forEach(el => {
      el.outerHTML = FS.icon(el.dataset.icon, parseInt(el.dataset.size || '18'));
    });
  },

  // 프로젝트 워런티 기간 목록 [{type:'기본'|'연장', start, end, memo}] (시작일순)
  // 예전 데이터(warranty_expire만 있음)는 설치일~만료일 '기본' 1건으로 간주
  warrantyPeriods(p) {
    const str = v => !v ? '' : (typeof v === 'string' ? v : FS.localDate(v.toDate ? v.toDate() : new Date(v)));
    let list = Array.isArray(p.warranty_periods)
      ? p.warranty_periods.map(x => ({ type: x.type || '연장', start: str(x.start), end: str(x.end), memo: x.memo || '' }))
      : [];
    if (!list.length && p.warranty_expire) list = [{ type: '기본', start: str(p.install_date), end: str(p.warranty_expire), memo: '' }];
    return list.sort((a, b) => (a.start || a.end).localeCompare(b.start || b.end));
  },
  // '기본 3년 + 연장 2회' 형태 요약
  warrantySummary(periods) {
    if (!periods.length) return '';
    const base = periods.find(x => x.type === '기본');
    const ext = periods.filter(x => x.type !== '기본').length;
    let years = '';
    if (base && base.start && base.end) {
      const y = Math.round((new Date(base.end) - new Date(base.start)) / (365.25 * 86400000));
      if (y > 0) years = ` ${y}년`;
    }
    return (base ? `기본${years}` : '') + (ext ? `${base ? ' + ' : ''}연장 ${ext}회` : '');
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
      if (await FS.checkAccess() === false) {
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
