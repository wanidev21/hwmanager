# HW Manager

> **응답 언어: 항상 한국어.** 도구 출력이 영어여도 사용자에게 보내는 모든 답변은 한국어로 작성할 것.

## 프로젝트
서버 H/W 엔지니어 업무 관리 툴.
- **개발 원칙**: 필드의 H/W 엔지니어가 폰(PWA)으로 정말 편하게 쓰고, 사무실·집에서는 같은 데이터를 웹으로 편하게 수정·추가하는 도구. 모든 수정·기능 추가·점검은 이 관점(현장 한 손 조작, 빠른 조회, 적은 터치 / PC 편집 편의)으로 판단할 것
FastAPI는 정적 파일 서빙만 담당. 데이터는 모두 Firestore (서버 데이터 API 없음).

## 개발 환경 (로컬)
- 경로: `J:\claude\WORK\hwmanager` (Windows 11)
- GitHub: https://github.com/wanidev21/hwmanager (공개 저장소, 브랜치 main). `firebase-credentials.json`·`.env`는 .gitignore로 제외. 개인정보(전화번호·회사 이메일)를 코드에 넣지 말 것
- Python 3.10 (시스템), Docker 미설치 → 로컬에서 uvicorn 직접 실행
- 의존성: `pip install -r requirements.txt`
- 포트: **8471** (8000은 사용 금지)
- 실행: `python -m uvicorn main:app --host 0.0.0.0 --port 8471 --reload`
- 확인: http://localhost:8471/api/health → `{"success": true}`
- 배포: **Firebase Hosting** (`firebase.json`, `.firebaserc`, public = `frontend/`) → https://hwmanager-593ba.web.app
  - CLI: `npm i -g firebase-tools` → `firebase login` → `firebase deploy --only hosting`
  - 폰 테스트는 `firebase hosting:channel:deploy test` 미리보기 채널 사용 (로컬 http/LAN IP로는 Google 로그인 불가)
- Dockerfile / docker-compose.yml / main.py는 예전 서버 배포용. 지금은 로컬 미리보기 용도로만 main.py 사용

## 스택
- 호스팅: Firebase Hosting (로컬은 FastAPI + uvicorn으로 정적 서빙)
- 인증: Firebase Auth Google 로그인 단일 (도메인 제한 없음, Firestore `config/access.emails` 허용 목록, 기본 스코프(이메일·프로필)만 — Google 캘린더 연동은 2026-10 제거)
- Firebase 계정(콘솔·CLI 로그인): karismawan1977@gmail.com
- DB: Firestore (Firebase 프로젝트 `hwmanager-593ba`)
- SDK: Firebase compat 10.8.0 (type="module" 방식 사용 안함)
- PWA: manifest.json + sw.js (서비스워커 캐시 `hwm-v1`)
- 대상: PC 웹 + 모바일 웹앱(PWA, iOS/Android 모두 "홈 화면에 추가")
- 관리 스크립트: firebase-admin + `firebase-credentials.json` (서비스 계정 키, 절대 커밋/공유 금지)

## 프론트엔드 구조 (SPA)
- `index.html`이 셸(사이드바 + 헤더). 메뉴 클릭 시 `/pages/{page}.html`을 fetch → `<style>`/`<script>`를 추출해 `#page-content`에 주입
- `pages/*.html`은 **완전한 HTML 문서가 아닌 조각(fragment)**. `<head>`·Firebase SDK 스크립트를 넣지 않음
- 페이지 스크립트는 전역(window) 스코프에 주입되므로 함수명 충돌 주의
- 기본 페이지: overview
- Firebase SDK는 `index.html`, `login.html`의 head에만 아래 순서로 로드:
  1. https://www.gstatic.com/firebasejs/10.8.0/firebase-app-compat.js
  2. https://www.gstatic.com/firebasejs/10.8.0/firebase-auth-compat.js
  3. https://www.gstatic.com/firebasejs/10.8.0/firebase-firestore-compat.js
  4. /firebase-config.js
  5. /static/js/firebase-service.js
- Firestore 접근은 `firebase-service.js`의 공통 헬퍼(getAll / getOne / add / update / remove / listen) 사용

## 파일 구조
```
hwmanager/
├── main.py
├── requirements.txt
├── .env / .env.example        # HOST, PORT
├── firebase-credentials.json  # 서비스 계정 키 (scripts용)
├── firebase.json, .firebaserc, firestore.rules   # Firebase Hosting·규칙
├── Dockerfile, docker-compose.yml, .dockerignore   # 배포용
├── scripts/                   # Firestore 관리 스크립트 (seed/reset/migrate/set_admin/reassign_owner/test)
└── frontend/
    ├── index.html             # SPA 셸
    ├── login.html
    ├── firebase-config.js
    ├── manifest.json, sw.js
    ├── static/
    │   ├── css/app.css
    │   ├── js/firebase-service.js
    │   ├── js/parts.js        # window.Parts: 부품 등록 창·단계 진행·반납 기한 계산
    │   └── icons/
    └── pages/
        ├── overview.html      # 개요 (기본)
        ├── customers.html     # 고객사·프로젝트·장비
        ├── delivery.html      # 작성·수정·서명·인쇄는 PC 전용, 폰(768px 이하)은 품목 확인만
        ├── tickets.html
        ├── warranty.html
        ├── parts.html         # 부품·RMA 현황 (반납 기한순). 등록·단계 로직은 static/js/parts.js (티켓 상세와 공용)
        ├── jobs.html          # 작업 일정 + 준비 체크리스트 (팀 공용, 하단 탭 '작업')
        ├── calendar.html      # 내 일정(개인 calendar_events) + 팀 작업 일정 표시
        ├── kb.html
        ├── tech.html
        ├── users.html         # 관리자 전용 메뉴
        └── infra.html         # 현재 사이드바 메뉴에 연결 안 됨
```

## URL 라우팅 (main.py)
- `/` → frontend/index.html
- `/login` → frontend/login.html
- `/static/*` → frontend/static/
- `/pages/*` → frontend/pages/
- `/firebase-config.js`, `/manifest.json`, `/sw.js` → frontend/ 해당 파일
- `/api/health` → `{"success": true}`

## Firestore 컬렉션
customers, projects, assets, tickets(+ logs 하위: 진행 기록), kb_articles,
audit_logs(변경 이력, 추가 전용), config/access(허용 계정),
jobs(작업 일정: date·time·customer/asset/ticket 연결·status 예정/완료/취소, items 맵 {id:{text,due_days,done,order}} — 체크는 `items.<id>.done` 필드 단위 갱신),
job_templates(준비 템플릿: name, items[{text, due_days}], 비어 있으면 jobs.html의 기본 템플릿 사용·첫 저장 시 함께 저장),
parts(부품·RMA: ticket_id·customer_id·asset_id 연결, status 요청/입고/교체/반납/종결, dates{단계:날짜}, 반납 기한=dates.교체+return_days, return_required=false면 교체→종결),
internal_assets, tech_domains, tech_topics, tech_notes, releases,
delivery_notes, delivery_items, calendar_events, users

- kb_articles / tech_* / releases: 문서에 `user_id` (작성자 uid) 기록

## 데이터 계층 구조
customers → projects (customer_id) → assets (customer_id, project_id)
- projects: 워런티는 프로젝트 단위로 관리 (warranty_expire)
- assets: hostname, serial, ip, os, cpu, memory, gpu, disk, bios_version, bmc_version, raid_version, driver_version 등 (현장에서 관리하는 펌웨어는 BIOS·BMC·RAID — 작업 완료 시 jobs.html에서 갱신, 작업 문서에 fw_changes 기록)

## 인증 흐름
1. login.html → `FS.loginWithGoogle()`: PC는 팝업, 모바일·PWA는 리다이렉트 (`FS.handleRedirectResult()`로 결과 처리)
   - Hosting 도메인(web.app)에서는 authDomain을 현재 도메인으로 바꿔 iOS Safari 리다이렉트 문제 회피
2. `FS.completeLogin()`: `FS.checkAccess()`(config/access 읽기 — 규칙상 허용 계정만 가능)로 확인해 목록에 없으면 거부, 신규 사용자 → users/{uid} 문서 생성 (role: 'user')
3. index.html: onAuthStateChanged로 확인, 미로그인 → /login
4. 30분 미사용 시 자동 로그아웃 (localStorage `hw-last-active`)
5. users.role === 'admin' 이면 사용자 관리 메뉴 표시
- 개인 데이터(kb_articles, tech_*, releases, calendar_events)는 `user_id == uid`로 필터 (클라이언트 쿼리 기준)
- Firestore 보안 규칙: `firestore.rules` (배포: `firebase deploy --only firestore:rules`)
  - 사용자 추가: 허용 목록(회원 관리 화면의 '로그인 허용 계정' 또는 `python scripts/access.py add <email>`). 이메일은 코드·저장소에 넣지 않음
    (OAuth 앱이 '테스트' 상태로 남아 있으면 Google Cloud 콘솔 OAuth 테스트 사용자에도 추가해야 함. 기본 스코프만 쓰므로 '프로덕션'으로 게시하면 이 단계 불필요)
  - 개인 데이터는 규칙에서도 `user_id == uid`만 허용, 공용 업무 데이터는 허용 계정 모두 읽기/쓰기, 목록에 없는 컬렉션은 차단
- 관리자 지정: `python scripts/set_admin.py <email>`
- 개인 데이터 소유자 이전: `python scripts/reassign_owner.py <from> <to> [--execute]`

## 실시간 동기화
- 모든 페이지의 `init()`은 `FS.watch([[컬렉션, 조건], ...], cb)`로 실시간 구독 → 데이터 바뀔 때마다 cb에서 다시 렌더링
- `loadPage()`가 페이지 전환 시 `FS.unwatchAll()`로 구독 해제. 페이지 코드에서 `getAll`로 목록을 불러오지 말 것 (편집 화면 등 1회성 조회만 허용)
- 저장 함수의 로컬 배열 갱신은 즉시 반영용으로 남아 있어도 무방 (스냅샷이 덮어씀)
- 동적 `<select>` 옵션은 `FS.setOptions()`로 채움 (중복 방지 + 선택값 유지)
- innerHTML 템플릿에 사용자 입력값을 넣을 때는 반드시 `${FS.esc(값)}` (`<bond0>` 같은 표기가 태그로 사라지는 것 방지). 문서 ID·고정 상수는 제외
- 오프라인 캐시(enablePersistence) 사용, 로그아웃 시 캐시 삭제
- sw.js는 네트워크 우선 (배포 즉시 반영), `/__/` 경로는 우회
- 전체 검색(index.html): 상단 검색 버튼 / PC Ctrl+K·`/` → 장비·고객사·프로젝트·티켓·작업. 처음 열 때 `FS.listen`으로 구독 시작해 계속 유지(unwatchAll 대상 아님). 결과는 `hwPageFilter` + `loadPage(page, {force:true})`로 열기 (같은 화면이어도 다시 열림)
- 급한 일 배지(index.html `_renderTodayBadges`): 같은 구독 데이터로 메뉴 옆 숫자·하단 탭 '홈'·탭 제목·설치 앱 아이콘(`navigator.setAppBadge`). 합계 = 긴급 미완료 장애 + 오늘/지난 예정 작업·준비 기한 도래 작업 + 반납 기한 3일 이내 부품 (워런티 30일 내는 메뉴에만)
- 엑셀 내보내기(PC 전용 `.pc-only`): `FS.exportXlsx(파일명, [{name, rows}])` — SheetJS(cdnjs xlsx 0.18.5)를 누를 때만 로드, 실패 시 CSV(UTF-8 BOM). 고객사·자산(장비+고객사 시트), 워런티(보이는 목록)
- 저장 대기 배지(index.html 상단): FS 쓰기 함수(add/update/remove/addNow/updateNow/audit)는 `_track()`으로 미확인 건수 집계, `FS.hasPendingWrites()`(waitForPendingWrites)로 페이지가 직접 쓴 것까지 확인. 새 쓰기 헬퍼를 만들면 `_track()`으로 감쌀 것

## 모바일
- PWA로 통일 (2026-10 결정). 예전 Capacitor 앱 `C:\waniwani\Claude\HWManagerMobile`(이메일 로그인, 구버전 포크)은 더 이상 개발하지 않음

## 모바일 설치 안내
- PC 사이드바 "📱 모바일 설치" → `static/icons/install-qr.svg` (배포 주소 QR, segno로 생성). 주소가 바뀌면 QR 재생성
- 폰(768px 이하)·설치된 앱(standalone)에서는 이 메뉴 숨김

## 디자인
- Linear/Notion 스타일 (심플, 여백 충분, 테두리 얇게)
- Primary #e8540a, 배경 #f7f7f5, 카드 #ffffff
- PC 우선, 사이드바 240px 고정 (768px 이하 모바일 대응 CSS 있음)
