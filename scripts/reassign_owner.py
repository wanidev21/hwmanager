"""
개인 데이터(kb_articles / tech_* / releases / calendar_events)의 소유자(user_id)를
다른 계정으로 일괄 이전. 기본은 dry-run (변경 대상만 출력).

사용법:
  python scripts/reassign_owner.py old@example.com new@gmail.com            # 미리보기
  python scripts/reassign_owner.py old@example.com new@gmail.com --execute  # 실제 이전
되돌리기: 두 이메일 순서를 바꿔서 다시 실행
"""
import os
import sys
import argparse
import warnings

# Windows 콘솔/파이프에서 한글 깨짐 방지, Python 버전 지원 종료 안내 숨김
sys.stdout.reconfigure(encoding='utf-8')
warnings.filterwarnings('ignore', category=FutureWarning)

import firebase_admin
from firebase_admin import credentials, auth, firestore
from google.cloud.firestore_v1.base_query import FieldFilter

CRED_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'firebase-credentials.json')
COLLECTIONS = ['kb_articles', 'tech_domains', 'tech_topics', 'tech_notes', 'releases', 'calendar_events']


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('from_email')
    parser.add_argument('to_email')
    parser.add_argument('--execute', action='store_true', help='실제로 변경 (없으면 미리보기)')
    args = parser.parse_args()

    firebase_admin.initialize_app(credentials.Certificate(CRED_PATH))
    db = firestore.client()

    src = auth.get_user_by_email(args.from_email).uid
    dst = auth.get_user_by_email(args.to_email).uid
    print(f'{args.from_email} ({src}) -> {args.to_email} ({dst})')
    print('모드:', '실행' if args.execute else 'dry-run')

    total = 0
    for col in COLLECTIONS:
        docs = list(db.collection(col).where(filter=FieldFilter('user_id', '==', src)).stream())
        print(f'  {col}: {len(docs)}건')
        total += len(docs)
        if args.execute:
            batch = db.batch()
            for i, d in enumerate(docs, 1):
                batch.update(d.reference, {'user_id': dst})
                if i % 400 == 0:
                    batch.commit()
                    batch = db.batch()
            batch.commit()

    print(f'합계 {total}건', '이전 완료' if args.execute else '(변경 없음, --execute로 실행)')


if __name__ == '__main__':
    main()
