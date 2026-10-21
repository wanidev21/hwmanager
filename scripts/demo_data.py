"""
시연용 데이터: 공용 업무 데이터를 비우고 가상의 서버 H/W 유지보수 현장 데이터로 다시 채운다.
날짜는 실행한 날 기준 (오늘 작업·내일 작업·반납 기한 지남·워런티 임박 등이 항상 살아 있도록 시연 전날 실행)

지우는 것: customers, projects, assets, tickets(+진행 기록), jobs, job_templates, parts,
          delivery_notes, delivery_items, audit_logs
두는 것:   config(허용 계정), users, 개인 데이터(KB·기술 노트·캘린더 등)
실행 전 자동으로 scripts/backup.py와 같은 전체 백업을 backups/에 남김.

사용법:
  python scripts/demo_data.py --owner <내 이메일> --yes
    --owner: 시연하는 사람(Firebase 로그인 계정). 일부 작업·티켓을 이 사람 담당으로 넣고('내 담당'),
             이 사람의 KB가 비어 있으면 KB 3건을 추가. 이메일은 코드에 두지 않음
  --yes 없이 실행하면 무엇을 지울지만 보여 줌

고객사·인물·연락처·S/N은 모두 가상 (연락처는 010-0000-xxxx, 메일은 example.com)
"""
import os
import sys
import random
import argparse
import warnings
from datetime import datetime, timedelta, timezone

sys.stdout.reconfigure(encoding='utf-8')
warnings.filterwarnings('ignore', category=FutureWarning)

import firebase_admin
from firebase_admin import credentials, firestore, auth

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from backup import backup, CRED_PATH   # noqa: E402

KST = timezone(timedelta(hours=9))
NOW = datetime.now(KST)
TODAY = NOW.replace(hour=0, minute=0, second=0, microsecond=0)
WIPE = ['customers', 'projects', 'assets', 'tickets', 'jobs', 'job_templates', 'parts',
        'delivery_notes', 'delivery_items', 'audit_logs']

random.seed(20261021)
db = None
ME = {'uid': 'demo-owner', 'name': '담당자'}
TEAM = ['서은우', '문지호', '배현수']


def d(days):                       # 'YYYY-MM-DD' (오늘 기준 +days)
    return (TODAY + timedelta(days=days)).strftime('%Y-%m-%d')


def ts(days, hour=10, minute=0):   # Timestamp용 datetime
    return TODAY + timedelta(days=days, hours=hour, minutes=minute)


def put(col, data, created_days=-30, doc_id=None):
    ref = db.collection(col).document(doc_id) if doc_id else db.collection(col).document()
    t = ts(created_days, 9, random.randint(0, 59))
    ref.set({**data, 'created_at': t, 'updated_at': t,
             'created_by': ME['uid'], 'created_by_name': ME['name']})
    return ref.id


def wipe():
    n = 0
    for col in WIPE:
        for snap in db.collection(col).stream():
            for sub in snap.reference.collections():
                for s in sub.stream():
                    s.reference.delete(); n += 1
            snap.reference.delete(); n += 1
    print(f'삭제: 문서 {n}개')


def audit(action, entity, entity_id, label, detail, days, by=None):
    t = ts(days, 18, random.randint(0, 59))
    db.collection('audit_logs').add({
        'action': action, 'entity': entity, 'entity_id': entity_id, 'label': label, 'detail': detail,
        'by': ME['uid'], 'by_name': by or ME['name'], 'at': t, 'created_at': t})


# ── 고객사·프로젝트·장비 ──────────────────────────────────────────────
CUSTOMERS = {
    'hanbit': dict(name='한빛클라우드(주)', contact='김도윤 과장', phone='010-0000-1101', email='infra@hanbit-cloud.example.com',
                   address='경기 성남시 분당구 판교로 (가상)', memo='IaaS 사업자. 작업은 22시 이후, 출입 3일 전 신청'),
    'sejong': dict(name='세종AI연구원', contact='이하늘 선임', phone='010-0000-2202', email='gpu-ops@sejong-ai.example.com',
                   address='세종특별자치시 (가상)', memo='GPU 학습 클러스터. 학습 잡 일정 확인 후 작업'),
    'daesung': dict(name='대성제약 정보팀', contact='장민재 팀장', phone='010-0000-3303', email='it@daesung-pharm.example.com',
                    address='충북 오송 (가상)', memo='MES·ERP 24시간 운영 — 이중화 장비 한 대씩만 작업'),
    'nuri': dict(name='누리데이터센터', contact='윤태호 차장', phone='010-0000-4404', email='noc@nuri-dc.example.com',
                 address='서울 금천구 가산동 (가상)', memo='코로케이션. 반입·반출 시 NOC 승인'),
    'moa': dict(name='모아핀테크(주)', contact='한서진 대리', phone='010-0000-5505', email='dba@moa-fintech.example.com',
                address='서울 영등포구 여의도 (가상)', memo='결제 DB. 변경 작업은 월 1회 정기 점검 창에서만'),
}

PROJECTS = [
    # key, customer, name, vendor, device_type, qty, install(days), [(type, start_days, end_days)]
    ('hb-iaas', 'hanbit', 'IaaS 컴퓨트 노드 2차 증설', 'Dell', '서버', 6, -400, [('기본', -400, 3 * 365 - 400)]),
    ('hb-bkp', 'hanbit', '백업 스토리지 도입', 'Dell', '스토리지', 2, -1075, [('기본', -1075, 20)]),
    ('sj-hgx', 'sejong', 'H100 학습 클러스터', 'Supermicro', 'GPU서버', 4, -240, [('기본', -240, 3 * 365 - 240)]),
    ('sj-ib', 'sejong', '학습 클러스터 InfiniBand 패브릭', 'NVIDIA', '스위치', 1, -240, [('기본', -240, 3 * 365 - 240)]),
    ('sj-inf', 'sejong', '추론 서버 (L40S)', 'Dell', 'GPU서버', 2, -30, [('기본', -30, 3 * 365 - 30)]),
    ('ds-erp', 'daesung', 'MES·ERP 서버 이중화', 'HPE', '서버', 4, -700, [('기본', -700, 3 * 365 - 700)]),
    ('nr-col', 'nuri', '코로케이션 고객 서버 유지보수', 'Dell', '서버', 3, -1110, [('기본', -1110, -15)]),
    ('moa-db', 'moa', '결제 DB 서버', 'Lenovo', '서버', 2, -150, [('기본', -150, 5 * 365 - 150)]),
]

# (project, hostname, model, serial, ip, location, os, cpu, memory, gpu, disk, bios, bmc, raid, status)
ASSETS = [
    *[('hb-iaas', f'hb-cmp-{i:02d}', 'Dell PowerEdge R760', f'8XK{i}QJ3', f'10.20.11.{10 + i}', f'판교 IDC 3F A-0{(i + 1) // 2} U{20 + (i % 2) * 2}',
       'Rocky Linux 9.4', 'Xeon Gold 6430 x2', '512GB DDR5', '', 'NVMe 3.84TB x4',
       '2.2.6' if i == 1 else '2.1.5', '7.10.30.00' if i == 1 else '7.00.00.172', 'PERC H965i 8.8.0.0.18-26', '운영중') for i in range(1, 7)],
    ('hb-bkp', 'hb-bkp-ctl-a', 'Dell PowerVault ME5024', 'ME5BK01', '10.20.30.11', '판교 IDC 3F B-02', '', '', '', '', 'SAS 2.4TB x24',
     '', '', 'ME5 FW ME5.1.1.0.5', '운영중'),
    ('hb-bkp', 'hb-bkp-ctl-b', 'Dell PowerVault ME5024', 'ME5BK02', '10.20.30.12', '판교 IDC 3F B-02', '', '', '', '', 'SAS 2.4TB x24',
     '', '', 'ME5 FW ME5.1.1.0.5', '운영중'),
    *[('sj-hgx', f'hgx-h100-{i:02d}', 'Supermicro SYS-821GE-TNHR', f'S4210{i}8XA', f'10.40.1.{100 + i}', f'세종 GPU홀 R-0{i}', 'Ubuntu 22.04 LTS',
       'Xeon Platinum 8480+ x2', '2TB DDR5', 'NVIDIA H100 SXM5 80GB x8', 'NVMe 7.68TB x8',
       '2.1', '01.03.12', 'Broadcom 9600-16i 8.6.2.0', '장애' if i == 3 else '운영중') for i in range(1, 5)],
    ('sj-ib', 'ib-sw-01', 'NVIDIA QM9700 (NDR 64p)', 'MT2341X0011', '10.40.0.2', '세종 GPU홀 R-00', 'MLNX-OS 3.11', '', '', '', '',
     '', '', '', '운영중'),
    *[('sj-inf', f'sj-inf-{i:02d}', 'Dell PowerEdge R760xa', f'3LQ{i}Z94', f'10.40.2.{10 + i}', '세종 GPU홀 R-05', 'Ubuntu 22.04 LTS',
       'Xeon Gold 6448Y x2', '1TB DDR5', 'NVIDIA L40S 48GB x4', 'NVMe 3.84TB x2', '2.2.6', '7.10.30.00', 'PERC H755 52.26.0-5179', '운영중') for i in (1, 2)],
    *[('ds-erp', h, 'HPE ProLiant DL380 Gen11', f'SGH3{n}1KX{n}', f'172.16.5.{20 + n}', f'오송 전산실 R-1{n}', 'RHEL 8.8',
       'Xeon Gold 5418Y x2', '384GB DDR5', '', 'SSD 960GB x2 + SAS 2.4TB x6', 'U54 v2.16', 'iLO 6 1.58', 'MR416i-p 52.26.3-5250',
       '운영중') for n, h in enumerate(['ds-mes-01', 'ds-mes-02', 'ds-erp-db01', 'ds-erp-db02'], start=1)],
    *[('nr-col', f'nuri-col-{i:02d}', 'Dell PowerEdge R650', f'C7P{i}MN2', f'192.168.70.{30 + i}', f'가산 IDC 5F C-1{i}', 'Ubuntu 20.04 LTS',
       'Xeon Silver 4314 x2', '256GB DDR4', '', 'SSD 1.92TB x4', '1.13.2', '6.10.80.00', 'PERC H745 51.16.0-4076', '운영중') for i in range(1, 4)],
    *[('moa-db', f'moa-db-{i:02d}', 'Lenovo ThinkSystem SR650 V3', f'J30{i}A7KQ', f'10.9.8.{i}', f'여의도 DC 2F D-0{i}', 'RHEL 9.2',
       'Xeon Gold 6442Y x2', '1TB DDR5', '', 'NVMe 3.2TB x8', 'ESE122N 2.10', 'XCC2 ESX320B 2.00', 'RAID 940-8i 52.24.0-4763', '운영중') for i in (1, 2)],
]


def seed_inventory():
    cust, proj, asset = {}, {}, {}
    for k, c in CUSTOMERS.items():
        cust[k] = put('customers', c, -1200)
    for key, ck, name, vendor, dtype, qty, inst, periods in PROJECTS:
        wp = [{'type': t, 'start': d(s), 'end': d(e), 'memo': ''} for t, s, e in periods]
        proj[key] = (put('projects', {
            'customer_id': cust[ck], 'name': name, 'vendor': vendor, 'device_type': dtype, 'quantity': qty,
            'install_date': d(inst), 'memo': '', 'warranty_periods': wp,
            'warranty_expire': max(p['end'] for p in wp), 'warranty_start': wp[0]['start'],
        }, inst), cust[ck])
    for (pk, host, model, sn, ip, loc, os_, cpu, mem, gpu, disk, bios, bmc, raid, status) in ASSETS:
        pid, cid = proj[pk]
        inst = next(p[6] for p in PROJECTS if p[0] == pk)
        asset[host] = put('assets', {
            'customer_id': cid, 'project_id': pid, 'hostname': host, 'model': model, 'serial': sn, 'ip_address': ip,
            'location': loc, 'os': os_, 'cpu': cpu, 'memory': mem, 'gpu': gpu, 'disk': disk,
            'bios_version': bios, 'bmc_version': bmc, 'raid_version': raid, 'driver_version': '',
            'device_type': next(p[4] for p in PROJECTS if p[0] == pk), 'status': status,
            'install_date': d(inst), 'vendor_case_no': '', 'memo': '',
        }, inst)
    return cust, proj, asset


# ── 장애 티켓 + 진행 기록 ─────────────────────────────────────────────
def seed_tickets(cust, asset):
    A = lambda h: {'asset_id': asset[h], 'asset_host': h}
    T = {}

    def ticket(key, ck, host, title, priority, status, assignee, opened, logs, completed=None):
        a = next(x for x in ASSETS if x[1] == host)
        data = {'title': title, 'customer_id': cust[ck], **A(host), 'asset_serial': a[3], 'asset_model': a[2],
                'assignee': assignee, 'priority': priority, 'status': status,
                'completed_at': d(completed) if completed is not None else None,
                'log_keys': [l[2] for l in logs][:20]}
        tid = put('tickets', data, opened)
        for (day, hhmm, text, typ, *extra) in logs:
            h, m = map(int, hhmm.split(':'))
            log = {'type': typ, 'text': text, 'at': ts(day, h, m), 'by': ME['uid'],
                   'by_name': extra[0] if extra else assignee, 'auto': typ == '상태', 'created_at': ts(day, h, m)}
            if typ == '부품' and len(extra) > 1:
                log.update(pn=extra[1], fru=extra[2] if len(extra) > 2 else '')
            if typ == '상태':
                log['to'] = text.split('→')[-1].strip()
            db.collection('tickets').document(tid).collection('logs').add(log)
        T[key] = (tid, title)

    me = ME['name']
    ticket('gpu', 'sejong', 'hgx-h100-03', 'hgx-h100-03 GPU#5 XID 79 (GPU fallen off the bus)', '긴급', '진행중', me, -2, [
        (-2, '09:12', '학습 잡 중단, nvidia-smi에서 GPU#5 사라짐. 고객 이하늘 선임 신고', '증상'),
        (-2, '10:40', 'dmesg: NVRM Xid 79, GPU has fallen off the bus. 재부팅 후에도 재현', '점검'),
        (-2, '11:05', '접수 → 진행중', '상태'),
        (-2, '14:30', 'nvidia-bug-report, SEL 로그 수집해 Supermicro RMA 접수 (SMC-RMA-2610-0571)', '벤더'),
        (-1, '16:20', 'H100 SXM5 모듈 RMA 승인 — 3~4영업일 내 입고 예정', '부품', me, '699-2G520-0200-030', 'GPU5'),
        (-1, '16:45', '고객: 교체 전까지 7GPU로 학습 계속 진행하기로 함', '고객연락'),
    ])
    ticket('psu', 'hanbit', 'hb-cmp-04', 'hb-cmp-04 PSU#2 Failed — iDRAC 경고', '높음', '진행중', me, -3, [
        (-3, '07:50', 'iDRAC 알림: PSU 2 failed. 이중화로 서비스 영향 없음', '증상'),
        (-3, '09:30', 'iDRAC LC 로그 확인 — PSU2 입력 정상, 출력 fault. 케이블 재장착 후에도 동일', '점검'),
        (-3, '10:10', 'Dell 기술지원 접수, 교체 부품 발송 요청', '벤더'),
        (-1, '15:00', '교체 PSU 입고 (1400W)', '부품', me, '0H1VGC', 'PSU2'),
        (-1, '15:20', '고객 김도윤 과장: 오늘 22시 작업 승인', '고객연락'),
    ])
    ticket('raid', 'daesung', 'ds-erp-db02', 'ds-erp-db02 RAID 가상 디스크 Degraded (Slot 4)', '높음', '완료', TEAM[1], -12, [
        (-12, '08:30', 'iLO: Logical drive 2 degraded, Bay 4 failed', '증상', TEAM[1]),
        (-12, '09:10', 'ssacli로 Bay 4 failed 확인, 핫스페어 없음', '점검', TEAM[1]),
        (-10, '14:00', '2.4TB SAS 디스크 핫스왑 교체, 리빌드 시작', '조치', TEAM[1]),
        (-9, '09:00', '리빌드 완료, 가상 디스크 Optimal', '조치', TEAM[1]),
        (-9, '09:05', '진행중 → 완료', '상태', TEAM[1]),
    ], completed=-9)
    ticket('ssd', 'daesung', 'ds-mes-01', 'ds-mes-01 OS 디스크 SMART 경고 (Wearout)', '높음', '진행중', TEAM[0], -16, [
        (-16, '10:00', 'iLO: Drive Bay 1 predictive failure (SSD wearout 98%)', '증상', TEAM[0]),
        (-14, '22:30', 'RAID1 한쪽 SSD 교체 완료, 리빌드 정상', '조치', TEAM[0]),
        (-13, '09:00', '불량 SSD 반납 필요 — HPE 반납 라벨 수령 대기', '부품', TEAM[0], 'P47808-B21', 'Bay1'),
    ])
    ticket('dimm', 'moa', 'moa-db-01', 'moa-db-01 메모리 CE 다수 발생 (DIMM A3)', '보통', '진행중', TEAM[1], -10, [
        (-10, '11:00', 'XCC 이벤트: DIMM A3 correctable error threshold', '증상', TEAM[1]),
        (-8, '22:00', '정기 점검 창에서 DIMM A3 교체 (64GB DDR5 RDIMM)', '조치', TEAM[1]),
        (-8, '22:40', '교체 후 메모리 테스트 통과, 2주 모니터링 후 종결 예정', '메모', TEAM[1]),
    ])
    ticket('bmc', 'nuri', 'nuri-col-02', 'nuri-col-02 iDRAC 웹 접속 불가', '낮음', '보류', TEAM[2], -6, [
        (-6, '13:00', 'iDRAC 웹 응답 없음, ping은 정상', '증상', TEAM[2]),
        (-6, '13:40', 'racadm racreset은 OS 접근 필요 — 고객 일정 대기', '점검', TEAM[2]),
        (-5, '10:00', '진행중 → 보류', '상태', TEAM[2]),
    ])
    ticket('me5', 'hanbit', 'hb-bkp-ctl-b', 'hb-bkp 컨트롤러 펌웨어 권고 업데이트 (Dell DSA)', '보통', '진행중', me, -7, [
        (-7, '10:00', 'Dell 보안 권고: ME5 펌웨어 ME5.1.2.0.1 업데이트 권장', '벤더'),
        (-6, '11:00', '고객과 작업 일정 협의 — 새벽 2시 작업 창 확보', '고객연락'),
    ])
    ticket('ib', 'sejong', 'ib-sw-01', 'ib-sw-01 포트 17 링크 플래핑', '보통', '완료', me, -25, [
        (-25, '09:00', 'UFM 알림: 포트 17 link down/up 반복', '증상'),
        (-24, '15:00', '케이블 교체 (NDR OSFP 2m) 후 정상, BER 정상 범위', '조치', me, 'MCP4Y10-N002', ''),
        (-23, '09:00', '진행중 → 완료', '상태'),
    ], completed=-23)
    return T


# ── 부품·RMA ─────────────────────────────────────────────────────────
def seed_parts(cust, asset, T):
    def part(tk, ck, host, name, pn, status, dates, **kw):
        tid, title = T[tk]
        put('parts', {'name': name, 'pn': pn, 'fru': kw.get('fru', ''), 'qty': 1, 'case_no': kw.get('case', ''),
                      'new_sn': kw.get('new_sn', ''), 'old_sn': kw.get('old_sn', ''),
                      'return_required': kw.get('ret', True), 'return_days': kw.get('days', 10),
                      'tracking': kw.get('tracking', ''), 'memo': kw.get('memo', ''),
                      'status': status, 'dates': {k: d(v) for k, v in dates.items()},
                      'ticket_id': tid, 'ticket_title': title, 'customer_id': cust[ck],
                      'asset_id': asset[host], 'asset_host': host}, min(dates.values()))
    part('gpu', 'sejong', 'hgx-h100-03', 'NVIDIA H100 SXM5 80GB 모듈', '699-2G520-0200-030', '요청', {'요청': -1},
         case='SMC-RMA-2610-0571', old_sn='1654023019842', fru='GPU5', days=15)
    part('psu', 'hanbit', 'hb-cmp-04', 'Dell 1400W Titanium PSU', '0H1VGC', '입고', {'요청': -3, '입고': -1},
         case='DELL-SR-198445012', new_sn='CN1797253K0145', fru='PSU2')
    part('ssd', 'daesung', 'ds-mes-01', 'HPE 480GB SATA RI SSD (OS)', 'P47808-B21', '교체', {'요청': -16, '입고': -15, '교체': -14},
         case='HPE-5078812345', old_sn='S5E2NE0R601234', new_sn='S5E2NE0R609876', fru='Bay1', memo='반납 라벨 고객사로 발송됨')
    part('dimm', 'moa', 'moa-db-01', 'Lenovo 64GB DDR5-4800 RDIMM', '4X71M22551', '교체', {'요청': -10, '입고': -9, '교체': -8},
         case='LNV-RMA-77120934', old_sn='80AD0123ABCD', new_sn='80AD0123EF01', fru='DIMM A3')
    part('raid', 'daesung', 'ds-erp-db02', 'HPE 2.4TB SAS 10K SFF HDD', '881457-B21', '종결',
         {'요청': -12, '입고': -11, '교체': -10, '반납': -6, '종결': -4},
         case='HPE-5078800012', old_sn='WFK1A2B3', new_sn='WFK1C4D5', tracking='CJ 6012-3456-7890', fru='Bay4')
    part('ib', 'sejong', 'ib-sw-01', 'NDR OSFP 패시브 케이블 2m', 'MCP4Y10-N002', '종결', {'요청': -25, '입고': -25, '교체': -24, '종결': -24},
         ret=False, memo='재고 사용 (반납 없음)')


# ── 작업 일정 (준비 체크리스트) ────────────────────────────────────────
def seed_jobs(cust, asset, T):
    n = [0]

    def items(spec):   # [(text, due_days, done)]
        out = {}
        for i, (text, due, done) in enumerate(spec):
            n[0] += 1
            it = {'text': text, 'due_days': due, 'done': done, 'order': i}
            if done:
                it.update(done_by_name=ME['name'], done_at=ts(-2, 17))
            out[f'i{n[0]:03d}'] = it
        return out

    def job(title, typ, day, time, ck, host, tk, assignee, spec, status='예정', memo='', **kw):
        tid, ttitle = T[tk] if tk else ('', '')
        return put('jobs', {'title': title, 'type': typ, 'date': d(day), 'time': time, 'customer_id': cust[ck],
                            'asset_id': asset.get(host, '') if host else '', 'asset_host': host or '',
                            'ticket_id': tid, 'ticket_title': ttitle, 'assignee': assignee, 'memo': memo,
                            'status': status, 'items': items(spec),
                            'completed_at': d(day) if status == '완료' else None, **kw}, min(day, 0) - 3)

    me = ME['name']
    job('hb-cmp-04 PSU#2 교체', '부품 교체', 0, '22:00', 'hanbit', 'hb-cmp-04', 'psu', me, [
        ('출입 신청', 3, True), ('교체 부품 수령 · P/N 확인', 2, True), ('작업계획서 · 작업 승인', 2, True),
        ('고객 담당자 일정 · 작업 시간 확인', 1, True), ('공구 · 정전기 방지 밴드', 0, False)],
        memo='판교 IDC 3F A-02. 출입은 B1 보안실에서 신분증 교환')
    job('hgx-h100-03 GPU#5 교체 (RMA 입고 후)', '부품 교체', 2, '10:00', 'sejong', 'hgx-h100-03', 'gpu', me, [
        ('출입 신청', 3, False), ('교체 부품 수령 · P/N 확인', 2, False), ('작업계획서 · 작업 승인', 2, False),
        ('고객 담당자 일정 · 작업 시간 확인', 1, True), ('공구 · 정전기 방지 밴드', 0, False)],
        memo='학습 잡 드레인 후 작업. HGX 트레이 분리 — 2인 작업')
    job('hb-bkp 컨트롤러 펌웨어 ME5.1.2.0.1', '펌웨어 업데이트', 3, '02:00', 'hanbit', 'hb-bkp-ctl-b', 'me5', me, [
        ('대상 버전 · 릴리스 노트 확인', 5, True), ('출입 신청', 3, True), ('작업계획서 · 롤백 계획', 2, False),
        ('서비스 중단 시간 고객 확인', 2, True), ('펌웨어 파일 USB 준비', 1, False)])
    job('moa-db-01 메모리 교체 후 재점검', '정기 점검', 5, '22:00', 'moa', 'moa-db-01', 'dimm', TEAM[1], [
        ('출입 신청', 3, False), ('이전 점검 이슈 확인', 1, False), ('점검표 준비', 1, False)])
    job('세종AI 추론 서버 2대 추가 설치', '신규 설치', 9, '09:30', 'sejong', None, None, me, [
        ('반입 장비 · 수량 확인', 3, False), ('출입 · 장비 반입 신청', 3, False), ('랙 위치 · 전원 · 케이블 확인', 2, False),
        ('IP · hostname 정보 받기', 2, False), ('납품확인서 준비', 1, False)])
    job('nuri-col-02 iDRAC 리셋 점검', '정기 점검', -1, '14:00', 'nuri', 'nuri-col-02', 'bmc', TEAM[2], [
        ('출입 신청', 3, True), ('이전 점검 이슈 확인', 1, True), ('점검표 준비', 1, False)],
        memo='고객 OS 접근 승인 받으면 racadm racreset')
    job('ds-erp-db02 RAID 디스크 교체', '부품 교체', -10, '14:00', 'daesung', 'ds-erp-db02', 'raid', TEAM[1], [
        ('출입 신청', 3, True), ('교체 부품 수령 · P/N 확인', 2, True), ('작업계획서 · 작업 승인', 2, True),
        ('고객 담당자 일정 · 작업 시간 확인', 1, True), ('공구 · 정전기 방지 밴드', 0, True)], status='완료')
    jid = job('hb-cmp-01 BIOS · iDRAC 업데이트 (1차)', '펌웨어 업데이트', -20, '23:00', 'hanbit', 'hb-cmp-01', None, me, [
        ('대상 버전 · 릴리스 노트 확인', 5, True), ('출입 신청', 3, True), ('작업계획서 · 롤백 계획', 2, True),
        ('서비스 중단 시간 고객 확인', 2, True), ('펌웨어 파일 USB 준비', 1, True)], status='완료',
        memo='1대 먼저 적용 후 1주 모니터링, 이상 없으면 나머지 5대',
        fw_changes=[{'label': 'BIOS', 'from': '2.1.5', 'to': '2.2.6'}, {'label': 'BMC', 'from': '7.00.00.172', 'to': '7.10.30.00'}])
    audit('수정', '장비', asset['hb-cmp-01'], 'hb-cmp-01',
          'BIOS 2.1.5 → 2.2.6, BMC 7.00.00.172 → 7.10.30.00 (작업: hb-cmp-01 BIOS · iDRAC 업데이트 (1차))', -20)


# ── 납품확인서 (품목 ↔ 장비 연결) ─────────────────────────────────────
def seed_delivery(cust, asset):
    def note(doc_no, ck, project, day, items, receiver):
        idx = {}
        for it in items:
            for h in it.get('hosts', []):
                idx.setdefault(asset[h], []).append(it['description'])
        nid = put('delivery_notes', {
            'customer_id': cust[ck], 'customer_name': CUSTOMERS[ck]['name'], 'project_name': project,
            'delivery_date': d(day), 'doc_number': doc_no, 'note': '', 'contact_mobile': '', 'contact_tel': '',
            'contact_fax': '', 'contact_email': '', 'supplier_name': ME['name'], 'receiver_name': receiver,
            'supplier_sig': '', 'receiver_sig': '', 'item_count': len(items), 'status': '완료',
            'asset_ids': list(idx), 'asset_items': {k: ', '.join(v) for k, v in idx.items()},
        }, day)
        for i, it in enumerate(items, start=1):
            hosts = it.get('hosts', [])
            put('delivery_items', {'delivery_id': nid, 'seq': i, 'description': it['description'], 'model': it['model'],
                                   'qty': it['qty'], 'unit': it.get('unit', 'EA'), 'note': it.get('note', ''),
                                   'asset_ids': [asset[h] for h in hosts], 'asset_hosts': hosts}, day)

    note(f'DN-{TODAY.year}-0031', 'sejong', '추론 서버 (L40S)', -30, [
        {'description': 'Dell PowerEdge R760xa', 'model': 'Server', 'qty': 2, 'unit': '대', 'hosts': ['sj-inf-01', 'sj-inf-02']},
        {'description': 'NVIDIA L40S 48GB PCIe', 'model': 'GPU', 'qty': 8, 'note': '서버당 4장', 'hosts': ['sj-inf-01', 'sj-inf-02']},
        {'description': 'NVIDIA ConnectX-7 200GbE NIC', 'model': 'NIC', 'qty': 2, 'hosts': ['sj-inf-01', 'sj-inf-02']},
        {'description': 'DAC 케이블 200G 3m', 'model': 'Cable', 'qty': 4},
    ], '이하늘')
    note(f'DN-{TODAY.year - 1}-0112', 'hanbit', 'IaaS 컴퓨트 노드 2차 증설', -400, [
        {'description': 'Dell PowerEdge R760', 'model': 'Server', 'qty': 6, 'unit': '대', 'hosts': [f'hb-cmp-{i:02d}' for i in range(1, 7)]},
        {'description': '3.84TB NVMe U.2 SSD', 'model': 'NVMe', 'qty': 24, 'note': '서버당 4개', 'hosts': [f'hb-cmp-{i:02d}' for i in range(1, 7)]},
        {'description': '25GbE SFP28 DAC 2m', 'model': 'Cable', 'qty': 12},
    ], '김도윤')
    note(f'DN-{TODAY.year}-0018', 'moa', '결제 DB 서버', -150, [
        {'description': 'Lenovo ThinkSystem SR650 V3', 'model': 'Server', 'qty': 2, 'unit': '대', 'hosts': ['moa-db-01', 'moa-db-02']},
        {'description': 'ThinkSystem 3.2TB NVMe Mixed Use', 'model': 'NVMe', 'qty': 16, 'hosts': ['moa-db-01', 'moa-db-02']},
    ], '한서진')


# ── 개인 KB (시연자에게 없을 때만) ─────────────────────────────────────
KB = [
    dict(title='NVIDIA XID 79 — GPU fallen off the bus 대응', symptom='nvidia-smi에서 GPU 사라짐, dmesg에 Xid 79',
         cause='PCIe 링크 단절: GPU 모듈·베이스보드·전원 불량, 과열', solution='1. nvidia-bug-report.sh 수집\n2. SEL·BMC 로그로 전원/온도 이벤트 확인\n3. 재부팅 후 재현 여부\n4. 재현 시 벤더 RMA (모듈 S/N 기록)',
         related_vendors=['NVIDIA', 'Supermicro'], keywords=['GPU', 'XID', 'RMA']),
    dict(title='Dell iDRAC PSU failed 경고 점검 순서', symptom='iDRAC 알림 PSU failed, 서버는 이중화로 동작',
         cause='PSU 출력 불량 또는 입력 전원·케이블 문제', solution='1. LC 로그에서 입력/출력 fault 구분\n2. 전원 케이블·PDU 교차 확인\n3. 출력 fault면 PSU 교체 (핫스왑)\n4. 교체 후 iDRAC에서 Redundancy 정상 확인',
         related_vendors=['Dell'], keywords=['PSU', 'iDRAC', '부품교체']),
    dict(title='HPE Smart Array 디스크 교체 · 리빌드 확인', symptom='Logical drive degraded, Bay n failed',
         cause='디스크 물리 불량', solution='1. ssacli ctrl all show config detail\n2. 핫스왑 교체 (LED 확인)\n3. 리빌드 진행률 모니터링\n4. 불량 디스크 반납 라벨·기한 확인',
         related_vendors=['HPE'], keywords=['RAID', '부품교체']),
]


def main():
    global db
    ap = argparse.ArgumentParser()
    ap.add_argument('--owner', help='시연하는 사람의 로그인 이메일 (담당자 이름·KB 소유자)')
    ap.add_argument('--yes', action='store_true', help='실제로 지우고 다시 채움')
    args = ap.parse_args()
    firebase_admin.initialize_app(credentials.Certificate(CRED_PATH))
    db = firestore.client()

    if args.owner:
        u = auth.get_user_by_email(args.owner)
        ME.update(uid=u.uid, name=u.display_name or args.owner.split('@')[0])
    counts = {c: len(list(db.collection(c).select([]).stream())) for c in WIPE}
    print('지울 문서:', ', '.join(f'{c} {n}' for c, n in counts.items()))
    print(f'담당자(내 담당): {ME["name"]}')
    if not args.yes:
        print('\n--yes를 붙여 실행하면 백업 후 지우고 시연 데이터로 채웁니다.')
        return

    backup(db)
    wipe()
    cust, proj, asset = seed_inventory()
    T = seed_tickets(cust, asset)
    seed_parts(cust, asset, T)
    seed_jobs(cust, asset, T)
    seed_delivery(cust, asset)
    if args.owner and not list(db.collection('kb_articles').where('user_id', '==', ME['uid']).limit(1).stream()):
        for i, k in enumerate(KB):
            put('kb_articles', {**k, 'user_id': ME['uid']}, -60 + i * 10)
        print(f'KB {len(KB)}건 추가 ({ME["name"]})')
    print(f'완료: 고객사 {len(cust)} · 프로젝트 {len(proj)} · 장비 {len(asset)} · 티켓 {len(T)} (기준일 {TODAY:%Y-%m-%d})')


if __name__ == '__main__':
    main()
