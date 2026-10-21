"""
스모크 테스트: 모든 화면을 PC·폰 크기로 열어 오류·로딩 실패·가로 넘침을 확인하고 스크린샷을 남긴다.
agent-browser(헤드리스 Chrome)로 실행. Google 로그인 대신 테스트 전용 계정에 커스텀 토큰으로 로그인.

테스트 계정: smoke@hwmanager.test (실제 메일함 없음, 비밀번호 없음 — 서비스 계정 키로만 로그인 가능, 일반 사용자 권한)
  처음 실행 시 Firebase 인증에 만들고 허용 목록(config/access)에 추가함.
  차단: python scripts/smoke_test.py --remove   (허용 목록에서 빼고 계정 삭제)

사용법:
  python -m uvicorn main:app --port 8471      # 로컬 서버 먼저
  python scripts/smoke_test.py                 # 기본 http://localhost:8471
  python scripts/smoke_test.py --base https://hwmanager-593ba--test-xxxx.web.app
  python scripts/smoke_test.py --pages tickets,parts --only phone

결과: smoke-results/ (스크린샷 + report.txt). 문제가 있으면 종료 코드 1
"""
import os
import sys
import json
import time
import shutil
import tempfile
import argparse
import subprocess
import warnings

sys.stdout.reconfigure(encoding='utf-8')
warnings.filterwarnings('ignore', category=FutureWarning)

import firebase_admin
from firebase_admin import credentials, firestore, auth

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
CRED_PATH = os.path.join(ROOT, 'firebase-credentials.json')
OUT_DIR = os.path.join(ROOT, 'smoke-results')

TEST_UID = 'smoke-test'
TEST_EMAIL = 'smoke@hwmanager.test'
SESSION = 'hwm-smoke'

PAGES = ['overview', 'customers', 'tickets', 'parts', 'jobs', 'warranty', 'calendar', 'delivery', 'kb', 'tech']
VIEWPORTS = {'pc': (1366, 800), 'phone': (390, 844)}

AB = shutil.which('agent-browser') or 'agent-browser'


def ab(*args, stdin=None, check=True):
    """agent-browser 실행 → --json 결과의 data"""
    env = {**os.environ, 'AGENT_BROWSER_SESSION': SESSION}
    # 출력은 파이프 대신 임시 파일로: 처음 실행 때 뜨는 브라우저 데몬이 파이프를 물고 있으면 Windows에서 끝나지 않음
    with tempfile.TemporaryFile('w+', encoding='utf-8') as out, tempfile.TemporaryFile('w+', encoding='utf-8') as err:
        subprocess.run([AB, *args, '--json'], input=stdin, stdin=None if stdin is not None else subprocess.DEVNULL,
                       stdout=out, stderr=err, text=True, encoding='utf-8', env=env, timeout=90)
        out.seek(0); err.seek(0)
        stdout, stderr = out.read().strip(), err.read().strip()
    try:
        res = json.loads(stdout.splitlines()[-1]) if stdout else {}
    except json.JSONDecodeError:
        res = {}
    if check and not res.get('success'):
        raise RuntimeError(f'agent-browser {args[0]} 실패: {res.get("error") or stderr or stdout}')
    return res.get('data') or {}


def js(code):
    """페이지에서 JS 실행 (Promise는 기다림) → 결과값"""
    return ab('eval', '--stdin', stdin=code).get('result')


def ensure_test_user():
    try:
        auth.get_user(TEST_UID)
    except auth.UserNotFoundError:
        auth.create_user(uid=TEST_UID, email=TEST_EMAIL, email_verified=True, display_name='스모크 테스트')
        print(f'테스트 계정 생성: {TEST_EMAIL}')
    ref = firestore.client().collection('config').document('access')
    emails = (ref.get().to_dict() or {}).get('emails', [])
    if TEST_EMAIL not in emails:
        ref.set({'emails': firestore.ArrayUnion([TEST_EMAIL])}, merge=True)
        print('허용 목록에 테스트 계정 추가')


def remove_test_user():
    firestore.client().collection('config').document('access').set({'emails': firestore.ArrayRemove([TEST_EMAIL])}, merge=True)
    try:
        auth.delete_user(TEST_UID)
    except auth.UserNotFoundError:
        pass
    firestore.client().collection('users').document(TEST_UID).delete()
    print('테스트 계정 삭제·허용 목록에서 제거 완료')


def wait_for(cond_js, timeout=10, interval=0.3):
    end = time.time() + timeout
    while time.time() < end:
        if js(cond_js):
            return True
        time.sleep(interval)
    return False


def login(base):
    token = auth.create_custom_token(TEST_UID).decode()
    ab('open', base + '/login')
    if not wait_for('typeof firebase !== "undefined" && !!firebase.auth', 15):
        raise RuntimeError('로그인 화면 로드 실패')
    # 토큰은 명령줄·출력에 남지 않도록 stdin으로만 전달
    # hw-login-pending: 로그인 버튼을 누른 것과 같게 (없으면 login.html이 '오래된 세션'으로 보고 로그아웃)
    js('sessionStorage.setItem("hw-login-pending", "1"), '
       f'firebase.auth().signInWithCustomToken({json.dumps(token)}).then(() => "ok", e => "ERR " + e.code)')
    # login.html이 허용 확인·사용자 등록 뒤 '/'로 이동
    if not wait_for('location.pathname === "/" && typeof loadPage === "function" && !!FS.getCurrentUser()', 20):
        raise RuntimeError('로그인 후 메인 화면으로 이동하지 못함 (허용 목록·규칙 확인)')


PAGE_CHECK = r"""
(async () => {
  const box = document.getElementById('page-content');
  const t0 = Date.now();
  while (Date.now() - t0 < 10000 && box.querySelector('.skeleton-page')) await new Promise(r => setTimeout(r, 200));
  await new Promise(r => setTimeout(r, 1500));   // 실시간 데이터 첫 렌더
  const doc = document.documentElement;
  const wide = [...box.querySelectorAll('*')].filter(el => {
    if (el.closest('.table-wrap, [style*="overflow-x"], .tabbar')) return false;
    const r = el.getBoundingClientRect();
    return r.width > 0 && r.right > innerWidth + 2 && getComputedStyle(el).position !== 'fixed';
  }).slice(0, 3).map(el => el.tagName.toLowerCase() + (el.id ? '#' + el.id : '') + (el.className && typeof el.className === 'string' ? '.' + el.className.trim().split(/\s+/).join('.') : ''));
  return {
    title: document.getElementById('page-title').textContent,
    loadFailed: box.textContent.includes('페이지를 불러올 수 없습니다'),
    stillLoading: !!box.querySelector('.skeleton-page'),
    pageOverflow: doc.scrollWidth - innerWidth,
    wide,
    toastsError: [...document.querySelectorAll('.toast-error .toast-msg')].map(e => e.textContent),
  };
})()
"""

FLOW_SEARCH = r"""
(async () => {
  openSearch();
  const inp = document.getElementById('gs-q');
  // 데이터에 있는 장비 이름 앞부분으로 검색 (시연 데이터가 바뀌어도 동작)
  const t1 = Date.now();
  while (Date.now() - t1 < 5000 && !gsData.assets.length) await new Promise(r => setTimeout(r, 200));
  const q = (gsData.assets[0]?.hostname || 'a').slice(0, 4);
  inp.value = q; inp.dispatchEvent(new Event('input'));
  await new Promise(r => setTimeout(r, 300));
  const hits = document.querySelectorAll('#gs-results .gs-hit').length;
  const first = document.querySelector('#gs-results .gs-hit');
  if (first) first.click();
  const t0 = Date.now();
  while (Date.now() - t0 < 8000) {
    const m = document.getElementById('asset-view-modal');
    if (m && m.style.display === 'flex') return { q, hits, opened: true };
    await new Promise(r => setTimeout(r, 200));
  }
  return { q, hits, opened: false };
})()
"""


def collect_errors():
    errs = []
    for e in (ab('errors', check=False).get('errors') or []):
        errs.append('pageerror: ' + str(e.get('message') or e)[:300])
    for m in (ab('console', check=False).get('messages') or []):
        if m.get('type') == 'error':
            errs.append('console: ' + str(m.get('text'))[:300])
    ab('errors', '--clear', check=False)
    ab('console', '--clear', check=False)
    return errs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', default='http://localhost:8471')
    ap.add_argument('--pages', default=','.join(PAGES))
    ap.add_argument('--only', choices=list(VIEWPORTS), help='한 화면 크기만')
    ap.add_argument('--remove', action='store_true', help='테스트 계정 삭제·허용 목록에서 제거')
    args = ap.parse_args()

    firebase_admin.initialize_app(credentials.Certificate(CRED_PATH))
    if args.remove:
        remove_test_user()
        return

    base = args.base.rstrip('/')
    pages = [p.strip() for p in args.pages.split(',') if p.strip()]
    os.makedirs(OUT_DIR, exist_ok=True)
    ensure_test_user()

    problems, lines = [], []
    try:
        login(base)
        collect_errors()   # 로그인 과정 메시지는 제외
        for vp, (w, h) in VIEWPORTS.items():
            if args.only and vp != args.only:
                continue
            ab('set', 'viewport', str(w), str(h))
            js('location.reload(), "ok"')
            wait_for('typeof loadPage === "function" && !!FS.getCurrentUser() && !document.querySelector("#page-content .skeleton-page")', 20)
            for page in pages:
                js(f'loadPage({json.dumps(page)}, {{ nav: true }}), "ok"')
                r = js(PAGE_CHECK) or {}
                shot = os.path.join(OUT_DIR, f'{vp}-{page}.png')
                ab('screenshot', shot, check=False)
                errs = collect_errors()
                bad = []
                if r.get('loadFailed'): bad.append('화면 로드 실패')
                if r.get('stillLoading'): bad.append('10초 넘게 로딩 중')
                if (r.get('pageOverflow') or 0) > 2: bad.append(f'가로 넘침 {r["pageOverflow"]}px {r.get("wide")}')
                bad += [f'오류 토스트: {t}' for t in r.get('toastsError') or []]
                bad += errs
                status = 'OK ' if not bad else 'NG '
                lines.append(f'{status}[{vp}] {page:<10} {r.get("title", "")}')
                for b in bad:
                    lines.append(f'      - {b}')
                    problems.append(f'[{vp}] {page}: {b}')
                print(lines[-1 - len(bad)])
                for b in bad:
                    print(f'      - {b}')
            # 흐름: 전체 검색(장비 이름 앞부분) → 장비 상세
            js('loadPage("overview", { nav: true }), "ok"')
            wait_for('!document.querySelector("#page-content .skeleton-page")', 10)
            s = js(FLOW_SEARCH) or {}
            ab('screenshot', os.path.join(OUT_DIR, f'{vp}-flow-search.png'), check=False)
            errs = collect_errors()
            ok = s.get('hits', 0) > 0 and s.get('opened') and not errs
            lines.append(f'{"OK " if ok else "NG "}[{vp}] 흐름: 검색 "{s.get("q", "")}" → 결과 {s.get("hits", 0)}건 → 장비 상세 {"열림" if s.get("opened") else "안 열림"}')
            print(lines[-1])
            if not ok:
                problems.append(f'[{vp}] 검색 흐름: {s} {errs}')
            js('closeSearch(); document.getElementById("asset-view-modal") && closeAssetView(), "ok"')
    finally:
        ab('close', check=False)

    report = '\n'.join(lines + ['', f'문제 {len(problems)}건'] + problems)
    with open(os.path.join(OUT_DIR, 'report.txt'), 'w', encoding='utf-8') as f:
        f.write(report + '\n')
    print(f'\n문제 {len(problems)}건 — 스크린샷·보고서: {os.path.relpath(OUT_DIR, ROOT)}/')
    sys.exit(1 if problems else 0)


if __name__ == '__main__':
    main()
