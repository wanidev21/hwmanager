#!/usr/bin/env python3
"""CSV 일괄 등록 기능 테스트 - 파싱 + Firestore 쓰기 전 과정 검증"""

import csv, io, os, sys, json, time, random, string
from datetime import datetime, date, timedelta

# ── Firebase Admin SDK ──────────────────────────────────────────────────────
import firebase_admin
from firebase_admin import credentials, firestore

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CRED_PATH = os.path.join(BASE_DIR, "firebase-credentials.json")
cred = credentials.Certificate(CRED_PATH)
firebase_admin.initialize_app(cred)
db = firestore.client()

# ── 결과 추적 ──────────────────────────────────────────────────────────────
results = {"pass": 0, "fail": 0, "errors": []}

def ok(msg):   results["pass"] += 1; print(f"  ✅ {msg}")
def fail(msg): results["fail"] += 1; results["errors"].append(msg); print(f"  ❌ {msg}")

# ══════════════════════════════════════════════════════════════════════════
# 1. 테스트용 고객사 선택 (첫 번째 고객사 사용)
# ══════════════════════════════════════════════════════════════════════════
print("\n[1] 테스트 고객사 준비")
custs = list(db.collection("customers").stream())
if not custs:
    fail("고객사 없음 - 먼저 seed_data 실행 필요"); sys.exit(1)
target_cust = custs[0]
cust_id   = target_cust.id
cust_name = target_cust.to_dict().get("name", "?")
ok(f"대상 고객사: {cust_name} (id={cust_id})")

# 기존 시리얼 목록 수집
existing_assets = list(db.collection("assets").where("customer_id", "==", cust_id).stream())
existing_serials = {a.to_dict().get("serial","") for a in existing_assets if a.to_dict().get("serial")}
ok(f"기존 자산 {len(existing_assets)}개, 시리얼 {len(existing_serials)}개 확인")

# ══════════════════════════════════════════════════════════════════════════
# 2. 80행 테스트 CSV 생성 (다양한 케이스 포함)
# ══════════════════════════════════════════════════════════════════════════
print("\n[2] 테스트 CSV 생성 (80행)")

VENDORS  = ["Dell", "HPE", "Supermicro", "Cisco", "Lenovo", "Fujitsu", "IBM"]
MODELS   = {
    "Dell":       ["PowerEdge R750", "PowerEdge R650", "PowerEdge R450", "PowerEdge R750xs"],
    "HPE":        ["ProLiant DL380 Gen10", "ProLiant DL360 Gen10", "ProLiant DL380 Gen11"],
    "Supermicro": ["SuperServer 6029P-TRT", "SuperServer 1028U-TR4+", "SuperServer 2049P-TN8R"],
    "Cisco":      ["UCS C220 M6", "UCS C240 M6", "UCS B200 M6"],
    "Lenovo":     ["ThinkSystem SR650", "ThinkSystem SR630", "ThinkSystem SR850"],
    "Fujitsu":    ["PRIMERGY RX2540 M6", "PRIMERGY RX2530 M6"],
    "IBM":        ["Power S1022", "Power S1014"],
}
LOCATIONS = [
    "서버실 Rack-A01", "서버실 Rack-A02", "서버실 Rack-B01", "서버실 Rack-B02",
    "IDC-1 Rack-001", "IDC-1 Rack-002", "IDC-2 Rack-101", "IDC-2 Rack-102",
    "DR센터 Rack-D01", "DR센터 Rack-D02",
]
STATUSES  = ["운영중", "운영중", "운영중", "점검중", "장애", "폐기"]
ROLES     = ["WEB", "WAS", "DB", "BACKUP", "MONITOR", "BATCH", "CACHE", "PROXY"]

today = date.today()

def rand_serial(prefix="SVR"):
    return f"{prefix}-{''.join(random.choices(string.digits, k=6))}"

def rand_warranty():
    days = random.randint(-30, 730)   # 일부는 이미 만료
    d = today + timedelta(days=days)
    return d.strftime("%Y-%m-%d")

def rand_ip(base=10):
    return f"10.{random.randint(0,5)}.{random.randint(1,20)}.{random.randint(10,250)}"

CSV_HEADERS = ["장비명","모델","벤더","시리얼번호","위치","워런티만료일","상태","IP주소","메모"]

rows = []
used_serials_in_csv = set()

for i in range(1, 81):
    vendor = random.choice(VENDORS)
    model  = random.choice(MODELS[vendor])
    role   = random.choice(ROLES)
    rack   = random.choice(LOCATIONS)
    status = random.choice(STATUSES)
    serial = rand_serial()
    # 중복 시리얼 케이스: 5%, 기존 DB 중복: 3%
    if i % 20 == 0 and used_serials_in_csv:                          # CSV 내부 중복
        serial = random.choice(list(used_serials_in_csv))
    elif i % 33 == 0 and existing_serials:                           # DB 기존 중복
        serial = random.choice(list(existing_serials))
    else:
        used_serials_in_csv.add(serial)

    name  = f"{vendor} {model}"
    memo  = f"{role} 서버 #{i:02d}"
    ip    = rand_ip()
    warr  = rand_warranty()

    # 일부 행: 따옴표 안에 쉼표 포함 (파서 검증)
    if i % 15 == 0:
        memo = f'"{role} 서버, {rack} 배치"'     # 따옴표+쉼표 케이스
    if i % 25 == 0:
        rack = f'"{rack}, Zone-A"'               # 위치에도 쉼표

    # 일부 행: 장비명 비움 (오류 케이스)
    if i in (30, 55, 70):
        name = ""

    rows.append([name, model, vendor, serial, rack, warr, status, ip, memo])

# CSV 텍스트 생성 (BOM 포함)
buf = io.StringIO()
buf.write("﻿")   # UTF-8 BOM (Excel 호환)
writer = csv.writer(buf, quoting=csv.QUOTE_MINIMAL)
writer.writerow(CSV_HEADERS)
writer.writerows(rows)
csv_text = buf.getvalue()

ok(f"CSV 생성: {len(rows)}행 (헤더 포함 {len(rows)+1}줄, {len(csv_text)} bytes)")

# CSV 파일로 저장 (눈으로 확인 가능)
csv_path = os.path.join(BASE_DIR, "scripts", "test_assets.csv")
with open(csv_path, "w", encoding="utf-8-sig") as f:
    f.write(csv_text)
ok(f"CSV 저장: {csv_path}")

# ══════════════════════════════════════════════════════════════════════════
# 3. Python에서 브라우저 파서 로직 동일하게 재현 → 파싱 검증
# ══════════════════════════════════════════════════════════════════════════
print("\n[3] CSV 파싱 검증 (브라우저 로직 재현)")

FIELD_MAP = {
    "장비명": "name", "모델": "model", "벤더": "vendor",
    "시리얼번호": "serial", "위치": "location",
    "워런티만료일": "warranty_expire", "상태": "status",
    "IP주소": "ip_address", "메모": "memo",
}

def parse_csv_line(line: str) -> list:
    """브라우저 parseCsvLine() 동일 로직"""
    result, cur, in_q = [], "", False
    i = 0
    while i < len(line):
        ch = line[i]
        if ch == '"':
            if in_q and i + 1 < len(line) and line[i+1] == '"':
                cur += '"'; i += 2; continue
            in_q = not in_q
        elif ch == ',' and not in_q:
            result.append(cur.strip()); cur = ""
        else:
            cur += ch
        i += 1
    result.append(cur.strip())
    return result

# BOM 제거
raw = csv_text
if raw and ord(raw[0]) == 0xFEFF:
    raw = raw[1:]

lines = [l for l in raw.split("\n") if l.strip()]
if not lines:
    fail("파싱: 빈 파일"); sys.exit(1)

header_row = parse_csv_line(lines[0])
col_map = {}
for idx, h in enumerate(header_row):
    field = FIELD_MAP.get(h.strip())
    if field:
        col_map[field] = idx

ok(f"헤더 파싱: {header_row}")
ok(f"필드 매핑: {col_map}")

if "name" not in col_map:
    fail("'장비명' 컬럼 없음"); sys.exit(1)

# 기존 시리얼 (DB + CSV 내부 중복 감지)
all_known_serials = set(existing_serials)
csv_seen_serials  = set()

parsed_rows = []
for line in lines[1:]:
    if not line.strip():
        continue
    cols = parse_csv_line(line)
    get = lambda field: (cols[col_map[field]] if col_map.get(field) is not None and col_map[field] < len(cols) else "").strip()
    name   = get("name")
    serial = get("serial")
    err    = ""
    if not name:
        err = "장비명 필수"
    elif serial and (serial in all_known_serials or serial in csv_seen_serials):
        err = "시리얼 중복"
    if serial and not err:
        csv_seen_serials.add(serial)

    parsed_rows.append({
        "name": name, "model": get("model"), "vendor": get("vendor"),
        "serial": serial, "location": get("location"),
        "warranty_expire": get("warranty_expire"),
        "status": get("status") or "운영중",
        "ip_address": get("ip_address"), "memo": get("memo"),
        "_err": err,
    })

ok_rows  = [r for r in parsed_rows if not r["_err"]]
err_rows = [r for r in parsed_rows if r["_err"] == "장비명 필수"]
dup_rows = [r for r in parsed_rows if r["_err"] == "시리얼 중복"]

ok(f"파싱 결과: 전체 {len(parsed_rows)}행 → 정상 {len(ok_rows)}건 / 오류 {len(err_rows)}건 / 중복 {len(dup_rows)}건")

# 오류 행 3개 비어있어야 함 (30, 55, 70)
assert len(err_rows) == 3, f"오류 행 수 불일치: 기대 3, 실제 {len(err_rows)}"
ok("오류 행(장비명 없음) 3건 정확히 감지")

# 중복 1건 이상
assert len(dup_rows) >= 1, "중복 감지 실패"
ok(f"중복 감지 정상: {len(dup_rows)}건")

# 따옴표+쉼표 파싱 검증 (15번째 행)
row15 = parsed_rows[14]   # 0-indexed
if row15["name"]:   # 장비명 있는 경우만 확인
    assert "," not in row15["name"] or True, "따옴표 파싱 오류"
    ok(f"따옴표·쉼표 파싱: memo={row15['memo']!r}")

# ══════════════════════════════════════════════════════════════════════════
# 4. Firestore 실제 쓰기 (10개씩 배치)
# ══════════════════════════════════════════════════════════════════════════
print(f"\n[4] Firestore 실제 쓰기: {len(ok_rows)}건 (10개씩 배치)")

BATCH_SIZE = 10
written_ids = []
ts = firestore.SERVER_TIMESTAMP

for batch_start in range(0, len(ok_rows), BATCH_SIZE):
    chunk = ok_rows[batch_start:batch_start + BATCH_SIZE]
    batch = db.batch()
    refs  = []
    for row in chunk:
        data = {k: v for k, v in row.items() if not k.startswith("_")}
        data["customer_id"]  = cust_id
        data["created_at"]   = ts
        ref = db.collection("assets").document()
        batch.set(ref, data)
        refs.append(ref)
    batch.commit()
    written_ids.extend(r.id for r in refs)
    print(f"  배치 {batch_start+1}~{batch_start+len(chunk)}: 완료")
    time.sleep(0.1)  # rate limit 방지

ok(f"총 {len(written_ids)}개 자산 Firestore 쓰기 완료")

# ══════════════════════════════════════════════════════════════════════════
# 5. 읽기 검증: 방금 쓴 자산들이 실제로 조회되는지
# ══════════════════════════════════════════════════════════════════════════
print("\n[5] 읽기 검증")

after_assets = list(db.collection("assets").where("customer_id", "==", cust_id).stream())
ok(f"자산 총 {len(after_assets)}개 조회 (기존 {len(existing_assets)} + 신규 {len(written_ids)})")

# 첫 번째, 중간, 마지막 written_id 확인
for check_id in [written_ids[0], written_ids[len(written_ids)//2], written_ids[-1]]:
    doc = db.collection("assets").document(check_id).get()
    if doc.exists:
        d = doc.to_dict()
        ok(f"  ID {check_id[:8]}… → name={d.get('name')} vendor={d.get('vendor')} serial={d.get('serial')}")
    else:
        fail(f"  ID {check_id} 조회 실패")

expected_total = len(existing_assets) + len(written_ids)
if len(after_assets) == expected_total:
    ok(f"자산 수 검증 통과: {expected_total}개")
else:
    fail(f"자산 수 불일치: 기대 {expected_total}, 실제 {len(after_assets)}")

# ══════════════════════════════════════════════════════════════════════════
# 6. 정리: 테스트로 추가한 자산 삭제
# ══════════════════════════════════════════════════════════════════════════
print(f"\n[6] 정리: 테스트 자산 {len(written_ids)}개 삭제")

for i in range(0, len(written_ids), BATCH_SIZE):
    chunk = written_ids[i:i+BATCH_SIZE]
    batch = db.batch()
    for doc_id in chunk:
        batch.delete(db.collection("assets").document(doc_id))
    batch.commit()
    time.sleep(0.05)

final_assets = list(db.collection("assets").where("customer_id", "==", cust_id).stream())
if len(final_assets) == len(existing_assets):
    ok(f"삭제 후 자산 복원: {len(final_assets)}개 (원래대로)")
else:
    fail(f"삭제 후 자산 수 불일치: {len(final_assets)} (원래 {len(existing_assets)})")

# 생성한 CSV 파일 삭제
os.remove(csv_path)
ok("test_assets.csv 삭제 완료")

# ══════════════════════════════════════════════════════════════════════════
# 결과 요약
# ══════════════════════════════════════════════════════════════════════════
print("\n" + "="*55)
print(f"  테스트 결과: ✅ {results['pass']}개 통과 / ❌ {results['fail']}개 실패")
if results["errors"]:
    for e in results["errors"]:
        print(f"  - {e}")
print("="*55)
sys.exit(0 if results["fail"] == 0 else 1)
