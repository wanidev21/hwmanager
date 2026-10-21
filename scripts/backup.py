"""
Firestore 전체 백업 → backups/YYYYMMDD-HHMMSS.json (저장소에 올라가지 않음)
무료: 서비스 계정 키로 읽기만 함 (Firebase 유료 백업 기능 불필요)

사용법:
  python scripts/backup.py              # 전체
  python scripts/backup.py --out D:/bk  # 저장 위치 지정

복원은 아직 없음 — 필요하면 JSON에서 문서 단위로 되살릴 수 있음 (컬렉션/문서id/필드 구조 그대로)
"""
import os
import sys
import json
import argparse
import warnings
from datetime import datetime, date

sys.stdout.reconfigure(encoding='utf-8')
warnings.filterwarnings('ignore', category=FutureWarning)

import firebase_admin
from firebase_admin import credentials, firestore

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
CRED_PATH = os.path.join(ROOT, 'firebase-credentials.json')


def _val(v):
    if isinstance(v, (datetime, date)):
        return {'__ts': v.isoformat()}
    if hasattr(v, 'path') and hasattr(v, 'id'):          # DocumentReference
        return {'__ref': v.path}
    if isinstance(v, dict):
        return {k: _val(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_val(x) for x in v]
    if isinstance(v, bytes):
        return {'__bytes': len(v)}
    return v


def dump_collection(col_ref):
    out = {}
    for snap in col_ref.stream():
        doc = {'data': _val(snap.to_dict() or {})}
        subs = {c.id: dump_collection(c) for c in snap.reference.collections()}
        if subs:
            doc['sub'] = subs
        out[snap.id] = doc
    return out


def backup(db, out_dir=None):
    out_dir = out_dir or os.path.join(ROOT, 'backups')
    os.makedirs(out_dir, exist_ok=True)
    data, total = {}, 0
    for col in db.collections():
        data[col.id] = dump_collection(col)
        total += len(data[col.id])
    path = os.path.join(out_dir, datetime.now().strftime('%Y%m%d-%H%M%S') + '.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump({'created_at': datetime.now().isoformat(), 'collections': data}, f, ensure_ascii=False, indent=1)
    print(f'백업: {len(data)}개 컬렉션, 문서 {total}개 → {os.path.relpath(path, ROOT)}')
    return path


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--out')
    args = ap.parse_args()
    firebase_admin.initialize_app(credentials.Certificate(CRED_PATH))
    backup(firestore.client(), args.out)
