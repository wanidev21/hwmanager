"""
HW Manager - 전체 기능 테스트 & 데이터 시딩
CRUD 테스트 + 현실적인 샘플 데이터 삽입
"""

import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timedelta
import random
import sys

# ── Init ──────────────────────────────────────────────────────────────
cred = credentials.Certificate("/app/firebase-credentials.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

passed = 0
failed = 0

def ok(msg):
    global passed
    passed += 1
    print(f"  ✓  {msg}")

def fail(msg, err=""):
    global failed
    failed += 1
    print(f"  ✗  {msg}  [{err}]")

def section(title):
    print(f"\n{'─'*50}")
    print(f"  {title}")
    print(f"{'─'*50}")

# ── 유틸 ──────────────────────────────────────────────────────────────
def ts(days_offset=0):
    return datetime.now() + timedelta(days=days_offset)

def date_str(days_offset=0):
    return (datetime.now() + timedelta(days=days_offset)).strftime("%Y-%m-%d")

# ──────────────────────────────────────────────────────────────────────
# 1. CUSTOMERS
# ──────────────────────────────────────────────────────────────────────
section("1. 고객사 (customers) CRUD")

customers_data = [
    {"name": "(주)한국인프라솔루션", "contact": "김민준", "phone": "02-3456-7890", "email": "minjun.kim@kis.co.kr",  "address": "서울 강남구 테헤란로 152", "note": "삼성 파트너사. 연 유지보수 계약 고객"},
    {"name": "넥스트클라우드(주)",   "contact": "이서연", "phone": "031-555-1234", "email": "seoyeon@nextcloud.kr",  "address": "경기 성남시 분당구 판교로 255", "note": "클라우드 전환 프로젝트 진행 중"},
    {"name": "대한데이터센터",       "contact": "박지호", "phone": "02-7890-1234", "email": "jiho.park@ddc.co.kr",   "address": "서울 중구 을지로 100",          "note": "DC 코로케이션 고객. 장비 200대 운영"},
    {"name": "(주)스마트팩토리텍",   "contact": "최유나", "phone": "051-345-6789", "email": "yuna.choi@sft.co.kr",   "address": "부산 해운대구 센텀중앙로 55",   "note": "제조 라인 서버 유지보수"},
    {"name": "글로벌바이오텍",       "contact": "정현우", "phone": "042-678-9012", "email": "hw.jung@gbt.co.kr",     "address": "대전 유성구 테크노2로 187",     "note": "연구소 HPC 클러스터 운영"},
    {"name": "(주)에듀테크플랫폼",   "contact": "한소희", "phone": "02-2345-8901", "email": "sohee.han@edutech.kr",  "address": "서울 마포구 공덕로 115",        "note": "e-러닝 플랫폼 서버 관리"},
]

customer_ids = []
for c in customers_data:
    try:
        ref = db.collection("customers").add({**c, "created_at": firestore.SERVER_TIMESTAMP, "updated_at": firestore.SERVER_TIMESTAMP})
        customer_ids.append(ref[1].id)
        ok(f"고객사 추가: {c['name']}")
    except Exception as e:
        fail(f"고객사 추가 실패: {c['name']}", e)

# READ
try:
    docs = db.collection("customers").stream()
    count = sum(1 for _ in docs)
    ok(f"고객사 조회: {count}건")
except Exception as e:
    fail("고객사 조회 실패", e)

# UPDATE
if customer_ids:
    try:
        db.collection("customers").document(customer_ids[0]).update({"note": "삼성 파트너사. 연 유지보수 계약 고객 (2025 갱신 완료)", "updated_at": firestore.SERVER_TIMESTAMP})
        ok("고객사 수정 (note 업데이트)")
    except Exception as e:
        fail("고객사 수정 실패", e)

# ──────────────────────────────────────────────────────────────────────
# 2. ASSETS
# ──────────────────────────────────────────────────────────────────────
section("2. 자산 (assets) CRUD")

assets_data = [
    # (주)한국인프라솔루션
    {"customer_id": customer_ids[0] if customer_ids else "", "name": "Dell PowerEdge R750",   "model": "PowerEdge R750",   "serial": "KIS-SVR-001", "category": "서버",      "warranty_expire": date_str(45),   "location": "서울 강남 IDC 3F Rack-A01", "note": "운영 DB 서버"},
    {"customer_id": customer_ids[0] if customer_ids else "", "name": "HPE ProLiant DL380",    "model": "DL380 Gen10 Plus", "serial": "KIS-SVR-002", "category": "서버",      "warranty_expire": date_str(200),  "location": "서울 강남 IDC 3F Rack-A02", "note": "백업 서버"},
    {"customer_id": customer_ids[0] if customer_ids else "", "name": "Cisco Catalyst 9300",   "model": "C9300-48P",        "serial": "KIS-SW-001",  "category": "네트워크",  "warranty_expire": date_str(-15),  "location": "서울 강남 IDC 3F MDF",      "note": "L3 스위치 — 워런티 만료"},
    # 넥스트클라우드
    {"customer_id": customer_ids[1] if len(customer_ids)>1 else "", "name": "Dell PowerEdge R650",   "model": "PowerEdge R650",   "serial": "NXT-SVR-001", "category": "서버",      "warranty_expire": date_str(380),  "location": "판교 사옥 서버실 Rack-B01", "note": "가상화 호스트 (VMware ESXi)"},
    {"customer_id": customer_ids[1] if len(customer_ids)>1 else "", "name": "Pure Storage FlashArray", "model": "FlashArray//C60",  "serial": "NXT-STO-001", "category": "스토리지", "warranty_expire": date_str(700),  "location": "판교 사옥 서버실 Rack-B02", "note": "올플래시 스토리지"},
    # 대한데이터센터
    {"customer_id": customer_ids[2] if len(customer_ids)>2 else "", "name": "HPE Synergy 480",        "model": "Synergy 480 Gen10","serial": "DDC-BLD-001", "category": "서버",      "warranty_expire": date_str(60),   "location": "을지로 DC Cage-C01",        "note": "블레이드 서버 #1"},
    {"customer_id": customer_ids[2] if len(customer_ids)>2 else "", "name": "HPE Synergy 480",        "model": "Synergy 480 Gen10","serial": "DDC-BLD-002", "category": "서버",      "warranty_expire": date_str(60),   "location": "을지로 DC Cage-C01",        "note": "블레이드 서버 #2"},
    {"customer_id": customer_ids[2] if len(customer_ids)>2 else "", "name": "Arista 7050X3",          "model": "DCS-7050X3",       "serial": "DDC-NW-001",  "category": "네트워크",  "warranty_expire": date_str(180),  "location": "을지로 DC MDF",             "note": "25G ToR 스위치"},
    # 스마트팩토리텍
    {"customer_id": customer_ids[3] if len(customer_ids)>3 else "", "name": "Lenovo ThinkSystem SR650","model": "SR650 V2",         "serial": "SFT-SVR-001", "category": "서버",      "warranty_expire": date_str(500),  "location": "부산 공장 서버실",          "note": "MES 운영 서버"},
    # 글로벌바이오텍
    {"customer_id": customer_ids[4] if len(customer_ids)>4 else "", "name": "NVIDIA DGX A100",        "model": "DGX A100 80GB",    "serial": "GBT-GPU-001", "category": "서버",      "warranty_expire": date_str(320),  "location": "대전 연구소 HPC실",         "note": "AI/ML 학습 서버"},
    {"customer_id": customer_ids[4] if len(customer_ids)>4 else "", "name": "Mellanox InfiniBand",    "model": "QM8700",           "serial": "GBT-IB-001",  "category": "네트워크",  "warranty_expire": date_str(320),  "location": "대전 연구소 HPC실",         "note": "InfiniBand HDR 스위치"},
]

asset_ids = []
for a in assets_data:
    try:
        ref = db.collection("assets").add({**a, "created_at": firestore.SERVER_TIMESTAMP, "updated_at": firestore.SERVER_TIMESTAMP})
        asset_ids.append(ref[1].id)
        ok(f"자산 추가: {a['name']} ({a['serial']})")
    except Exception as e:
        fail(f"자산 추가 실패: {a['name']}", e)

# READ with condition
try:
    docs = db.collection("assets").where("category", "==", "서버").stream()
    cnt = sum(1 for _ in docs)
    ok(f"자산 조건 조회 (서버만): {cnt}건")
except Exception as e:
    fail("자산 조건 조회 실패", e)

# ──────────────────────────────────────────────────────────────────────
# 3. TICKETS
# ──────────────────────────────────────────────────────────────────────
section("3. 장애 티켓 (tickets) CRUD")

tickets_data = [
    {"title": "Dell R750 RAID 컨트롤러 배터리 경고",        "customer_id": customer_ids[0] if customer_ids else "", "assignee": "김철수", "status": "진행중", "priority": "높음", "description": "BBU(Battery Backup Unit) 방전 경고 알람 발생. RAID 성능 저하 우려.\n조치: BBU 교체 부품 발주 완료. 다음 주 방문 점검 예정."},
    {"title": "넥스트클라우드 ESXi 호스트 응답 없음",        "customer_id": customer_ids[1] if len(customer_ids)>1 else "", "assignee": "이영희", "status": "완료",   "priority": "긴급", "description": "02:15 ESXi 호스트 1번 응답 불가. VM 전체 다운.\n조치: PSU 불량 확인 후 교체 완료. 03:40 서비스 복구."},
    {"title": "Cisco 스위치 포트 플래핑 (KIS-SW-001)",      "customer_id": customer_ids[0] if customer_ids else "", "assignee": "박민수", "status": "접수",   "priority": "중간", "description": "Gi0/0/12 포트 반복 link up/down. 연결 서버 간헐적 네트워크 단절 발생."},
    {"title": "대한DC 블레이드 팬 이상음 및 온도 상승",      "customer_id": customer_ids[2] if len(customer_ids)>2 else "", "assignee": "최지영", "status": "진행중", "priority": "높음", "description": "Synergy 480 #1 팬 베어링 이상 소음. 서버 내부 온도 82°C 경고.\n조치: 팬 모듈 교체 긴급 요청, 임시 외부 냉각 조치."},
    {"title": "GBT DGX A100 GPU 메모리 오류",               "customer_id": customer_ids[4] if len(customer_ids)>4 else "", "assignee": "정현수", "status": "보류",   "priority": "높음", "description": "GPU #3 ECC 메모리 오류 다수 발생. CUDA 학습 작업 중단.\n보류 사유: 제조사 RMA 절차 진행 중 (NVIDIA 케이스 #2025-8847)."},
    {"title": "SFT MES 서버 OS 디스크 용량 경고",            "customer_id": customer_ids[3] if len(customer_ids)>3 else "", "assignee": "김철수", "status": "완료",   "priority": "중간", "description": "/var/log 파티션 94% 사용. 로그 로테이션 설정 변경 및 오래된 로그 정리 완료."},
    {"title": "Pure Storage 컨트롤러 failover 알람",         "customer_id": customer_ids[1] if len(customer_ids)>1 else "", "assignee": "이영희", "status": "완료",   "priority": "긴급", "description": "CT0 컨트롤러 NVMe 캐시 오류로 CT1으로 자동 failover.\n조치: CT0 캐시 모듈 교체 후 복구 완료. 데이터 손실 없음."},
    {"title": "에듀테크 웹서버 SSL 인증서 만료 임박",        "customer_id": customer_ids[5] if len(customer_ids)>5 else "", "assignee": "박민수", "status": "접수",   "priority": "중간", "description": "*.edutech.kr 와일드카드 인증서 D-12. 갱신 작업 일정 조율 필요."},
]

ticket_ids = []
for t in tickets_data:
    try:
        ref = db.collection("tickets").add({**t, "created_at": firestore.SERVER_TIMESTAMP, "updated_at": firestore.SERVER_TIMESTAMP})
        ticket_ids.append(ref[1].id)
        ok(f"티켓 추가: [{t['status']}] {t['title'][:40]}")
    except Exception as e:
        fail(f"티켓 추가 실패: {t['title'][:40]}", e)

# UPDATE - 상태 변경
if ticket_ids:
    try:
        db.collection("tickets").document(ticket_ids[2]).update({"status": "진행중", "updated_at": firestore.SERVER_TIMESTAMP})
        ok("티켓 상태 변경: 접수 → 진행중")
    except Exception as e:
        fail("티켓 상태 변경 실패", e)

# READ - 미완료 티켓
try:
    docs = db.collection("tickets").where("status", "!=", "완료").stream()
    cnt = sum(1 for _ in docs)
    ok(f"미완료 티켓 조회: {cnt}건")
except Exception as e:
    fail("미완료 티켓 조회 실패", e)

# ──────────────────────────────────────────────────────────────────────
# 4. KB ARTICLES
# ──────────────────────────────────────────────────────────────────────
section("4. 지식베이스 (kb_articles) CRUD")

kb_data = [
    {"title": "Dell iDRAC RAID 컨트롤러 BBU 교체 절차",
     "category": "하드웨어 유지보수",
     "tags": ["Dell", "RAID", "BBU", "iDRAC"],
     "content": """## 증상
RAID 컨트롤러 BBU 방전 또는 불량 시 쓰기 캐시 비활성화로 성능 저하.

## 교체 절차
1. iDRAC → Storage → Physical Disks에서 배터리 상태 확인
2. 서버 전원 유지 상태로 BBU 핫스왑 가능 여부 확인 (H730P, H750 지원)
3. 새 BBU 장착 후 충전 대기 (2~4시간)
4. 충전 완료 후 Write-Back Cache 자동 재활성화 확인

## 주의사항
- BBU 교체 중 쓰기 캐시는 Write-Through로 전환됨 (성능 저하 예상)
- 교체 전 반드시 백업 확인""",
     "author": "김철수"},

    {"title": "VMware ESXi 호스트 PSU 불량 판별 및 교체",
     "category": "하드웨어 유지보수",
     "tags": ["VMware", "ESXi", "PSU", "전원"],
     "content": """## 불량 확인
- esxcli hardware power cpu get 또는 iDRAC/iLO 에서 PSU 알람 확인
- 이중화 PSU인 경우 불량 PSU LED 황색 점등

## 핫스왑 교체 절차
1. 불량 PSU 식별 (전면/후면 레이블 확인)
2. PSU 고정 래치 해제 후 슬라이드 아웃
3. 신품 PSU 삽입 — 딸깍 소리 확인
4. 전력 공급 안정화 대기 30초
5. iDRAC에서 PSU 상태 정상 전환 확인

## 교체 후 검증
- VM 전체 정상 동작 확인
- vSphere Client에서 Host Summary 녹색 확인""",
     "author": "이영희"},

    {"title": "Cisco Catalyst 포트 플래핑 원인 분석 가이드",
     "category": "네트워크",
     "tags": ["Cisco", "Catalyst", "포트플래핑", "STP"],
     "content": """## 포트 플래핑 정의
인터페이스가 짧은 시간 내에 반복적으로 up/down 하는 현상.

## 주요 원인
1. 케이블 불량 또는 접촉 불량
2. SFP 모듈 불량
3. 연결 NIC 드라이버/펌웨어 문제
4. Auto-negotiation 불일치
5. STP BPDU 루프

## 진단 명령어
```
show interface Gi0/0/12 counters errors
show log | include LINEPROTO
debug spanning-tree events
```

## 조치
- 케이블 교체 → SFP 교체 → NIC 드라이버 업데이트 순으로 진행
- 지속 시 `spanning-tree portfast` 적용 검토""",
     "author": "박민수"},

    {"title": "HPE iLO를 통한 서버 원격 온도 모니터링",
     "category": "모니터링",
     "tags": ["HPE", "iLO", "온도", "모니터링"],
     "content": """## iLO 온도 임계치 기본값
- 경고(Caution): CPU 80°C, Ambient 40°C
- 위험(Critical): CPU 95°C, Ambient 45°C

## CLI 확인 (iLO SSH)
```bash
show /system1/thermal1
map1/thermal1> show -a
```

## SNMP 설정
iLO SNMP를 활성화하여 Zabbix/PRTG 연동 가능.
OID: 1.3.6.1.4.1.232.6.2.6.8.1.4.*

## 조치 기준
- 80°C 이상: 팬 필터 청소, 에어플로우 점검
- 85°C 이상: 즉시 방문 점검 및 팬 교체 검토""",
     "author": "최지영"},

    {"title": "Pure Storage FlashArray 컨트롤러 Failover 복구 절차",
     "category": "스토리지",
     "tags": ["Pure Storage", "FlashArray", "Failover", "NVMe"],
     "content": """## Failover 발생 시
1. purecli> `purearray list` — 현재 active 컨트롤러 확인
2. `purehw list --type ct` — 불량 컨트롤러 Faulted 상태 확인

## 캐시 모듈 교체
1. 불량 컨트롤러 완전 오프라인 확인 후 슬롯에서 제거
2. Pure Storage 지원 승인된 NVMe 캐시 모듈로 교체
3. 컨트롤러 재삽입 → 자동 rebuild 시작 (30~60분)
4. `purearray list` 에서 Status: Normal 확인

## 데이터 무결성 검증
- `purevolume list` 로 모든 볼륨 정상 마운트 확인
- 호스트 측 I/O 정상 여부 확인""",
     "author": "이영희"},

    {"title": "NVIDIA DGX GPU ECC 오류 대응 및 RMA 절차",
     "category": "GPU/HPC",
     "tags": ["NVIDIA", "DGX", "GPU", "ECC", "RMA"],
     "content": """## ECC 오류 확인
```bash
nvidia-smi --query-gpu=ecc.errors.corrected.volatile.total,ecc.errors.uncorrected.volatile.total --format=csv
nvidia-smi -q -d ECC
```

## 임계치
- Corrected ECC: 모니터링 (정상 범위 내일 수 있음)
- Uncorrected ECC: 즉시 GPU 격리 조치

## RMA 절차
1. nvidia-bug-report.sh 실행 및 로그 수집
2. NVIDIA Enterprise Support 케이스 오픈
3. 부품 도착 전 해당 GPU 비활성화 (`nvidia-smi -pm 0 -i 3`)
4. 교체 후 `nvidia-smi -pm 1` 및 DCGM 진단 실행

## 예방
- DCGM(Data Center GPU Manager) 상시 모니터링 권장""",
     "author": "정현수"},
]

kb_ids = []
for k in kb_data:
    try:
        ref = db.collection("kb_articles").add({**k, "created_at": firestore.SERVER_TIMESTAMP, "updated_at": firestore.SERVER_TIMESTAMP})
        kb_ids.append(ref[1].id)
        ok(f"KB 추가: {k['title'][:45]}")
    except Exception as e:
        fail(f"KB 추가 실패: {k['title'][:45]}", e)

# UPDATE
if kb_ids:
    try:
        db.collection("kb_articles").document(kb_ids[0]).update({"tags": ["Dell", "RAID", "BBU", "iDRAC", "H730P"], "updated_at": firestore.SERVER_TIMESTAMP})
        ok("KB 태그 수정")
    except Exception as e:
        fail("KB 수정 실패", e)

# ──────────────────────────────────────────────────────────────────────
# 5. DELIVERY NOTES + ITEMS
# ──────────────────────────────────────────────────────────────────────
section("5. 납품확인서 (delivery_notes + delivery_items) CRUD")

delivery_data = [
    {"doc_number": "DN-2025-0041", "customer_id": customer_ids[0] if customer_ids else "", "customer_name": "(주)한국인프라솔루션", "delivery_date": "2025-03-10", "project_name": "운영 서버 증설 프로젝트", "note": "설치 완료 확인"},
    {"doc_number": "DN-2025-0042", "customer_id": customer_ids[1] if len(customer_ids)>1 else "", "customer_name": "넥스트클라우드(주)",   "delivery_date": "2025-03-18", "project_name": "스토리지 확장 도입",   "note": "PSU 교체 포함"},
    {"doc_number": "DN-2025-0043", "customer_id": customer_ids[2] if len(customer_ids)>2 else "", "customer_name": "대한데이터센터",       "delivery_date": "2025-04-02", "project_name": "네트워크 장비 교체",   "note": ""},
    {"doc_number": "DN-2025-0044", "customer_id": customer_ids[4] if len(customer_ids)>4 else "", "customer_name": "글로벌바이오텍",       "delivery_date": "2025-04-15", "project_name": "HPC 노드 추가",        "note": "InfiniBand 케이블 포함"},
    {"doc_number": "DN-2025-0045", "customer_id": customer_ids[3] if len(customer_ids)>3 else "", "customer_name": "(주)스마트팩토리텍",   "delivery_date": "2025-05-07", "project_name": "MES 서버 유지보수",    "note": "SSD 교체 작업"},
]

delivery_items_map = {
    "DN-2025-0041": [
        {"name": "Dell PowerEdge R750 (32Core/256GB/NVMe 3.2TB×4)", "quantity": 1, "unit": "대", "unit_price": 18500000},
        {"name": "Dell EMC PowerSwitch S5248F-ON",                   "quantity": 1, "unit": "대", "unit_price": 4200000},
        {"name": "Cat6A UTP 케이블 1m",                              "quantity": 24, "unit": "개", "unit_price": 8000},
    ],
    "DN-2025-0042": [
        {"name": "Pure Storage FlashArray//C60 캐시 모듈 교체",      "quantity": 1, "unit": "식", "unit_price": 2800000},
        {"name": "HPE ProLiant PSU 800W HS",                         "quantity": 2, "unit": "개", "unit_price": 380000},
    ],
    "DN-2025-0043": [
        {"name": "Arista DCS-7050X3-48YC12 ToR 스위치",              "quantity": 2, "unit": "대", "unit_price": 9800000},
        {"name": "100G QSFP28 DAC 케이블 3m",                        "quantity": 8, "unit": "개", "unit_price": 45000},
    ],
    "DN-2025-0044": [
        {"name": "Mellanox QM8700 InfiniBand HDR 스위치",             "quantity": 1, "unit": "대", "unit_price": 22000000},
        {"name": "HDR InfiniBand 케이블 2m",                          "quantity": 16, "unit": "개", "unit_price": 180000},
    ],
    "DN-2025-0045": [
        {"name": "Samsung PM9A3 7.68TB NVMe SSD",                    "quantity": 4, "unit": "개", "unit_price": 1850000},
        {"name": "현장 출장 서비스 (반일)",                           "quantity": 1, "unit": "식", "unit_price": 300000},
    ],
}

dn_ids = []
for d in delivery_data:
    try:
        items = delivery_items_map.get(d["doc_number"], [])
        total = sum(i["quantity"] * i["unit_price"] for i in items)
        ref = db.collection("delivery_notes").add({
            **d, "total_amount": total,
            "created_at": firestore.SERVER_TIMESTAMP, "updated_at": firestore.SERVER_TIMESTAMP
        })
        dn_id = ref[1].id
        dn_ids.append(dn_id)
        ok(f"납품확인서 추가: {d['doc_number']} ({d['customer_name']}) 합계 {total:,}원")

        for item in items:
            db.collection("delivery_items").add({
                **item, "delivery_id": dn_id,
                "created_at": firestore.SERVER_TIMESTAMP, "updated_at": firestore.SERVER_TIMESTAMP
            })
        ok(f"  └ 납품 품목 {len(items)}개 추가")
    except Exception as e:
        fail(f"납품확인서 추가 실패: {d['doc_number']}", e)

# ──────────────────────────────────────────────────────────────────────
# 6. TECH DOMAINS / TOPICS / NOTES
# ──────────────────────────────────────────────────────────────────────
section("6. 기술 학습 (tech_domains / topics / notes) CRUD")

domains = [
    {"name": "서버 하드웨어",   "description": "x86 서버 아키텍처, 부품, 장애 진단 및 교체"},
    {"name": "스토리지",        "description": "SAN/NAS/올플래시, RAID, 백업 아키텍처"},
    {"name": "네트워크",        "description": "L2/L3 스위칭, 라우팅, SDN 및 케이블링"},
    {"name": "가상화/클라우드", "description": "VMware vSphere, KVM, 퍼블릭 클라우드 연동"},
    {"name": "GPU/HPC",         "description": "AI/ML 인프라, GPU 클러스터, InfiniBand"},
]

domain_ids = []
for d in domains:
    try:
        ref = db.collection("tech_domains").add({**d, "created_at": firestore.SERVER_TIMESTAMP, "updated_at": firestore.SERVER_TIMESTAMP})
        domain_ids.append(ref[1].id)
        ok(f"기술 도메인 추가: {d['name']}")
    except Exception as e:
        fail(f"도메인 추가 실패: {d['name']}", e)

topics_data = [
    {"domain_idx": 0, "name": "RAID 레벨 및 컨트롤러",  "description": "RAID 0/1/5/6/10, 하드웨어 컨트롤러 비교"},
    {"domain_idx": 0, "name": "서버 전원 및 냉각",       "description": "PSU 이중화, 서버 팬 구조, 온도 관리"},
    {"domain_idx": 1, "name": "NVMe/NVMe-oF",            "description": "NVMe 프로토콜, NVMe-oF 패브릭 구성"},
    {"domain_idx": 2, "name": "Spanning Tree Protocol",  "description": "STP, RSTP, MSTP 동작 원리 및 설정"},
    {"domain_idx": 3, "name": "VMware vSAN",              "description": "하이퍼컨버지드 인프라, vSAN 정책 및 운영"},
    {"domain_idx": 4, "name": "NVIDIA DCGM",              "description": "GPU 모니터링 및 진단 도구 활용"},
]

topic_ids = []
for t in topics_data:
    d_idx = t.pop("domain_idx")
    domain_id = domain_ids[d_idx] if d_idx < len(domain_ids) else ""
    try:
        ref = db.collection("tech_topics").add({**t, "domain_id": domain_id, "created_at": firestore.SERVER_TIMESTAMP, "updated_at": firestore.SERVER_TIMESTAMP})
        topic_ids.append(ref[1].id)
        ok(f"기술 토픽 추가: {t['name']}")
    except Exception as e:
        fail(f"토픽 추가 실패: {t['name']}", e)

notes_data = [
    {"topic_idx": 0, "title": "RAID 5 vs RAID 6 — 대용량 디스크 환경에서의 선택",
     "content": "4TB 이상 SATA 디스크 환경에서 RAID 5 재구성 중 URE 발생 확률이 급증함. 8TB 이상은 RAID 6 또는 RAID 10 권장. 재구성 시간을 줄이기 위해 핫스페어 필수."},
    {"topic_idx": 1, "title": "HPE ProLiant 서버 팬 교체 시 주의사항",
     "content": "HPE 서버는 Non-HPE 팬 사용 시 팬 속도를 최대로 고정시킴 (소음 매우 큼). 반드시 HPE 정품 또는 HPE 승인 부품 사용. iLO에서 팬 정책 확인."},
    {"topic_idx": 2, "title": "NVMe-oF vs iSCSI 성능 비교",
     "content": "NVMe-oF(RDMA over RoCEv2): 4K 랜덤 읽기 약 10M IOPS, 지연 15~20μs.\niSCSI over 25GbE: 약 800K IOPS, 지연 80~150μs.\n고성능 DB 워크로드는 NVMe-oF 채택 권장."},
    {"topic_idx": 3, "title": "BPDU Guard와 PortFast 조합 설정",
     "content": "엔드 디바이스 연결 포트에 PortFast 설정 시 반드시 BPDU Guard 함께 적용.\n`spanning-tree portfast` + `spanning-tree bpduguard enable`\n스위치 연결 포트에 PortFast 적용 금지."},
    {"topic_idx": 4, "title": "vSAN ReadyNode 선정 기준",
     "content": "VMware HCL 등재 여부 최우선. All-Flash 구성 권장 (캐시 tier 20% 룰 불필요).\n최소 4노드 권장 (fault domain 구성).\nWitness Appliance 활용으로 2+1 구성도 가능."},
    {"topic_idx": 5, "title": "DCGM-Exporter + Prometheus 연동",
     "content": "dcgm-exporter를 systemd 또는 Docker로 실행 후 Prometheus scrape config에 추가.\nGrafana NVIDIA DCGM 공식 대시보드(ID: 12239) 임포트.\nSM Clock, Memory Bandwidth Utilization, NVLink 주요 지표 모니터링."},
]

for n in notes_data:
    t_idx = n.pop("topic_idx")
    topic_id = topic_ids[t_idx] if t_idx < len(topic_ids) else ""
    try:
        db.collection("tech_notes").add({**n, "topic_id": topic_id, "created_at": firestore.SERVER_TIMESTAMP, "updated_at": firestore.SERVER_TIMESTAMP})
        ok(f"기술 노트 추가: {n['title'][:45]}")
    except Exception as e:
        fail(f"노트 추가 실패: {n['title'][:45]}", e)

# ──────────────────────────────────────────────────────────────────────
# 7. DELETE 테스트 (임시 문서 생성 후 삭제)
# ──────────────────────────────────────────────────────────────────────
section("7. DELETE 기능 테스트")

try:
    ref = db.collection("tickets").add({"title": "[테스트] 삭제용 임시 티켓", "status": "접수", "created_at": firestore.SERVER_TIMESTAMP, "updated_at": firestore.SERVER_TIMESTAMP})
    tmp_id = ref[1].id
    ok(f"임시 티켓 생성 (id: {tmp_id[:16]}...)")
    db.collection("tickets").document(tmp_id).delete()
    doc = db.collection("tickets").document(tmp_id).get()
    if not doc.exists:
        ok("임시 티켓 삭제 확인")
    else:
        fail("삭제 후에도 문서 존재")
except Exception as e:
    fail("DELETE 테스트 실패", e)

# ──────────────────────────────────────────────────────────────────────
# 8. API 헬스 체크
# ──────────────────────────────────────────────────────────────────────
section("8. API 헬스 체크")

try:
    import urllib.request
    with urllib.request.urlopen("http://localhost:8471/api/health", timeout=5) as r:
        body = r.read().decode()
        if "true" in body.lower():
            ok(f"GET /api/health → {body.strip()}")
        else:
            fail("/api/health 응답 이상", body)
except Exception as e:
    fail("/api/health 연결 실패", e)

try:
    with urllib.request.urlopen("http://localhost:8471/", timeout=5) as r:
        if r.status == 200:
            ok("GET / → 200 OK (index.html 서빙)")
        else:
            fail(f"GET / → {r.status}")
except Exception as e:
    fail("GET / 연결 실패", e)

try:
    with urllib.request.urlopen("http://localhost:8471/login", timeout=5) as r:
        if r.status == 200:
            ok("GET /login → 200 OK (login.html 서빙)")
except Exception as e:
    fail("GET /login 연결 실패", e)

try:
    with urllib.request.urlopen("http://localhost:8471/static/css/app.css", timeout=5) as r:
        if r.status == 200:
            ok("GET /static/css/app.css → 200 OK")
except Exception as e:
    fail("정적 파일 서빙 실패", e)

# ──────────────────────────────────────────────────────────────────────
# 최종 집계
# ──────────────────────────────────────────────────────────────────────
print(f"\n{'═'*50}")
print(f"  테스트 결과: ✓ {passed}개 통과   ✗ {failed}개 실패")
print(f"{'═'*50}\n")

# 데이터 현황 요약
print("  📊 Firestore 데이터 현황")
for col in ["customers", "assets", "tickets", "kb_articles", "delivery_notes", "delivery_items", "tech_domains", "tech_topics", "tech_notes"]:
    cnt = sum(1 for _ in db.collection(col).stream())
    print(f"     {col:<20} {cnt:>4}건")
print()

if failed > 0:
    sys.exit(1)
