# HW Manager

서버 H/W 엔지니어를 위한 업무 관리 웹앱입니다.
고객사·프로젝트·장비 자산, 장애 티켓, 워런티, 납품확인서, 일정, 지식베이스를 한곳에서 관리하고, **PC와 휴대폰(아이폰·안드로이드)에서 같은 데이터를 실시간으로** 읽고 쓸 수 있습니다.

- 서버 없이 동작합니다. 화면은 **Firebase Hosting**, 데이터는 **Firestore**, 로그인은 **Google 계정**을 사용합니다.
- 휴대폰에서는 앱스토어 없이 **홈 화면에 추가(PWA)** 해서 앱처럼 씁니다.
- 한 기기에서 수정하면 다른 기기 화면에 **새로고침 없이 바로** 반영됩니다.

---

## 목차

1. [주요 기능](#1-주요-기능)
2. [어떻게 동작하나요](#2-어떻게-동작하나요)
3. [준비물](#3-준비물)
4. [설치 가이드 (처음 한 번)](#4-설치-가이드-처음-한-번)
5. [사용 방법](#5-사용-방법)
6. [사용자 추가하기](#6-사용자-추가하기)
7. [코드 수정 후 다시 배포하기](#7-코드-수정-후-다시-배포하기)
8. [로컬에서 개발하기](#8-로컬에서-개발하기)
9. [관리 스크립트](#9-관리-스크립트)
10. [문제 해결 (자주 만나는 오류)](#10-문제-해결-자주-만나는-오류)
11. [보안 참고 사항](#11-보안-참고-사항)
12. [프로젝트 구조](#12-프로젝트-구조)

---

## 1. 주요 기능

| 메뉴 | 하는 일 |
|---|---|
| **개요** | 고객사 수, 처리 중인 티켓, 워런티 만료 임박 프로젝트 등을 한눈에 보는 대시보드 |
| **고객사·자산** | 고객사 → 프로젝트 → 장비(hostname, serial, IP, OS, CPU, GPU, BMC/BIOS/드라이버 버전 등) 3단 관리, CSV로 장비 일괄 등록 |
| **납품확인서** | 품목 입력, 공급자·인수자 서명(터치/마우스), A4 미리보기·인쇄(PDF 저장) |
| **장애 티켓** | 접수 → 진행중 → 보류 → 완료 상태 관리, 완료일 자동 기록 |
| **워런티 현황** | 프로젝트별 워런티 만료일과 남은 기간 (만료·30일·90일 이내 표시) |
| **캘린더** | 앱 전용 일정 + Google 캘린더 일정 함께 보기·등록 |
| **지식베이스** | 장애 증상·원인·조치 순서를 문서로 정리 (본인 것만 보임) |
| **기술 학습** | 기술 도메인별 학습 토픽 진행 상태, 노트, 벤더 릴리스 추적 (본인 것만 보임) |
| **회원 관리** | 관리자만 보이는 메뉴. 사용자 역할(user/admin) 변경 |
| **📱 모바일 설치** | PC 화면에서 QR 코드를 띄워 휴대폰에 바로 설치 |

---

## 2. 어떻게 동작하나요

```
 [PC 브라우저]          [휴대폰 (홈 화면 앱)]
       │                        │
       └──────────┬─────────────┘
                  │  https://<프로젝트ID>.web.app
                  ▼
        ┌──────────────────────┐
        │   Firebase Hosting   │  ← 화면 파일(HTML/CSS/JS)만 전달
        └──────────────────────┘
                  │  브라우저가 직접 접속
        ┌─────────┴──────────┐
        ▼                    ▼
 ┌──────────────┐    ┌───────────────┐
 │ Firebase Auth│    │   Firestore   │  ← 모든 데이터. 실시간 동기화
 │ (Google 로그인)│    │ + 보안 규칙     │  ← 허용된 계정만 읽기/쓰기
 └──────────────┘    └───────────────┘
```

- **Firebase**는 Google이 제공하는 앱 개발 플랫폼입니다. 이 프로젝트는 그중 Hosting(웹 호스팅), Authentication(로그인), Firestore(데이터베이스) 세 가지를 씁니다. 개인·소규모 사용은 **무료 요금제(Spark)** 로 충분합니다.
- **Google Cloud**는 Firebase 프로젝트의 "뒷단"입니다. Firebase 프로젝트를 만들면 같은 이름의 Google Cloud 프로젝트가 자동으로 생깁니다. Google 로그인 화면(OAuth 동의 화면)과 Google 캘린더 연동 설정은 Google Cloud 콘솔에서 해야 합니다.
- 별도 서버(백엔드)가 없습니다. `main.py`(FastAPI)는 **내 PC에서 미리 보기용**으로만 씁니다.

---

## 3. 준비물

| 준비물 | 용도 | 확인 방법 |
|---|---|---|
| **Google 계정** | Firebase/Google Cloud 콘솔 사용, 앱 로그인 | — |
| **Node.js 18 이상** | Firebase CLI(배포 도구) 설치 | `node -v` |
| **Python 3.10 이상** | 내 PC에서 미리 보기, 관리 스크립트 실행 | `python --version` |
| **Git** | 코드 내려받기 | `git --version` |

설치가 안 되어 있다면:
- Node.js: https://nodejs.org (LTS 버전 설치)
- Python: https://www.python.org/downloads (Windows 설치 시 **"Add Python to PATH" 체크**)
- Git: https://git-scm.com/downloads

---

## 4. 설치 가이드 (처음 한 번)

> 아래 순서대로 진행하면 됩니다. 각 단계 끝에 **✅ 확인** 항목이 있으니 하나씩 체크하면서 넘어가세요.
> 화면 메뉴 이름은 Google이 가끔 바꿉니다. 이름이 조금 달라도 비슷한 메뉴를 찾으면 됩니다.

### Step 1. 코드 내려받기

```bash
git clone https://github.com/wanidev21/hwmanager.git
cd hwmanager
```

✅ 확인: `hwmanager` 폴더 안에 `frontend`, `firebase.json`, `firestore.rules` 가 보이면 OK.

---

### Step 2. Firebase 프로젝트 만들기

1. https://console.firebase.google.com 에 Google 계정으로 접속합니다.
2. **"프로젝트 만들기"(또는 "프로젝트 추가")** 를 누릅니다.
3. 프로젝트 이름을 입력합니다. 예: `hwmanager`
   - 아래에 자동으로 **프로젝트 ID**가 만들어집니다. 예: `hwmanager-593ba`
   - **이 프로젝트 ID를 메모해 두세요.** 웹 주소(`https://프로젝트ID.web.app`)와 설정 파일에 계속 쓰입니다.
4. Google 애널리틱스는 필요 없으니 **꺼도 됩니다.**
5. "프로젝트 만들기"를 누르고 1분 정도 기다립니다.

✅ 확인: Firebase 콘솔 왼쪽 위에 프로젝트 이름이 보이면 OK.

---

### Step 3. 웹 앱 등록하고 설정값 복사하기

Firebase에 "이 프로젝트를 웹에서 쓴다"고 알려 주고, 접속용 설정값을 받는 단계입니다.

1. Firebase 콘솔 첫 화면(프로젝트 개요)에서 **`</>` (웹) 아이콘**을 누릅니다.
2. 앱 닉네임을 입력합니다. 예: `hwmanager-web`
   - "Firebase 호스팅도 설정" 체크는 **안 해도 됩니다.** (Step 8에서 따로 합니다)
3. "앱 등록"을 누르면 아래와 같은 코드가 나옵니다.

   ```js
   const firebaseConfig = {
     apiKey: "AIza....",
     authDomain: "프로젝트ID.firebaseapp.com",
     projectId: "프로젝트ID",
     storageBucket: "프로젝트ID.firebasestorage.app",
     messagingSenderId: "1234567890",
     appId: "1:1234567890:web:abcdef..."
   };
   ```

4. 이 내용으로 **`frontend/firebase-config.js`** 파일을 덮어씁니다. (파일 안의 `const firebaseConfig = { ... };` 부분 전체를 교체)
5. 프로젝트 루트의 **`.firebaserc`** 파일에서 프로젝트 ID를 내 것으로 바꿉니다.

   ```json
   {
     "projects": {
       "default": "내-프로젝트-ID"
     }
   }
   ```

> 💡 나중에 다시 보려면: Firebase 콘솔 → ⚙️ **프로젝트 설정** → **일반** 탭 → 아래쪽 "내 앱"

✅ 확인: `frontend/firebase-config.js` 의 `projectId` 와 `.firebaserc` 의 `default` 가 같은 값이면 OK.

---

### Step 4. Google 로그인 켜기 (Firebase Authentication)

1. Firebase 콘솔 왼쪽 메뉴 → **빌드 → Authentication** → **시작하기**
2. **로그인 방법(Sign-in method)** 탭 → **Google** 선택
3. **사용 설정** 스위치를 켜고, **프로젝트 지원 이메일**에 내 Gmail을 선택 → **저장**

> ℹ️ 같은 화면의 **설정 → 승인된 도메인** 목록에 `localhost`, `프로젝트ID.firebaseapp.com`, `프로젝트ID.web.app` 이 있는지 확인하세요. 기본으로 들어가 있습니다. 다른 도메인에서 쓰려면 여기에 추가해야 합니다.

✅ 확인: 로그인 제공업체 목록에 **Google — 사용 설정됨** 이 보이면 OK.

---

### Step 5. 데이터베이스 만들기 (Cloud Firestore)

1. Firebase 콘솔 왼쪽 메뉴 → **빌드 → Firestore Database** → **데이터베이스 만들기**
2. 위치(리전): **`asia-northeast3 (서울)`** 을 권장합니다.
   - ⚠️ **위치는 나중에 바꿀 수 없습니다.**
3. 보안 모드: **프로덕션 모드**로 시작 → 만들기
   - 실제 보안 규칙은 Step 9에서 이 저장소의 `firestore.rules` 로 덮어씁니다.

✅ 확인: Firestore 화면에 빈 "데이터" 탭이 보이면 OK. (컬렉션은 앱을 쓰면 자동으로 생깁니다)

---

### Step 6. 로그인 허용 계정 지정하기

이 앱은 **허용 목록에 있는 Google 계정만** 쓸 수 있습니다. 내 Gmail 주소를 **두 파일** 모두에 넣어야 합니다.

**① `frontend/static/js/firebase-service.js`** — 화면에서 로그인 허용 여부를 판단

```js
const ALLOWED_EMAILS = ['내이메일@gmail.com'];
```

**② `firestore.rules`** — 데이터베이스가 실제로 접근을 허용하는 기준 (진짜 방어선)

```
request.auth.token.email in ['내이메일@gmail.com'];
```

- 이메일은 **소문자**로 적으세요.
- 여러 명이면 `['a@gmail.com', 'b@gmail.com']` 처럼 쉼표로 이어 씁니다.

✅ 확인: 두 파일에 같은 이메일 목록이 들어 있으면 OK.

---

### Step 7. Google Cloud 콘솔 설정 (중요)

Google 로그인 화면과 Google 캘린더 연동은 **Google Cloud 콘솔**에서 설정합니다.
Firebase 프로젝트를 만들 때 같은 이름의 Google Cloud 프로젝트가 이미 만들어져 있습니다.

1. https://console.cloud.google.com 에 **같은 Google 계정**으로 접속합니다.
2. 화면 맨 위의 **프로젝트 선택** 드롭다운에서 Firebase 프로젝트와 **같은 프로젝트**(예: `hwmanager-593ba`)를 고릅니다.
   - ⚠️ 다른 프로젝트가 선택된 채로 설정하면 적용되지 않습니다. 항상 맨 위 프로젝트 이름을 먼저 확인하세요.

#### 7-1. Google Calendar API 켜기

캘린더 화면에서 Google 캘린더 일정을 불러오려면 필요합니다.

1. 왼쪽 메뉴 → **API 및 서비스 → 라이브러리**
2. 검색창에 `Google Calendar API` → 선택 → **사용** 버튼

✅ 확인: 버튼이 "관리"로 바뀌면 OK.

#### 7-2. OAuth 동의 화면 설정 + 테스트 사용자 추가

Google 로그인 시 나오는 "OO 앱이 내 Google 계정에 접근하려고 합니다" 화면을 설정하는 곳입니다.

1. 왼쪽 메뉴 → **Google 인증 플랫폼(Google Auth Platform)**
   - 예전 화면에서는 **API 및 서비스 → OAuth 동의 화면** 입니다.
2. 처음이면 **시작하기**를 누르고 앱 이름(예: `HW Manager`), 지원 이메일을 입력합니다.
3. **대상(Audience)** 메뉴로 갑니다.
   - **사용자 유형: 외부(External)** 여야 합니다. (`내부`는 회사 Google Workspace 조직 계정 전용입니다. 개인 Gmail이면 외부를 선택하세요)
   - **게시 상태: 테스트** 그대로 둡니다.
4. 같은 화면 아래 **테스트 사용자 → + Add users** → 로그인할 Gmail 주소들을 추가 → **저장**

> ❓ **왜 "테스트" 상태로 두나요?**
> 이 앱은 Google 캘린더 읽기·쓰기 권한(민감한 권한)을 요청합니다. 누구나 쓰게 "프로덕션"으로 게시하려면 Google의 앱 심사가 필요합니다.
> 개인·소규모 팀이라면 **테스트 상태 + 테스트 사용자 등록(최대 100명)** 으로 충분하고 심사도 필요 없습니다.
> 대신 **테스트 사용자에 없는 계정은 로그인이 차단됩니다.** ("액세스 차단됨: … Google 인증 절차를 완료하지 않았습니다")

✅ 확인: 테스트 사용자 목록에 내 Gmail이 보이면 OK.

#### 7-3. 리디렉션 URI 등록

Google 로그인을 마친 뒤 **돌아올 주소**를 등록하는 단계입니다. 빠뜨리면 `redirect_uri_mismatch` 오류가 납니다.

1. 왼쪽 메뉴 → **API 및 서비스 → 사용자 인증 정보(Credentials)**
2. **OAuth 2.0 클라이언트 ID** 목록에서 **`Web client (auto created by Google Service)`** 를 누릅니다.
   - Firebase가 Google 로그인을 켤 때 자동으로 만든 클라이언트입니다.
   - 클라이언트가 여러 개라면: Firebase 콘솔 → Authentication → 로그인 방법 → Google → **웹 SDK 구성**의 "웹 클라이언트 ID"와 **같은 ID**를 고르세요.
3. **승인된 리디렉션 URI** 에 아래 **두 줄이 모두** 있어야 합니다. 없는 줄은 **+ URI 추가**로 **새 줄에** 추가합니다.

   ```
   https://프로젝트ID.firebaseapp.com/__/auth/handler
   https://프로젝트ID.web.app/__/auth/handler
   ```

   - ⚠️ 기존 줄을 **고쳐 쓰지 말고 새 줄로 추가**하세요. 둘 중 하나라도 빠지면 PC 또는 휴대폰 한쪽에서 로그인이 안 됩니다.
   - PC(내 PC 미리 보기 포함)는 `firebaseapp.com` 주소를, 배포된 사이트·휴대폰은 `web.app` 주소를 씁니다.
4. 맨 아래 **저장**. 반영까지 **5분~몇 시간** 걸릴 수 있습니다.

✅ 확인: 승인된 리디렉션 URI에 두 줄이 모두 보이면 OK.

---

### Step 8. Firebase CLI 설치하고 로그인하기

Firebase CLI는 터미널에서 배포를 하는 도구입니다.

```bash
npm install -g firebase-tools
firebase login
```

- `firebase login` 을 실행하면 브라우저가 열립니다. **Firebase 프로젝트를 만든 Google 계정**으로 로그인하고 허용합니다.
- "Allow Firebase to collect CLI usage…?" 질문에는 `n` 을 입력해도 됩니다.
- Windows에서 터미널 프로그램 안의 셸(예: 에디터 내장 터미널)에서 질문 입력이 막히면, **새 PowerShell 창**을 열어서 실행하세요.

확인:

```bash
firebase login:list        # "Logged in as 내이메일@gmail.com" 이 나오면 OK
firebase projects:list     # 내 프로젝트 ID가 목록에 보이면 OK
```

---

### Step 9. 보안 규칙 배포하기

Step 6에서 수정한 `firestore.rules` 를 Firestore에 적용합니다.

```bash
firebase deploy --only firestore:rules
```

> 다른 방법: Firebase 콘솔 → Firestore Database → **규칙** 탭에 `firestore.rules` 내용을 그대로 붙여 넣고 **게시**해도 됩니다.

✅ 확인: `Deploy complete!` 가 나오거나, 콘솔 규칙 탭에 내 이메일이 들어간 규칙이 보이면 OK.

---

### Step 10. 웹사이트 배포하기 (Firebase Hosting)

```bash
firebase deploy --only hosting
```

끝나면 아래처럼 주소가 나옵니다.

```
✔  Deploy complete!
Hosting URL: https://프로젝트ID.web.app
```

✅ 확인: 그 주소를 브라우저로 열어 로그인 화면이 보이면 OK.

---

### Step 11. 첫 로그인 + 관리자 지정

1. `https://프로젝트ID.web.app` 에 접속 → **Google로 로그인** → 허용 목록에 넣은 계정 선택
2. 처음 로그인하면 일반 사용자(`user`)로 등록됩니다. **관리자(`admin`)로 올리려면** 아래 스크립트를 실행합니다.

**① 서비스 계정 키 받기** (관리 스크립트 전용 비밀 키)

1. Firebase 콘솔 → ⚙️ **프로젝트 설정** → **서비스 계정** 탭
2. **새 비공개 키 생성** → JSON 파일 다운로드
3. 파일 이름을 **`firebase-credentials.json`** 으로 바꿔서 **프로젝트 루트**(README.md와 같은 폴더)에 둡니다.

> 🔒 이 파일은 데이터베이스 전체 관리 권한을 가진 열쇠입니다. **절대 GitHub에 올리거나 남에게 보내지 마세요.** (`.gitignore` 에 이미 등록되어 있습니다)

**② 관리자 지정 실행**

```bash
pip install -r requirements.txt
python scripts/set_admin.py 내이메일@gmail.com
```

`… -> role: admin` 이 나오면 완료입니다. 앱을 새로고침하면 사이드바에 **회원 관리** 메뉴가 나타납니다.

---

### Step 12. (도메인이 바뀐 경우만) 설치용 QR 코드 다시 만들기

PC 사이드바의 **📱 모바일 설치** QR 코드는 `frontend/static/icons/install-qr.svg` 이미지입니다.
현재 이 저장소의 QR은 `https://hwmanager-593ba.web.app` 을 가리키므로, **내 프로젝트 주소로 다시 만들어야** 합니다.

```bash
pip install segno
python -c "import segno; segno.make('https://내-프로젝트-ID.web.app', error='m').save('frontend/static/icons/install-qr.svg', scale=8, border=2, dark='#1a1a1a', light='#ffffff', xmldecl=False, omitsize=True)"
firebase deploy --only hosting
```

`frontend/index.html` 의 QR 아래 주소 문구(`hwmanager-593ba.web.app`)도 내 주소로 바꿔 주세요.

🎉 **설치 끝!**

---

## 5. 사용 방법

### 5-1. PC에서 쓰기

브라우저(Chrome·Edge·Safari 등)로 `https://프로젝트ID.web.app` 에 접속해 Google로 로그인합니다.
왼쪽 사이드바에서 메뉴를 고르면 됩니다.

- **30분 동안 아무 조작이 없으면 자동 로그아웃**됩니다. (5분 전에 경고 표시)
- 사이드바 아래쪽(내 이름 옆) 🌙 버튼으로 다크 모드를 켤 수 있습니다. 로그아웃은 그 옆 ↩ 버튼입니다. (휴대폰은 왼쪽 위 ☰ 메뉴를 열면 보입니다)

### 5-2. 휴대폰에 설치하기 (아이폰·안드로이드 공통)

앱스토어 없이 "홈 화면에 추가" 방식으로 설치합니다. 설치하면 주소창 없이 일반 앱처럼 열립니다.

**가장 쉬운 방법 — QR 코드**
1. PC에서 사이드바 맨 아래 **📱 모바일 설치** 를 누릅니다.
2. 휴대폰 **카메라**로 QR 코드를 비추고, 화면에 뜨는 링크를 누릅니다.

**아이폰**
1. 반드시 **Safari** 로 엽니다. (Chrome 앱에서는 홈 화면 추가가 제한됩니다)
2. 화면 아래 **공유 버튼(□↑)** → **홈 화면에 추가** → 추가

**안드로이드 (갤럭시 등)**
1. **Chrome** 으로 엽니다.
2. 오른쪽 위 **⋮** → **앱 설치** (또는 **홈 화면에 추가**) → **설치**
   - "설치"와 "바로가기 만들기" 중 고르라면 **설치**
   - 삼성 인터넷: 아래 **≡** → **현재 페이지 추가** → **홈 화면**

설치 후에는 홈 화면의 **HW Manager** 아이콘으로 실행합니다.

> ⚠️ **카카오톡·문자 등에서 링크를 눌러 열면** 그 앱 안의 브라우저로 열려서 Google 로그인이 차단됩니다. QR 코드나 Chrome/Safari 주소창으로 직접 여세요.

### 5-3. 화면별 사용법

**고객사·자산**
- 왼쪽에서 고객사를 고르면 → 오른쪽에 프로젝트 목록 → 프로젝트를 고르면 장비 목록이 나옵니다.
- 장비는 CSV 파일로 한꺼번에 등록할 수 있습니다. (장비 목록 화면의 CSV 가져오기)
- 고객사를 삭제하면 그 아래 프로젝트·장비도 함께 삭제됩니다.

**납품확인서**
- **+ 새 납품확인서** → 고객사(목록 선택 또는 "직접 입력 전환"), 프로젝트명, 납품일, 문서번호 입력
- **+ 행 추가** 로 품목 입력 (품목명은 이전에 입력한 값이 자동완성으로 뜹니다). 품목명이 빈 행은 저장되지 않습니다.
- 공급자·인수자 서명란에 마우스나 손가락으로 서명
- **👁 미리보기** 로 A4 결과물 확인 → **저장** 또는 **✓ 완료 처리**
- 목록에서 행을 누르면 미리보기가 열립니다. PC에서는 **수정·인쇄**도 할 수 있습니다. (인쇄 창에서 "PDF로 저장" 가능)
- 휴대폰에서는 목록 → 미리보기 **조회 전용**입니다.

**장애 티켓**
- **+ 티켓 등록** → 제목, 고객사, 우선순위, 담당자, 증상 입력
- 목록에서 티켓을 누르면 오른쪽(휴대폰은 아래)에 상세 정보와 **상태 변경** 버튼이 나옵니다.
- **완료**로 바꾸면 완료일이 자동 기록됩니다.
- 위쪽 숫자 카드(전체/접수/진행중/보류/완료)를 누르면 해당 상태만 걸러 봅니다.
- 휴대폰에서 표가 넓으면 **옆으로 밀어서** 나머지 칸을 봅니다.

**워런티 현황**
- 프로젝트의 워런티 만료일(고객사·자산 → 프로젝트에서 입력)을 기준으로 남은 일수를 보여 줍니다.
- 만료(빨강), 30일 이내(빨강), 90일 이내(주황) 순으로 표시됩니다.

**캘린더**
- 날짜를 눌러 일정을 추가합니다.
- 저장 위치로 **HW Manager(앱 전용)** 또는 **내 Google 캘린더**를 고를 수 있습니다.
- Google 캘린더 일정은 5분마다 자동으로 다시 불러옵니다.
- "Google 캘린더 미연결"이 보이면 옆의 **다시 연결** 을 누르세요. (로그인 후 약 1시간이 지나면 Google 연결이 만료됩니다)

**지식베이스 / 기술 학습**
- **본인이 작성한 것만** 보입니다. (다른 사용자와 공유되지 않음)
- 지식베이스: 장애 증상·원인·조치 순서를 정리하고 키워드로 검색합니다.
- 기술 학습: 도메인(예: GPU) → 토픽(예: NVLink) 진행 상태를 동그라미를 눌러 바꿉니다(미착수 → 진행중 → 완료). 노트와 벤더 릴리스도 기록합니다.

**회원 관리** (관리자만)
- 로그인한 적이 있는 사용자 목록과 역할(user/admin)을 바꿉니다.

### 5-4. 여러 기기에서 동시에 쓰기

- PC와 휴대폰, 또는 여러 사람이 동시에 열어 두어도 됩니다. 한쪽에서 저장·수정·삭제하면 **다른 기기 화면에 1초 안에** 반영됩니다.
- 다른 기기에서 지운 항목을 보고 있었다면 상세 창이 자동으로 닫힙니다.
- 한 번 본 데이터는 기기에 임시 저장되어 다음에 더 빨리 열립니다. (로그아웃하면 지워집니다)

---

## 6. 사용자 추가하기

새 사람이 쓰려면 **세 곳**에 그 사람의 Gmail을 추가해야 합니다.

| # | 위치 | 하는 일 | 빠뜨리면 |
|---|---|---|---|
| 1 | `frontend/static/js/firebase-service.js` 의 `ALLOWED_EMAILS` | 화면에서 로그인 허용 | "등록되지 않은 계정입니다" |
| 2 | `firestore.rules` 의 `allowed()` | 데이터 접근 허용 | 로그인은 되지만 데이터가 안 보임 |
| 3 | Google Cloud 콘솔 → Google 인증 플랫폼 → 대상 → **테스트 사용자** | Google 로그인 허용 | "액세스 차단됨: … 인증 절차를 완료하지 않았습니다" |

수정한 뒤 배포합니다.

```bash
firebase deploy --only hosting,firestore:rules
```

관리자로 만들려면 그 사람이 한 번 로그인한 뒤:

```bash
python scripts/set_admin.py 그사람@gmail.com
```

---

## 7. 코드 수정 후 다시 배포하기

```bash
firebase deploy --only hosting            # 화면(frontend 폴더)만
firebase deploy --only firestore:rules    # 보안 규칙만
firebase deploy --only hosting,firestore:rules   # 둘 다
```

- 배포하면 PC는 새로고침, 휴대폰 앱은 **완전히 종료했다가 다시 열면** 새 버전이 적용됩니다.
- 잘못 배포했다면 Firebase 콘솔 → Hosting → 출시 기록에서 이전 버전으로 **롤백**할 수 있습니다.

---

## 8. 로컬에서 개발하기

배포 전에 내 PC에서 미리 확인할 때 씁니다. (데이터는 실제 Firestore를 그대로 사용합니다)

```bash
pip install -r requirements.txt
python -m uvicorn main:app --host 0.0.0.0 --port 8471 --reload
```

브라우저에서 http://localhost:8471 접속.

- 내 PC 미리 보기는 **PC 브라우저에서만** 로그인됩니다. 휴대폰에서 PC의 IP 주소로 접속하면 Google 로그인이 막히므로, 휴대폰 테스트는 배포된 주소나 아래 미리보기 채널을 쓰세요.

```bash
firebase hosting:channel:deploy test   # 임시 미리보기 주소 발급 (실서비스에 영향 없음)
```

> 미리보기 채널 주소(`프로젝트ID--test-xxxx.web.app`)에서 휴대폰 로그인을 하려면, 그 주소의 `/__/auth/handler` 도 Step 7-3의 리디렉션 URI에 추가해야 합니다.

**코드 작성 규칙 (중요)**
- 화면에 사용자 입력값을 넣을 때는 반드시 `${FS.esc(값)}` 으로 감쌉니다. (`<bond0>` 같은 표기가 사라지는 것 방지)
- 목록 데이터는 `FS.watch()` 로 실시간 구독합니다. 페이지를 옮기면 자동으로 해제됩니다.
- `pages/*.html` 은 완전한 HTML이 아니라 `index.html` 에 끼워 넣는 조각입니다. Firebase 스크립트를 넣지 마세요.

---

## 9. 관리 스크립트

모두 프로젝트 루트에 `firebase-credentials.json`(Step 11)이 있어야 실행됩니다.
스크립트는 보안 규칙을 거치지 않고 데이터베이스를 직접 수정하므로 **신중하게** 사용하세요.

| 명령 | 하는 일 |
|---|---|
| `python scripts/set_admin.py <이메일>` | 관리자로 지정 (`--role user` 를 붙이면 해제) |
| `python scripts/reassign_owner.py <원래이메일> <새이메일>` | 지식베이스·기술 학습·캘린더 등 **개인 데이터의 주인을 옮김**. 기본은 미리보기, 끝에 `--execute` 를 붙여야 실제 변경 |
| `python scripts/seed_data.py` 등 `seed_*`, `test_*` | 개발 초기에 쓰던 **테스트 데이터 생성용**. 내 프로젝트에서 쓰려면 파일 안의 프로젝트 ID·키를 먼저 확인하세요 |
| `python scripts/reset_data.py` | ⚠️ 데이터 초기화. 실행 전 반드시 내용 확인 |

---

## 10. 문제 해결 (자주 만나는 오류)

### "액세스 차단됨: 프로젝트ID.firebaseapp.com은(는) Google 인증 절차를 완료하지 않았습니다"
→ 로그인하려는 Gmail이 **OAuth 테스트 사용자**에 없습니다. [Step 7-2](#7-2-oauth-동의-화면-설정--테스트-사용자-추가)에서 추가하세요.

### "400 오류: redirect_uri_mismatch"
→ 로그인 후 돌아올 주소가 등록되지 않았습니다. 오류 화면의 **오류 세부정보**를 누르면 `redirect_uri=...` 값이 보입니다. 그 주소를 [Step 7-3](#7-3-리디렉션-uri-등록)의 승인된 리디렉션 URI에 **새 줄로** 추가하세요. 반영까지 몇 분 걸릴 수 있습니다.

### "등록되지 않은 계정입니다. 관리자에게 문의하세요"
→ Google 로그인은 됐지만 앱의 허용 목록(`ALLOWED_EMAILS`)에 없는 계정입니다. 계정 선택 화면에서 다른 계정을 골랐는지 확인하거나, [6. 사용자 추가하기](#6-사용자-추가하기)를 따라 추가하세요.

### 로그인은 되는데 데이터가 하나도 안 보이거나 "데이터 동기화 오류: permission-denied"
→ `firestore.rules` 의 허용 이메일에 그 계정이 없거나, 규칙을 배포하지 않았습니다. `firebase deploy --only firestore:rules` 를 실행하세요.

### 휴대폰에서 Google 계정을 선택한 뒤 아무 반응이 없음
→ 앱을 **완전히 종료**(최근 앱 목록에서 위로 밀기)한 뒤 다시 열어 로그인하세요. 카카오톡 등 다른 앱 안에서 연 경우라면 Chrome/Safari로 직접 여세요.

### "요청이 Google 정책을 준수하지 않습니다" / `disallowed_useragent`
→ 카카오톡·문자 등 **앱 안의 브라우저**에서 열었습니다. Chrome(안드로이드) 또는 Safari(아이폰)에서 주소를 직접 열거나 QR 코드를 쓰세요.

### "팝업이 차단되었습니다"
→ PC 브라우저 주소창 오른쪽의 팝업 차단 아이콘을 눌러 이 사이트의 팝업을 허용하세요.

### 캘린더에 "Google 캘린더 미연결"
→ Google 연결은 로그인 후 약 1시간이 지나면 만료됩니다. **다시 연결** 버튼을 누르세요. 계속 실패하면 [Step 7-1](#7-1-google-calendar-api-켜기)의 Calendar API가 켜져 있는지 확인하세요.

### 배포했는데 휴대폰에 예전 화면이 나옴
→ 홈 화면 앱을 완전히 종료했다가 다시 여세요. 그래도 같으면 브라우저에서 사이트 데이터를 지우고 다시 설치하세요.

### `firebase login` 후에도 "No authorized accounts"
→ 로그인 과정이 중간에 멈췄을 수 있습니다. **새 PowerShell(또는 터미널) 창**에서 `firebase login` 을 다시 실행하고 `Success! Logged in as …` 가 나오는지 확인하세요.

---

## 11. 보안 참고 사항

- **`frontend/firebase-config.js` 의 `apiKey` 는 공개되어도 괜찮습니다.** Firebase 웹 설정값은 원래 브라우저에 그대로 전달되는 값이며, 비밀번호가 아닙니다. 데이터 보호는 **Firestore 보안 규칙**(`firestore.rules`)이 담당합니다.
- **`firebase-credentials.json`(서비스 계정 키)은 절대 공개하면 안 됩니다.** 실수로 올렸다면 즉시 Firebase 콘솔 → 프로젝트 설정 → 서비스 계정 → Google Cloud 콘솔에서 해당 키를 **삭제**하고 새로 발급하세요.
- 현재 보안 규칙 요약
  - 허용 목록에 있는 계정만 읽기·쓰기 가능. 그 외 계정은 로그인하더라도 데이터에 접근 불가
  - 지식베이스·기술 학습·캘린더 일정은 **본인 데이터만** 접근 가능
  - 사용자 역할(`role`) 변경은 관리자만 가능
  - 규칙에 없는 컬렉션은 모두 차단

---

## 12. 프로젝트 구조

```
hwmanager/
├── README.md
├── firebase.json            # Firebase Hosting·규칙 배포 설정 (public = frontend)
├── .firebaserc              # 배포 대상 Firebase 프로젝트 ID
├── firestore.rules          # Firestore 보안 규칙 (허용 이메일 목록 포함)
├── main.py                  # 로컬 미리 보기 서버 (FastAPI)
├── requirements.txt
├── Dockerfile, docker-compose.yml   # (선택) 자체 서버에 올릴 때
├── scripts/                 # 관리 스크립트 (firebase-credentials.json 필요)
└── frontend/                # 배포되는 화면 전체
    ├── index.html           # 앱 셸 (사이드바 + 페이지 로더)
    ├── login.html
    ├── firebase-config.js   # Firebase 웹 설정값 (Step 3)
    ├── manifest.json, sw.js # 휴대폰 설치(PWA)·오프라인 캐시
    ├── static/
    │   ├── css/app.css
    │   ├── js/firebase-service.js   # 로그인·데이터 접근 공통 코드 (허용 이메일 목록 포함)
    │   └── icons/                   # 앱 아이콘, 설치용 QR
    └── pages/               # 메뉴별 화면 (index.html 에 끼워 넣는 조각)
        ├── overview.html  customers.html  delivery.html  tickets.html
        ├── warranty.html  calendar.html   kb.html        tech.html
        └── users.html     infra.html
```

### Firestore 컬렉션

| 컬렉션 | 내용 | 공유 범위 |
|---|---|---|
| `customers` → `projects` → `assets` | 고객사 → 프로젝트(워런티) → 장비 | 허용 계정 전체 |
| `tickets` | 장애 티켓 | 허용 계정 전체 |
| `delivery_notes`, `delivery_items` | 납품확인서, 품목 | 허용 계정 전체 |
| `internal_assets` | 사내 장비 | 허용 계정 전체 |
| `kb_articles` | 지식베이스 | 본인만 |
| `tech_domains`, `tech_topics`, `tech_notes`, `releases` | 기술 학습 | 본인만 |
| `calendar_events` | 앱 전용 일정 | 본인만 |
| `users` | 사용자 정보·역할 | 허용 계정 전체 (역할 변경은 관리자만) |

### 기술 스택

- 화면: HTML / CSS / JavaScript (빌드 도구 없음), Firebase JS SDK 10.8 (compat)
- 데이터·인증·호스팅: Firebase (Cloud Firestore, Authentication, Hosting)
- 휴대폰: PWA (manifest + Service Worker)
- 로컬 미리 보기·관리 스크립트: Python (FastAPI, firebase-admin)
