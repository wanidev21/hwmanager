"""
QA용 고객사-프로젝트-장비 테스트 데이터 시드
실행: docker compose exec app python scripts/seed_qa_data.py
"""
import os, sys, datetime
import firebase_admin
from firebase_admin import credentials, firestore

CRED_PATH = os.path.join(os.path.dirname(__file__), '..', 'firebase-credentials.json')

def main():
    cred = credentials.Certificate(CRED_PATH)
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    now = datetime.datetime.now(datetime.timezone.utc)

    def ts(): return firestore.SERVER_TIMESTAMP

    # ── 고객사 5곳 ─────────────────────────────────────────────
    customers = [
        {'name': '(주)한국인프라솔루션', 'contact': '김민준', 'phone': '02-3456-7890',
         'email': 'minjun.kim@kis.co.kr', 'address': '서울 강남구 테헤란로 152',
         'memo': 'HPE/DELL 서버 100대 이상 운영 고객'},
        {'name': '넥스트클라우드(주)', 'contact': '이서연', 'phone': '031-555-1234',
         'email': 'seoyeon@nextcloud.kr', 'address': '경기 성남시 분당구 판교로 255',
         'memo': 'DGX A100 클러스터 도입 고객'},
        {'name': '대한데이터센터', 'contact': '박지호', 'phone': '02-7890-1234',
         'email': 'jiho.park@ddc.co.kr', 'address': '서울 중구 을지로 100',
         'memo': '코로케이션 DC. 장비 200대 운영'},
        {'name': '글로벌바이오텍', 'contact': '정현우', 'phone': '042-678-9012',
         'email': 'hw.jung@gbt.co.kr', 'address': '대전 유성구 테크노2로 187',
         'memo': 'HPC 클러스터 연구소 고객'},
        {'name': '(주)스마트팩토리텍', 'contact': '최유나', 'phone': '051-345-6789',
         'email': 'yuna.choi@sft.co.kr', 'address': '부산 해운대구 센텀중앙로 55',
         'memo': '제조라인 엣지 서버 유지보수'},
    ]

    cust_ids = []
    for c in customers:
        ref = db.collection('customers').add({**c, 'created_at': ts(), 'updated_at': ts()})[1]
        cust_ids.append(ref.id)
        print(f'  ✓ 고객사: {c["name"]}')

    # ── 프로젝트 (고객사당 2~3개) ────────────────────────────────
    projects = [
        # 한국인프라솔루션
        {'cust_idx': 0, 'name': 'HPE ProLiant 서버 도입 1차', 'vendor': 'HPE',
         'device_type': '서버', 'quantity': 20,
         'install_date': '2022-03-15', 'warranty_expire': '2025-03-14',
         'memo': 'Gen10 Plus 랙형 서버 20대. 워런티 만료 임박'},
        {'cust_idx': 0, 'name': 'DELL PowerEdge 2차 증설', 'vendor': 'DELL',
         'device_type': '서버', 'quantity': 15,
         'install_date': '2023-07-01', 'warranty_expire': '2026-06-30',
         'memo': 'R750 시리즈 15대 증설'},
        # 넥스트클라우드
        {'cust_idx': 1, 'name': 'DGX A100 클러스터 구축', 'vendor': 'DGX',
         'device_type': 'GPU서버', 'quantity': 8,
         'install_date': '2023-11-20', 'warranty_expire': '2026-11-19',
         'memo': 'A100 80GB 8대. CUDA 12.3'},
        {'cust_idx': 1, 'name': 'InfiniBand 스위치 도입', 'vendor': 'DELL',
         'device_type': '스위치', 'quantity': 2,
         'install_date': '2023-11-20', 'warranty_expire': '2028-11-19',
         'memo': 'HDR 200Gb 스위치 2대'},
        # 대한데이터센터
        {'cust_idx': 2, 'name': 'HPE Synergy 컴포저블 인프라', 'vendor': 'HPE',
         'device_type': '서버', 'quantity': 30,
         'install_date': '2021-06-01', 'warranty_expire': '2024-05-31',
         'memo': '이미 만료됨. 갱신 협의 필요'},
        {'cust_idx': 2, 'name': 'Lenovo ThinkSystem 스토리지', 'vendor': 'Lenovo',
         'device_type': '스토리지', 'quantity': 4,
         'install_date': '2022-09-10', 'warranty_expire': '2025-09-09',
         'memo': 'DE4000H 올플래시 4대'},
        # 글로벌바이오텍
        {'cust_idx': 3, 'name': 'HPC 클러스터 구축', 'vendor': 'OEM',
         'device_type': 'GPU서버', 'quantity': 12,
         'install_date': '2024-01-15', 'warranty_expire': '2027-01-14',
         'memo': 'V100 32GB x4 노드 12대'},
        # 스마트팩토리텍
        {'cust_idx': 4, 'name': '엣지 서버 배포', 'vendor': 'DELL',
         'device_type': '서버', 'quantity': 6,
         'install_date': '2023-04-01', 'warranty_expire': '2026-03-31',
         'memo': 'PowerEdge R450 엣지 배포'},
    ]

    proj_ids = []
    for p in projects:
        data = {
            'customer_id':     cust_ids[p['cust_idx']],
            'name':            p['name'],
            'vendor':          p['vendor'],
            'device_type':     p['device_type'],
            'quantity':        p['quantity'],
            'install_date':    p['install_date'],
            'warranty_expire': p['warranty_expire'],
            'memo':            p['memo'],
            'created_at': ts(), 'updated_at': ts(),
        }
        ref = db.collection('projects').add(data)[1]
        proj_ids.append({'id': ref.id, 'cust_id': cust_ids[p['cust_idx']], 'name': p['name']})
        print(f'  ✓ 프로젝트: {p["name"]}')

    # ── 장비 (주요 프로젝트에 3~5대씩) ─────────────────────────────
    assets = [
        # DGX A100 클러스터 (proj_ids[2])
        {'proj_idx': 2, 'hostname': 'dgx-node-01', 'device_type': 'GPU서버',
         'model': 'DGX A100', 'serial': 'DGX-2023-001', 'location': 'Rack-A01-U1',
         'ip_address': '10.10.1.1', 'os': 'Ubuntu 20.04 LTS',
         'cpu': 'AMD EPYC 7742 x2', 'memory': '1TB DDR4',
         'gpu': 'NVIDIA A100 80GB x8', 'disk': 'NVMe 30TB',
         'bmc_version': '3.40.40', 'bios_version': '3.7.0',
         'driver_version': '525.147.05', 'install_date': '2023-11-20',
         'status': '운영중', 'memo': 'Primary AI Training Node'},
        {'proj_idx': 2, 'hostname': 'dgx-node-02', 'device_type': 'GPU서버',
         'model': 'DGX A100', 'serial': 'DGX-2023-002', 'location': 'Rack-A01-U5',
         'ip_address': '10.10.1.2', 'os': 'Ubuntu 20.04 LTS',
         'cpu': 'AMD EPYC 7742 x2', 'memory': '1TB DDR4',
         'gpu': 'NVIDIA A100 80GB x8', 'disk': 'NVMe 30TB',
         'bmc_version': '3.40.40', 'bios_version': '3.7.0',
         'driver_version': '525.147.05', 'install_date': '2023-11-20',
         'status': '운영중', 'memo': ''},
        {'proj_idx': 2, 'hostname': 'dgx-node-03', 'device_type': 'GPU서버',
         'model': 'DGX A100', 'serial': 'DGX-2023-003', 'location': 'Rack-A02-U1',
         'ip_address': '10.10.1.3', 'os': 'Ubuntu 20.04 LTS',
         'cpu': 'AMD EPYC 7742 x2', 'memory': '1TB DDR4',
         'gpu': 'NVIDIA A100 80GB x8', 'disk': 'NVMe 30TB',
         'bmc_version': '3.38.10', 'bios_version': '3.6.5',
         'driver_version': '525.147.05', 'install_date': '2023-11-20',
         'status': '장애', 'vendor_case_no': 'NV-2024-88821',
         'memo': 'GPU 1번 팬 이상. 벤더 케이스 접수'},
        # HPE ProLiant (proj_ids[0])
        {'proj_idx': 0, 'hostname': 'hpe-prod-01', 'device_type': '서버',
         'model': 'ProLiant DL380 Gen10 Plus', 'serial': 'HPE-2022-001',
         'location': 'Rack-B01-U1', 'ip_address': '10.20.1.1',
         'os': 'RHEL 8.6', 'cpu': 'Intel Xeon Gold 6338 x2', 'memory': '512GB DDR4',
         'disk': 'SAS 1.2TB x6', 'bmc_version': '2.98', 'bios_version': 'U30 v2.60',
         'driver_version': '', 'install_date': '2022-03-15',
         'status': '운영중', 'memo': 'DB 메인 서버'},
        {'proj_idx': 0, 'hostname': 'hpe-prod-02', 'device_type': '서버',
         'model': 'ProLiant DL380 Gen10 Plus', 'serial': 'HPE-2022-002',
         'location': 'Rack-B01-U3', 'ip_address': '10.20.1.2',
         'os': 'RHEL 8.6', 'cpu': 'Intel Xeon Gold 6338 x2', 'memory': '512GB DDR4',
         'disk': 'SAS 1.2TB x6', 'bmc_version': '2.98', 'bios_version': 'U30 v2.60',
         'driver_version': '', 'install_date': '2022-03-15',
         'status': '점검중', 'memo': 'iLO 접속 이슈 확인 중'},
        # DELL PowerEdge (proj_ids[1])
        {'proj_idx': 1, 'hostname': 'dell-app-01', 'device_type': '서버',
         'model': 'PowerEdge R750', 'serial': 'DELL-2023-001',
         'location': 'Rack-C01-U1', 'ip_address': '10.20.2.1',
         'os': 'Ubuntu 22.04 LTS', 'cpu': 'Intel Xeon Silver 4316 x2',
         'memory': '256GB DDR4', 'disk': 'NVMe 1.92TB x2',
         'bmc_version': '6.00.30', 'bios_version': '1.8.2',
         'driver_version': '', 'install_date': '2023-07-01',
         'status': '운영중', 'memo': 'WAS 서버 1번'},
        {'proj_idx': 1, 'hostname': 'dell-app-02', 'device_type': '서버',
         'model': 'PowerEdge R750', 'serial': 'DELL-2023-002',
         'location': 'Rack-C01-U3', 'ip_address': '10.20.2.2',
         'os': 'Ubuntu 22.04 LTS', 'cpu': 'Intel Xeon Silver 4316 x2',
         'memory': '256GB DDR4', 'disk': 'NVMe 1.92TB x2',
         'bmc_version': '6.00.30', 'bios_version': '1.8.2',
         'driver_version': '', 'install_date': '2023-07-01',
         'status': '운영중', 'memo': 'WAS 서버 2번'},
    ]

    for a in assets:
        p = proj_ids[a['proj_idx']]
        data = {
            'customer_id':    p['cust_id'],
            'project_id':     p['id'],
            'hostname':       a['hostname'],
            'device_type':    a['device_type'],
            'model':          a.get('model', ''),
            'serial':         a.get('serial', ''),
            'location':       a.get('location', ''),
            'ip_address':     a.get('ip_address', ''),
            'os':             a.get('os', ''),
            'status':         a.get('status', '운영중'),
            'cpu':            a.get('cpu', ''),
            'memory':         a.get('memory', ''),
            'gpu':            a.get('gpu', ''),
            'disk':           a.get('disk', ''),
            'bmc_version':    a.get('bmc_version', ''),
            'bios_version':   a.get('bios_version', ''),
            'driver_version': a.get('driver_version', ''),
            'install_date':   a.get('install_date', ''),
            'vendor_case_no': a.get('vendor_case_no', ''),
            'memo':           a.get('memo', ''),
            'created_at': ts(), 'updated_at': ts(),
        }
        db.collection('assets').add(data)
        print(f'  ✓ 장비: {a["hostname"]} ({p["name"]})')

    print(f'\n완료: 고객사 {len(customers)}개, 프로젝트 {len(projects)}개, 장비 {len(assets)}대')

if __name__ == '__main__':
    main()
