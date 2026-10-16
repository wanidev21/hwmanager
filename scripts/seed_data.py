"""
HW Manager Firestore 테스트 데이터 시드 스크립트

인증 방식 (우선순위):
  1. firebase-credentials.json (서비스 계정 키 파일)
  2. 환경변수 FIREBASE_EMAIL + FIREBASE_PASSWORD (이메일/비밀번호)
  3. 인터랙티브 이메일/비밀번호 입력

실행: docker compose exec app python scripts/seed_data.py
     docker compose exec -e FIREBASE_EMAIL=... -e FIREBASE_PASSWORD=... app python scripts/seed_data.py
"""

import json
import os
import sys
import uuid
import getpass
from datetime import datetime, timedelta, date

try:
    import requests
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests", "-q"])
    import requests

# ── Firebase 설정 ──
API_KEY = "AIzaSyA46Gdc79dKkLRntGe8qlv_d9kpb2h25x4"
PROJECT_ID = "hwmanager-593ba"
FIRESTORE_BASE = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents"
CRED_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "firebase-credentials.json")


def get_token_admin():
    """firebase-admin SDK로 Firestore 직접 접근 (서비스 계정 키 사용)"""
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore as fs_admin
    except ImportError:
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "firebase-admin", "-q"])
        import firebase_admin
        from firebase_admin import credentials, firestore as fs_admin

    if not firebase_admin._apps:
        cred = credentials.Certificate(CRED_PATH)
        firebase_admin.initialize_app(cred)
    return fs_admin.client(), "admin"


def get_token_email(email, password):
    """이메일/비밀번호로 Firebase Auth 토큰 획득"""
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={API_KEY}"
    resp = requests.post(url, json={"email": email, "password": password, "returnSecureToken": True})
    data = resp.json()
    if "idToken" not in data:
        err = data.get("error", {}).get("message", "알 수 없는 오류")
        print(f"❌ 로그인 실패: {err}")
        sys.exit(1)
    print(f"✓ Firebase Auth 로그인 성공 ({email})")
    return data["idToken"], "rest"


# ── 인증 모드 결정 ──
USE_ADMIN = False
ID_TOKEN = None
DB_CLIENT = None

if os.path.isfile(CRED_PATH):
    print("✓ 서비스 계정 키 파일 사용")
    try:
        DB_CLIENT, _ = get_token_admin()
        USE_ADMIN = True
    except Exception as e:
        print(f"  ⚠ Admin SDK 실패: {e}")

if not USE_ADMIN:
    email = os.environ.get("FIREBASE_EMAIL", "")
    password = os.environ.get("FIREBASE_PASSWORD", "")
    if not email:
        print("\n서비스 계정 키 파일이 없습니다.")
        print("Firebase 이메일/비밀번호로 로그인합니다.")
        email = input("  이메일: ").strip()
        password = getpass.getpass("  비밀번호: ")
    ID_TOKEN, _ = get_token_email(email, password)

HEADERS = {"Authorization": f"Bearer {ID_TOKEN}", "Content-Type": "application/json"} if ID_TOKEN else {}


# ── Firestore 값 타입 변환 (REST API용) ──
def fv(val):
    if val is None:
        return {"nullValue": None}
    if isinstance(val, bool):
        return {"booleanValue": val}
    if isinstance(val, int):
        return {"integerValue": str(val)}
    if isinstance(val, float):
        return {"doubleValue": val}
    if isinstance(val, datetime):
        return {"timestampValue": val.strftime("%Y-%m-%dT%H:%M:%SZ")}
    if isinstance(val, list):
        return {"arrayValue": {"values": [fv(v) for v in val]}}
    if isinstance(val, dict):
        return {"mapValue": {"fields": {k: fv(v) for k, v in val.items()}}}
    return {"stringValue": str(val)}


# ── CRUD (Admin SDK 또는 REST API) ──
def add(collection: str, data: dict) -> str:
    now = datetime.utcnow()
    doc_data = {**data, "created_at": now, "updated_at": now}
    doc_id = str(uuid.uuid4())

    if USE_ADMIN:
        from google.cloud.firestore_v1 import SERVER_TIMESTAMP
        doc_data["created_at"] = now
        doc_data["updated_at"] = now
        DB_CLIENT.collection(collection).document(doc_id).set(doc_data)
    else:
        url = f"{FIRESTORE_BASE}/{collection}/{doc_id}"
        body = {"fields": {k: fv(v) for k, v in doc_data.items()}}
        resp = requests.patch(url, headers=HEADERS, json=body)
        if resp.status_code not in (200, 201):
            print(f"  ⚠ 쓰기 실패 ({collection}): {resp.status_code} {resp.text[:200]}")
    return doc_id


def delete_all(collection: str) -> int:
    if USE_ADMIN:
        docs = list(DB_CLIENT.collection(collection).stream())
        batch = DB_CLIENT.batch()
        count = 0
        for doc in docs:
            batch.delete(doc.reference)
            count += 1
            if count % 500 == 0:
                batch.commit()
                batch = DB_CLIENT.batch()
        if count % 500 != 0:
            batch.commit()
        return count
    else:
        url = f"{FIRESTORE_BASE}/{collection}"
        resp = requests.get(url, headers=HEADERS, params={"pageSize": 300})
        if resp.status_code != 200:
            return 0
        docs = resp.json().get("documents", [])
        for doc in docs:
            requests.delete(f"https://firestore.googleapis.com/v1/{doc['name']}", headers=HEADERS)
        return len(docs)


# ── 기존 데이터 초기화 ──
COLLECTIONS = [
    "customers", "assets", "tickets", "kb_articles",
    "internal_assets", "tech_domains", "tech_topics",
    "tech_notes", "releases", "delivery_notes", "delivery_items",
]
print("\n기존 데이터 삭제 중...")
for col in COLLECTIONS:
    n = delete_all(col)
    if n:
        print(f"  - {col}: {n}개 삭제")

today = date(2026, 5, 19)
def d(days): return (today + timedelta(days=days)).isoformat()

# ════════════════════════════════════════════
# 1. 고객사 5개
# ════════════════════════════════════════════
print("\n[1/7] 고객사 생성...")
customers_raw = [
    dict(name="(주)카카오엔터프라이즈", contact="이준혁", phone="02-6210-0001",
         email="junhyuk.lee@kakaoenterprise.com", address="경기도 성남시 분당구 판교역로 166",
         memo="SLA: 4시간 내 현장 출동. GPU 클러스터 40노드 운영 중.", sla_tier="Premium", fleet_size=40),
    dict(name="삼성SDS", contact="박민수", phone="02-6484-0002",
         email="minsoo.park@samsungsds.com", address="서울특별시 송파구 올림픽로35길 125",
         memo="SLA: 2시간 내 원격 대응, 8시간 내 현장. 연간 유지보수 계약.", sla_tier="Enterprise", fleet_size=85),
    dict(name="LG CNS", contact="김태영", phone="02-2099-3000",
         email="taeyoung.kim@lgcns.com", address="서울특별시 마포구 마젤란21로 18",
         memo="SLA: 4시간 내 원격, 익일 현장. HPE 서버 주력.", sla_tier="Standard", fleet_size=32),
    dict(name="네이버클라우드", contact="정수아", phone="031-784-1000",
         email="sua.jung@naver.com", address="경기도 성남시 분당구 불정로 6",
         memo="SLA: 1시간 내 원격 대응. DGX A100 클러스터 운영.", sla_tier="Platinum", fleet_size=60),
    dict(name="SK텔레콤 AI&CO", contact="한동욱", phone="02-6100-2114",
         email="dongwook.han@sktai.com", address="서울특별시 중구 을지로 65",
         memo="SLA: 2시간 내 원격. AMD Instinct GPU 서버 테스트 환경.", sla_tier="Premium", fleet_size=18),
]
cust_ids = {}
for c in customers_raw:
    cust_ids[c["name"]] = add("customers", c)
    print(f"  + {c['name']}")

# ════════════════════════════════════════════
# 2. 장비 20대
# ════════════════════════════════════════════
print("\n[2/7] 장비 생성...")
assets_data = [
    # 카카오엔터프라이즈 (6대)
    dict(customer_id=cust_ids["(주)카카오엔터프라이즈"], name="DGX-A100-001", model="DGX A100 80GB", vendor="NVIDIA",
         serial="NV-DGX-20240101-001", location="판교IDC A동 3층 Rack-01", status="운영중",
         ip_address="10.10.1.11", warranty_expire=d(410), memo="CUDA 12.4, Driver 550.54"),
    dict(customer_id=cust_ids["(주)카카오엔터프라이즈"], name="DGX-A100-002", model="DGX A100 80GB", vendor="NVIDIA",
         serial="NV-DGX-20240101-002", location="판교IDC A동 3층 Rack-01", status="운영중",
         ip_address="10.10.1.12", warranty_expire=d(380), memo="NVLink 구성. DGX-A100-001과 NVSwitch 연결"),
    dict(customer_id=cust_ids["(주)카카오엔터프라이즈"], name="DGX-A100-003", model="DGX A100 80GB", vendor="NVIDIA",
         serial="NV-DGX-20240102-003", location="판교IDC A동 3층 Rack-02", status="장애",
         ip_address="10.10.1.13", warranty_expire=d(15), memo="GPU#3 ECC 오류 발생. 교체 부품 대기 중"),
    dict(customer_id=cust_ids["(주)카카오엔터프라이즈"], name="PowerEdge-R750xa-001", model="PowerEdge R750xa", vendor="Dell",
         serial="DELL-R750-20230515-001", location="판교IDC A동 3층 Rack-03", status="운영중",
         ip_address="10.10.1.21", warranty_expire=d(-45), memo="워런티 만료됨. 연장 계약 검토 필요"),
    dict(customer_id=cust_ids["(주)카카오엔터프라이즈"], name="PowerEdge-R750xa-002", model="PowerEdge R750xa", vendor="Dell",
         serial="DELL-R750-20230515-002", location="판교IDC A동 3층 Rack-03", status="운영중",
         ip_address="10.10.1.22", warranty_expire=d(60), memo="PERC H755 RAID 컨트롤러 장착"),
    dict(customer_id=cust_ids["(주)카카오엔터프라이즈"], name="ProLiant-DL380-001", model="ProLiant DL380 Gen10", vendor="HPE",
         serial="HPE-DL380-20220801-001", location="판교IDC A동 3층 Rack-04", status="점검중",
         ip_address="10.10.1.31", warranty_expire=d(200), memo="iLO 펌웨어 업그레이드 중"),
    # 삼성SDS (5대)
    dict(customer_id=cust_ids["삼성SDS"], name="ThinkSystem-SR650-001", model="ThinkSystem SR650 V2", vendor="Lenovo",
         serial="LNV-SR650-20231201-001", location="가산IDC B동 5층 Rack-10", status="운영중",
         ip_address="10.20.1.11", warranty_expire=d(540), memo="XClarity Controller 설정 완료"),
    dict(customer_id=cust_ids["삼성SDS"], name="ThinkSystem-SR650-002", model="ThinkSystem SR650 V2", vendor="Lenovo",
         serial="LNV-SR650-20231201-002", location="가산IDC B동 5층 Rack-10", status="운영중",
         ip_address="10.20.1.12", warranty_expire=d(510), memo="HA 클러스터 구성 노드 2"),
    dict(customer_id=cust_ids["삼성SDS"], name="PowerEdge-R860-001", model="PowerEdge R860", vendor="Dell",
         serial="DELL-R860-20240301-001", location="가산IDC B동 5층 Rack-11", status="운영중",
         ip_address="10.20.1.21", warranty_expire=d(680), memo="4S Xeon Scalable. 메모리 3TB"),
    dict(customer_id=cust_ids["삼성SDS"], name="PowerEdge-R860-002", model="PowerEdge R860", vendor="Dell",
         serial="DELL-R860-20240301-002", location="가산IDC B동 5층 Rack-11", status="운영중",
         ip_address="10.20.1.22", warranty_expire=d(660), memo="오라클 DB 전용 서버"),
    dict(customer_id=cust_ids["삼성SDS"], name="ProLiant-DL560-001", model="ProLiant DL560 Gen10", vendor="HPE",
         serial="HPE-DL560-20230101-001", location="가산IDC B동 5층 Rack-12", status="운영중",
         ip_address="10.20.1.31", warranty_expire=d(25), memo="iLO5 Advanced 라이선스. 워런티 임박!"),
    # LG CNS (3대)
    dict(customer_id=cust_ids["LG CNS"], name="ProLiant-DL380-001", model="ProLiant DL380 Gen11", vendor="HPE",
         serial="HPE-DL380G11-20240601-001", location="마포IDC C동 2층 Rack-05", status="운영중",
         ip_address="10.30.1.11", warranty_expire=d(920), memo="Gen11 최신 구매. iLO6 펌웨어"),
    dict(customer_id=cust_ids["LG CNS"], name="ProLiant-DL360-001", model="ProLiant DL360 Gen10 Plus", vendor="HPE",
         serial="HPE-DL360-20220601-001", location="마포IDC C동 2층 Rack-05", status="운영중",
         ip_address="10.30.1.12", warranty_expire=d(-120), memo="워런티 만료. Care Pack 연장 필요"),
    dict(customer_id=cust_ids["LG CNS"], name="ThinkSystem-SR860-001", model="ThinkSystem SR860 V2", vendor="Lenovo",
         serial="LNV-SR860-20231001-001", location="마포IDC C동 2층 Rack-06", status="운영중",
         ip_address="10.30.1.21", warranty_expire=d(440), memo="4S 고성능 서버. SAP HANA 전용"),
    # 네이버클라우드 (4대)
    dict(customer_id=cust_ids["네이버클라우드"], name="DGX-H100-001", model="DGX H100", vendor="NVIDIA",
         serial="NV-DGHX-20240901-001", location="춘천IDC D동 1층 Rack-01", status="운영중",
         ip_address="10.40.1.11", warranty_expire=d(1100), memo="H100 SXM5 80GB x8. NVLink 4.0 구성"),
    dict(customer_id=cust_ids["네이버클라우드"], name="DGX-H100-002", model="DGX H100", vendor="NVIDIA",
         serial="NV-DGHX-20240901-002", location="춘천IDC D동 1층 Rack-01", status="운영중",
         ip_address="10.40.1.12", warranty_expire=d(1080), memo="LLM 파인튜닝 전용 노드"),
    dict(customer_id=cust_ids["네이버클라우드"], name="PowerEdge-R7625-001", model="PowerEdge R7625", vendor="Dell",
         serial="DELL-R7625-20240701-001", location="춘천IDC D동 1층 Rack-02", status="운영중",
         ip_address="10.40.1.21", warranty_expire=d(780), memo="AMD EPYC 9654 x2. 스토리지 서버"),
    dict(customer_id=cust_ids["네이버클라우드"], name="PowerEdge-R7625-002", model="PowerEdge R7625", vendor="Dell",
         serial="DELL-R7625-20240701-002", location="춘천IDC D동 1층 Rack-02", status="장애",
         ip_address="10.40.1.22", warranty_expire=d(760), memo="RAID 컨트롤러 오류. 교체 진행 중"),
    # SK텔레콤 (2대)
    dict(customer_id=cust_ids["SK텔레콤 AI&CO"], name="ProLiant-XL675d-001", model="ProLiant XL675d Gen10 Plus", vendor="HPE",
         serial="HPE-XL675-20230901-001", location="을지로IDC E동 3층 Rack-08", status="운영중",
         ip_address="10.50.1.11", warranty_expire=d(310), memo="AMD Instinct MI250X GPU 가속 서버"),
    dict(customer_id=cust_ids["SK텔레콤 AI&CO"], name="ProLiant-XL675d-002", model="ProLiant XL675d Gen10 Plus", vendor="HPE",
         serial="HPE-XL675-20230901-002", location="을지로IDC E동 3층 Rack-08", status="운영중",
         ip_address="10.50.1.12", warranty_expire=d(290), memo="ROCm 5.7 환경. PyTorch 학습 클러스터"),
]
for a in assets_data:
    add("assets", a)
    print(f"  + {a['name']} ({a['vendor']})")

# ════════════════════════════════════════════
# 3. 장애 티켓 10개
# ════════════════════════════════════════════
print("\n[3/7] 장애 티켓 생성...")
tickets_data = [
    dict(title="[P1] DGX-A100-003 GPU#3 ECC Uncorrectable Error 발생",
         customer_id=cust_ids["(주)카카오엔터프라이즈"], assignee="김정완", priority="긴급", status="진행중",
         symptom="GPU#3에서 반복적인 ECC Uncorrectable Error 발생. nvidia-smi에서 GPU 상태 N/A 표시. 해당 GPU가 학습 작업에서 제외됨.",
         action="1. nvidia-smi -q 로 GPU 상태 확인 - GPU#3 ECC Error 카운트 급증 확인\n2. dcgmi diag -r 3 실행 → GPU#3 메모리 테스트 실패\n3. 해당 GPU를 compute 작업에서 격리\n4. NVIDIA 케이스 오픈 (#CS-2024-051234)\n5. 교체 GPU 모듈 배송 대기 중 (ETA: 3일)"),
    dict(title="[P1] 네이버클라우드 PowerEdge-R7625-002 RAID 컨트롤러 오류",
         customer_id=cust_ids["네이버클라우드"], assignee="이상현", priority="긴급", status="진행중",
         symptom="PERC H965i RAID 컨트롤러가 감지되지 않음. 시스템 부팅 시 'No RAID Controller Found' 오류. 스토리지 접근 불가.",
         action="1. iDRAC에서 컨트롤러 상태 확인 → Fault 상태\n2. RAID 컨트롤러 PCI 슬롯 재장착 시도 → 증상 동일\n3. Dell 긴급 지원 접수 (케이스 #DS-2026-001122)\n4. 교체 컨트롤러 당일 출고 확정\n5. 데이터 보호를 위해 서버 종료 후 대기 중"),
    dict(title="[P2] 삼성SDS ProLiant DL560 iLO 접속 불가",
         customer_id=cust_ids["삼성SDS"], assignee="박지훈", priority="높음", status="접수",
         symptom="ProLiant-DL560-001의 iLO 웹 인터페이스 접속이 안 됨. ping은 응답하지만 HTTP/HTTPS 포트 타임아웃.",
         action="현장 방문 일정 조율 중 (2026-05-21 오전 예정)"),
    dict(title="[P2] 카카오 PowerEdge R750xa-002 팬 이상 경고",
         customer_id=cust_ids["(주)카카오엔터프라이즈"], assignee="김정완", priority="높음", status="완료",
         symptom="iDRAC에서 Fan 5, Fan 6 'RPM below lower critical threshold' 경고. 서버 내부 온도 상승 (CPU 75°C).",
         action="1. iDRAC 이벤트 로그 확인 → Fan 5,6 RPM이 임계값 이하\n2. 현장 방문 팬 물리 상태 점검 → 팬 블레이드 파손 확인\n3. 팬 어셈블리 2개 교체 (Dell 파트 0MV989)\n4. 교체 후 RPM 정상화 확인 (3,600 RPM)\n5. 24시간 모니터링 후 정상 확인 완료"),
    dict(title="[P2] LG CNS ProLiant DL360 메모리 모듈 장애",
         customer_id=cust_ids["LG CNS"], assignee="이상현", priority="높음", status="완료",
         symptom="POST 중 'Memory Error Detected in DIMM Slot 3A' 경고. 시스템이 4TB → 3.5TB 메모리로 축소 인식.",
         action="1. iLO 이벤트 로그에서 DIMM 3A Uncorrectable ECC Error 확인\n2. DIMM 재장착 → 증상 동일\n3. HPE DDR4 32GB RDIMM 교체 (파트 P06031-B21)\n4. memtest86 24시간 테스트 통과\n5. 정상 운영 복귀 확인"),
    dict(title="[P3] 삼성SDS ThinkSystem SR650-001 디스크 예측 실패 알림",
         customer_id=cust_ids["삼성SDS"], assignee="박지훈", priority="보통", status="진행중",
         symptom="XClarity Controller에서 SAS HDD 2번 디스크 'Predictive Failure' 알림. SMART 데이터에서 Reallocated Sector Count 급증.",
         action="1. SMART 데이터 분석 → Reallocated: 847, Pending: 23\n2. RAID 5 구성 확인 → 디스크 2번이 Degraded 상태\n3. Lenovo 파트 주문 완료 (7XB7A05926)\n4. 부품 입고 후 핫스왑 교체 예정 (2026-05-22)"),
    dict(title="[P3] 네이버클라우드 DGX H100-001 NVLink 성능 저하",
         customer_id=cust_ids["네이버클라우드"], assignee="김정완", priority="보통", status="보류",
         symptom="DGX H100-001에서 GPU 간 NVLink 대역폭이 예상치(900GB/s)의 60% 수준으로 측정됨. 멀티-GPU 학습 효율 급감.",
         action="1. nvidia-smi nvlink -s 로 상태 확인 → GPU 0-1 링크 일부 비활성\n2. dcgmi diag -r 4 실행 → NVLink 테스트 partial fail\n3. 시스템 재부팅 후 개선 여부 모니터링 중\n4. NVIDIA 엔지니어 원격 지원 일정 조율 중 (보류)"),
    dict(title="[P3] SK텔레콤 HPE ProLiant XL675d PSU 레던던시 경고",
         customer_id=cust_ids["SK텔레콤 AI&CO"], assignee="이상현", priority="보통", status="접수",
         symptom="PSU2 fault 표시. 현재 PSU1 단독 운영 중. 레던던시 상실 상태로 전력 이중화 미적용.",
         action="HPE 파트넘버 확인 중 (P21242-B21 예상). 부품 주문 예정."),
    dict(title="[P4] 카카오엔터프라이즈 ProLiant DL380 OS 업데이트 후 NIC 인식 불가",
         customer_id=cust_ids["(주)카카오엔터프라이즈"], assignee="박지훈", priority="낮음", status="완료",
         symptom="RHEL 9.3 커널 업데이트 후 10GbE NIC (Broadcom BCM57416) 인식 안됨.",
         action="1. dmesg에서 드라이버 바인딩 오류 확인 (bnxt_en 모듈)\n2. firmware-bnxt 패키지 재설치\n3. dracut 재생성 후 재부팅 → NIC 정상 인식\n4. KB 등록 완료"),
    dict(title="[P4] LG CNS ThinkSystem SR860 BMC 펌웨어 업그레이드 필요",
         customer_id=cust_ids["LG CNS"], assignee="박지훈", priority="낮음", status="접수",
         symptom="Lenovo XClarity에서 BMC 펌웨어 보안 취약점 알림 (CVE-2024-22102). 현재 버전 2.95, 권고 버전 3.10.",
         action="정기 점검 일정(2026-05-30)에 펌웨어 업그레이드 포함 예정."),
]
for t in tickets_data:
    add("tickets", t)
    print(f"  + [{t['priority']}] {t['title'][:48]}...")

# ════════════════════════════════════════════
# 4. KB 지식베이스 8개
# ════════════════════════════════════════════
print("\n[4/7] KB 지식베이스 생성...")
kb_data = [
    dict(title="NVIDIA GPU ECC Uncorrectable Error 대응 절차",
         symptom="nvidia-smi에서 ECC Error 카운트 급증 또는 GPU 상태 N/A 표시. DCGM에서 ECC DBE 알람 발생.",
         cause="GPU VRAM 셀 불량에 의한 하드웨어 ECC 에러. 열 스트레스, 과전류, 또는 제조 불량이 원인.",
         solution="1. nvidia-smi -q | grep -i ecc 로 에러 카운트 확인\n2. dcgmi diag -r 3 실행 → GPU 메모리 종합 테스트\n3. 에러 GPU 격리: CUDA_VISIBLE_DEVICES에서 제외\n4. 드라이버 재설치: rmmod nvidia; modprobe nvidia\n5. ECC 리셋 시도: nvidia-smi -e 0 → reboot → nvidia-smi -e 1\n6. 지속 시 하드웨어 교체 → 벤더 케이스 오픈",
         related_vendors=["NVIDIA"], keywords=["GPU", "ECC", "메모리", "DCGM", "nvidia-smi"]),
    dict(title="Dell iDRAC 접속 불가 시 복구 방법",
         symptom="iDRAC 웹 UI, SSH, IPMI 모두 응답 없음. ping은 되지만 포트 타임아웃. OS는 정상 운영.",
         cause="iDRAC 펌웨어 hang, 메모리 부족, 또는 네트워크 설정 오류.",
         solution="1. F2로 BIOS 진입 → iDRAC Settings에서 iDRAC 리셋\n2. racadm을 통한 리셋: racadm racreset\n3. 물리적 iDRAC 리셋 버튼 (서버 후면 핀 홀) 15초 누름\n4. Power cycling: OS shutdown → 전원 완전 차단 30초 → 재시작\n5. 펌웨어 업데이트 필요 시 Dell DSU 사용",
         related_vendors=["Dell"], keywords=["iDRAC", "원격관리", "BMC", "IPMI", "펌웨어"]),
    dict(title="HPE iLO 5 Advanced 설정 및 트러블슈팅",
         symptom="iLO 웹 UI 로그인 실패, 원격 콘솔 연결 오류, 팬/온도 센서 데이터 미표시.",
         cause="iLO 라이선스 만료, 인증서 오류, 네트워크 구성 문제, 또는 iLO 펌웨어 버그.",
         solution="1. iLO IP 브라우저 접속 → 기본 계정 admin/패스워드(라벨 확인)\n2. 네트워크 설정: Administration → Network → iLO Dedicated NIC\n3. iLO 리셋: Administration → Reset iLO\n4. 인증서 오류 시: Security → SSL Certificate → Generate Self-Signed\n5. 펌웨어 업데이트: Firmware & OS Software → Online Firmware Update",
         related_vendors=["HPE"], keywords=["iLO", "원격관리", "HPE", "펌웨어", "라이선스"]),
    dict(title="RAID 컨트롤러 Predictive Failure 디스크 교체 절차",
         symptom="RAID 관리 툴에서 특정 디스크 Predictive Failure 상태 표시. SMART 데이터에서 Reallocated Sector Count 증가.",
         cause="HDD/SSD의 물리적 노화, 불량 섹터 누적.",
         solution="1. SMART 데이터 확인: smartctl -a /dev/sdX\n2. RAID 상태 확인: MegaCLI -PDList -aAll | grep -i failure\n3. 동일 용량/속도/인터페이스 교체 디스크 준비\n4. 핫스왑 가능 여부 확인\n5. 디스크 교체 후 Rebuild 시작: MegaCLI -PDRbld -Start -PhysDrv[E:S] -aAll\n6. Rebuild 완료 후 전체 RAID Consistency Check 실행",
         related_vendors=["Dell", "HPE", "Lenovo"], keywords=["RAID", "부품교체", "HDD", "SSD", "SMART"]),
    dict(title="NVLink / NVSwitch 성능 저하 진단 방법",
         symptom="멀티-GPU 학습 속도 저하. nvidia-smi nvlink -s 에서 일부 링크 비활성. NCCL AllReduce 대역폭이 예상치 이하.",
         cause="NVLink 커넥터 접촉 불량, 드라이버/펌웨어 버그, 또는 BIOS 설정 문제.",
         solution="1. 링크 상태 확인: nvidia-smi nvlink -s\n2. DCGM 진단: dcgmi diag -r 4\n3. NCCL 테스트: nccl-tests로 AllReduce 대역폭 측정\n4. 시스템 재부팅으로 링크 재초기화\n5. 드라이버 재설치 (최신 버전으로 업그레이드)\n6. 지속 시 NVIDIA 기술 지원 접수",
         related_vendors=["NVIDIA"], keywords=["NVLink", "GPU", "NCCL", "성능", "멀티GPU"]),
    dict(title="Linux 커널 업데이트 후 NIC 드라이버 문제 해결",
         symptom="커널 업데이트 후 NIC 인식 안됨 또는 link down. dmesg에서 드라이버 바인딩 오류.",
         cause="커널 모듈과 firmware 버전 불일치. 새 커널의 드라이버 버그 또는 DKMS 모듈 재빌드 실패.",
         solution="1. dmesg | grep -i 'eth\\|nic\\|driver' 로 오류 메시지 확인\n2. lspci -k 로 NIC 드라이버 바인딩 상태 확인\n3. DKMS 모듈 재빌드: dkms autoinstall\n4. 펌웨어 재설치: dnf reinstall linux-firmware\n5. 이전 커널로 부팅 테스트",
         related_vendors=["Dell", "HPE", "Lenovo"], keywords=["드라이버", "NIC", "커널", "Linux", "네트워크"]),
    dict(title="서버 BMC/iDRAC/iLO/XCC 펌웨어 업데이트 절차",
         symptom="보안 취약점 CVE 알림, 관리 UI 기능 오류, 센서 데이터 이상 등 BMC 관련 문제.",
         cause="구버전 펌웨어의 알려진 버그 또는 보안 취약점.",
         solution="Dell iDRAC: DSU 설치 후 dsu --non-interactive\nHPE iLO: iLO 웹 UI → Firmware Update 또는 SPP ISO 부팅\nLenovo XCC: onecli update flash --nocompare --dir /firmware/\n\n공통: 업데이트 전 현재 설정 백업 필수",
         related_vendors=["Dell", "HPE", "Lenovo"], keywords=["펌웨어", "BMC", "iDRAC", "iLO", "XCC", "보안"]),
    dict(title="HPE ProLiant 서버 팬 오류 및 고온 경고 대응",
         symptom="iLO에서 'Fan Failure' 또는 'Fan Degraded' 경고. 서버 CPU/GPU 온도가 임계값 초과.",
         cause="팬 블레이드 파손, 베어링 마모, 또는 팬 커넥터 접촉 불량. 고온 환경 또는 흡기 필터 막힘.",
         solution="1. iLO → Power & Thermal에서 팬 RPM 및 온도 확인\n2. 물리적 팬 상태 육안 점검\n3. 팬 커넥터 재장착\n4. 흡기/배기 필터 청소 (압축 공기 사용)\n5. 팬 어셈블리 교체 (HPE 파트번호 확인)\n6. 서버룸 냉각 환경 점검",
         related_vendors=["HPE"], keywords=["팬", "온도", "열관리", "부품교체", "HPE", "고온"]),
]
for kb in kb_data:
    add("kb_articles", kb)
    print(f"  + {kb['title'][:50]}...")

# ════════════════════════════════════════════
# 5. 사내 인프라 8대
# ════════════════════════════════════════════
print("\n[5/7] 사내 인프라 생성...")
infra_data = [
    dict(name="xii-gpu-dev-01", sub="개발팀 GPU 서버", device_type="서버", status="사용중",
         vendor="NVIDIA", model="DGX Station A100", serial_number="XII-DGX-2024-001",
         ip_address="192.168.1.101", team="AI개발팀", user_name="이정호",
         os="Ubuntu 22.04 LTS", cpu="AMD EPYC 7742 64-Core", memory="512GB DDR4",
         gpu="A100 80GB x4", disk="NVMe 7.68TB x4", location="본사 3층 서버실",
         usage_period="2024.01~", purpose="딥러닝 모델 개발 및 실험"),
    dict(name="xii-gpu-dev-02", sub="개발팀 GPU 서버 #2", device_type="서버", status="사용중",
         vendor="Dell", model="PowerEdge R750xa", serial_number="XII-R750-2024-001",
         ip_address="192.168.1.102", team="AI개발팀", user_name="박상우",
         os="Ubuntu 20.04 LTS", cpu="Intel Xeon Gold 6338 x2", memory="256GB DDR4",
         gpu="A100 40GB x4", disk="SAS 1.8TB x6 RAID6", location="본사 3층 서버실",
         usage_period="2024.03~", purpose="모델 파인튜닝 및 추론 테스트"),
    dict(name="xii-storage-01", sub="중앙 스토리지", device_type="NAS", status="사용중",
         vendor="HPE", model="Alletra 5030", serial_number="XII-NAS-2023-001",
         ip_address="192.168.1.201", team="인프라팀", user_name="",
         os="HPE OneOS", cpu="-", memory="64GB", gpu="", disk="NVMe 30.72TB x24",
         location="본사 3층 서버실", usage_period="2023.07~", purpose="개발팀 공유 스토리지"),
    dict(name="xii-sw-core-01", sub="코어 스위치", device_type="스위치", status="사용중",
         vendor="Cisco", model="Nexus 9364C", serial_number="XII-SW-2023-001",
         ip_address="192.168.1.1", team="인프라팀", user_name="",
         os="NX-OS 10.2(5)", cpu="-", memory="64GB", gpu="", disk="",
         location="본사 3층 서버실", usage_period="2023.01~", purpose="서버실 코어 네트워크 스위칭 (100GbE)"),
    dict(name="xii-ws-infra-01", sub="인프라팀 워크스테이션", device_type="워크스테이션", status="사용중",
         vendor="Lenovo", model="ThinkStation P620", serial_number="XII-WS-2023-001",
         ip_address="192.168.2.11", team="인프라팀", user_name="김정완",
         os="Windows 11 Pro + Ubuntu 22.04 (WSL2)", cpu="AMD Threadripper PRO 5965WX",
         memory="256GB DDR4 ECC", gpu="RTX A5000 24GB", disk="NVMe 2TB x2",
         location="본사 2층 인프라팀 자리", usage_period="2023.05~", purpose="서버 관리 및 현장 진단"),
    dict(name="xii-gpu-spare-01", sub="예비 GPU 서버", device_type="서버", status="예비",
         vendor="Dell", model="PowerEdge R740xd", serial_number="XII-R740-2021-001",
         ip_address="", team="인프라팀", user_name="",
         os="Unallocated", cpu="Intel Xeon Gold 6230 x2", memory="192GB DDR4",
         gpu="V100 32GB x2", disk="SAS 1.2TB x12", location="본사 3층 서버실 예비 Rack",
         usage_period="2021.09~2023.12 (현재 예비)", purpose="장애 발생 시 임시 대체 서버"),
    dict(name="xii-build-01", sub="CI/CD 빌드 서버", device_type="서버", status="사용중",
         vendor="HPE", model="ProLiant DL325 Gen10 Plus", serial_number="XII-DL325-2022-001",
         ip_address="192.168.1.151", team="DevOps팀", user_name="",
         os="Ubuntu 22.04 LTS", cpu="AMD EPYC 7713 64-Core", memory="256GB DDR4",
         gpu="", disk="NVMe 3.84TB x2", location="본사 3층 서버실",
         usage_period="2022.06~", purpose="GitHub Actions self-hosted runner"),
    dict(name="xii-gpu-spare-02", sub="구형 GPU 서버 (미사용)", device_type="서버", status="미사용",
         vendor="Supermicro", model="SYS-4029GP-TRT2", serial_number="XII-SMC-2020-001",
         ip_address="", team="", user_name="",
         os="Ubuntu 18.04 LTS", cpu="Intel Xeon Gold 6130 x2", memory="128GB DDR4",
         gpu="Tesla V100 16GB x10", disk="SATA SSD 960GB x2",
         location="본사 3층 서버실 예비 Rack", usage_period="2020.01~2023.06", purpose="폐기 검토 중"),
]
for ia in infra_data:
    add("internal_assets", ia)
    print(f"  + {ia['name']} ({ia['status']})")

# ════════════════════════════════════════════
# 6. 기술 도메인 3개 + 토픽 15개 + 노트 5개 + 릴리스 5개
# ════════════════════════════════════════════
print("\n[6/7] 기술 학습 데이터 생성...")
domains_raw = [{"name": "GPU Computing"}, {"name": "서버 H/W"}, {"name": "네트워크 인프라"}]
domain_ids = {}
for dmt in domains_raw:
    domain_ids[dmt["name"]] = add("tech_domains", dmt)
    print(f"  + 도메인: {dmt['name']}")

topics_raw = [
    {"domain_id": domain_ids["GPU Computing"], "name": "CUDA 아키텍처 (Hopper/Ada)", "status": "완료"},
    {"domain_id": domain_ids["GPU Computing"], "name": "NVLink / NVSwitch 구조", "status": "완료"},
    {"domain_id": domain_ids["GPU Computing"], "name": "DCGM 모니터링 및 진단", "status": "진행중"},
    {"domain_id": domain_ids["GPU Computing"], "name": "GPU 메모리 관리 (ECC, HBM)", "status": "진행중"},
    {"domain_id": domain_ids["GPU Computing"], "name": "NCCL 분산학습 최적화", "status": "미착수"},
    {"domain_id": domain_ids["GPU Computing"], "name": "ROCm / AMD Instinct 이해", "status": "미착수"},
    {"domain_id": domain_ids["서버 H/W"], "name": "BMC/IPMI 원격 관리", "status": "완료"},
    {"domain_id": domain_ids["서버 H/W"], "name": "RAID 컨트롤러 및 스토리지", "status": "완료"},
    {"domain_id": domain_ids["서버 H/W"], "name": "서버 전원 설계 (PSU, PDU)", "status": "진행중"},
    {"domain_id": domain_ids["서버 H/W"], "name": "열관리 및 냉각 시스템", "status": "미착수"},
    {"domain_id": domain_ids["서버 H/W"], "name": "PCIe 버스 및 슬롯 이해", "status": "미착수"},
    {"domain_id": domain_ids["네트워크 인프라"], "name": "InfiniBand (HDR/NDR) 구조", "status": "진행중"},
    {"domain_id": domain_ids["네트워크 인프라"], "name": "RoCE v2 (RDMA over Ethernet)", "status": "미착수"},
    {"domain_id": domain_ids["네트워크 인프라"], "name": "100/400GbE 스위치 아키텍처", "status": "미착수"},
    {"domain_id": domain_ids["네트워크 인프라"], "name": "네트워크 대역폭 테스트 (iperf3, qperf)", "status": "완료"},
]
for t in topics_raw:
    add("tech_topics", t)
    print(f"  + 토픽: {t['name']} ({t['status']})")

notes_raw = [
    dict(domain_id=domain_ids["GPU Computing"], title="DCGM Health Check 자동화 스크립트",
         content="dcgmi health -g 0 -c\ndcgmi diag -r 1  # 빠른 검사\ndcgmi diag -r 3  # 메모리 포함\ndcgmi diag -r 4  # NVLink 포함\ndcgmi dmon -e 203,204,252,1001,1002  # 실시간 모니터링\n\nCron: 0 2 * * * dcgmi diag -r 3 >> /var/log/dcgm-diag.log 2>&1",
         keywords=["DCGM", "GPU", "모니터링", "자동화"]),
    dict(domain_id=domain_ids["GPU Computing"], title="NVLink 대역폭 측정 및 벤치마크",
         content="NCCL 테스트:\ngit clone https://github.com/NVIDIA/nccl-tests\ncd nccl-tests && make MPI=1\n./build/all_reduce_perf -b 8 -e 8G -f 2 -g 8\n\n예상값: DGX A100 → 600 GB/s, DGX H100 → 900 GB/s\n\nNVLink 상태: nvidia-smi nvlink -s / -e / -c",
         keywords=["NVLink", "NCCL", "대역폭", "벤치마크", "GPU"]),
    dict(domain_id=domain_ids["서버 H/W"], title="Dell DSU를 통한 시스템 펌웨어 일괄 업데이트",
         content="DSU 설치:\nwget https://linux.dell.com/repo/hardware/dsu/bootstrap.cgi -O bootstrap.sh\nbash bootstrap.sh && yum install dell-system-update\n\n업데이트:\ndsu --list                # 목록\ndsu --non-interactive     # 전체 업데이트\n\n주의: BIOS 업데이트는 재부팅 필요. iDRAC 업데이트 후 약 5분간 접속 불가.",
         keywords=["펌웨어", "Dell", "DSU", "업데이트", "iDRAC"]),
    dict(domain_id=domain_ids["네트워크 인프라"], title="iperf3를 이용한 네트워크 대역폭 측정",
         content="iperf3 -s                          # 서버\niperf3 -c <IP> -t 30 -P 4         # 클라이언트 (4 스트림)\niperf3 -c <IP> --bidir             # 양방향\niperf3 -c <IP> -u -b 10G          # UDP\n\n100GbE 팁:\nservice irqbalance stop\niperf3 -c <IP> -w 4M -P 8",
         keywords=["iperf3", "네트워크", "대역폭", "테스트", "100GbE"]),
    dict(domain_id=domain_ids["서버 H/W"], title="서버 RAID 구성 및 MegaCLI 사용 가이드",
         content="MegaCLI -AdpAllInfo -aAll\nMegaCLI -PDList -aAll\nMegaCLI -LDInfo -Lall -aAll\nMegaCLI -PDRbld -Start -PhysDrv[E:S] -aAll\nMegaCLI -PDRbld -ShowProg -PhysDrv[E:S] -aAll\n\nE: Enclosure ID (보통 252 또는 64), S: Slot Number (0부터)",
         keywords=["RAID", "MegaCLI", "스토리지", "디스크", "HDD"]),
]
for n in notes_raw:
    add("tech_notes", n)
    print(f"  + 노트: {n['title'][:45]}...")

releases_raw = [
    dict(date="2026-04-15", title="NVIDIA Driver 550.144.03 (Linux)",
         description="H100/A100 ECC 처리 개선, DCGM 7.x 호환성 수정. CVE-2024-0090 패치 포함.", status="파악완료"),
    dict(date="2026-03-28", title="CUDA Toolkit 12.5 Update",
         description="cuDNN 9.x 통합, Blackwell 아키텍처 사전 지원. Python 3.12 공식 지원.", status="추적중"),
    dict(date="2026-04-01", title="Dell DSU 24.04.00 (RHEL9 지원)",
         description="RHEL 9.4 공식 지원 추가. iDRAC 7.x 업데이트 포함.", status="적용완료"),
    dict(date="2026-05-10", title="HPE SPP 2026.04.0 (Gen11 지원)",
         description="ProLiant Gen11 서버 전용 드라이버 번들. iLO 6 FW 3.15 포함. 보안 패치 12종 적용.", status="학습필요"),
    dict(date="2026-02-20", title="Mellanox OFED 24.01-0.3.3.1",
         description="ConnectX-7 드라이버 안정화. RoCE v2 DCQCN 파라미터 자동 튜닝 기능 추가.", status="파악완료"),
]
for r in releases_raw:
    add("releases", r)
    print(f"  + 릴리스: {r['title']}")

# ════════════════════════════════════════════
# 7. 납품확인서 3개
# ════════════════════════════════════════════
print("\n[7/7] 납품확인서 생성...")
delivery_docs = [
    {
        "note": dict(customer_id=cust_ids["네이버클라우드"], customer_name="", delivery_date="2026-04-28",
                     doc_number="DN-2026-041", supplier_name="김정완", receiver_name="정수아",
                     supplier_sig="", receiver_sig="", status="완료"),
        "items": [
            dict(pn="NV-H100-SXM5-80", model="GPU", description="NVIDIA H100 SXM5 80GB HBM3", qty=8),
            dict(pn="NV-NVSWITCH3-CX", model="Switch", description="NVSwitch 3.0 Module", qty=2),
            dict(pn="CABLE-NVL-100G", model="Cable", description="NVLink 4.0 Interconnect Cable 1m", qty=16),
        ],
    },
    {
        "note": dict(customer_id=cust_ids["삼성SDS"], customer_name="", delivery_date="2026-05-07",
                     doc_number="DN-2026-051", supplier_name="이상현", receiver_name="박민수",
                     supplier_sig="", receiver_sig="", status="완료"),
        "items": [
            dict(pn="LNV-7XB7A05926", model="HDD", description="Lenovo 2.4TB 10K SAS 12Gb 512e 2.5in", qty=4),
            dict(pn="LNV-4XG7A37090", model="Memory", description="Lenovo 64GB TruDDR4 3200 MHz RDIMM", qty=8),
        ],
    },
    {
        "note": dict(customer_id=cust_ids["(주)카카오엔터프라이즈"], customer_name="", delivery_date="2026-05-15",
                     doc_number="DN-2026-052", supplier_name="박지훈", receiver_name="이준혁",
                     supplier_sig="", receiver_sig="", status="작성중"),
        "items": [
            dict(pn="DELL-0MV989", model="Cooling", description="Dell PowerEdge Fan Assembly 0MV989", qty=2),
            dict(pn="NV-GPU-A100-MODULE", model="GPU", description="NVIDIA A100 80GB PCIe Replacement Module", qty=1),
        ],
    },
]
total_items = 0
for entry in delivery_docs:
    note_id = add("delivery_notes", entry["note"])
    print(f"  + 납품확인서 {entry['note']['doc_number']}")
    for item in entry["items"]:
        add("delivery_items", {**item, "note_id": note_id})
        total_items += 1

print("\n" + "="*55)
print("✅ 시드 데이터 생성 완료")
print("="*55)
print(f"  고객사:          {len(customers_raw)}개")
print(f"  장비 (assets):   {len(assets_data)}개")
print(f"  장애 티켓:       {len(tickets_data)}개")
print(f"  KB 지식베이스:   {len(kb_data)}개")
print(f"  사내 인프라:     {len(infra_data)}개")
print(f"  기술 도메인:     {len(domains_raw)}개")
print(f"  기술 토픽:       {len(topics_raw)}개")
print(f"  기술 노트:       {len(notes_raw)}개")
print(f"  릴리스:          {len(releases_raw)}개")
print(f"  납품확인서:      {len(delivery_docs)}개")
print(f"  납품 품목:       {total_items}개")
