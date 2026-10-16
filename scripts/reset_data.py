"""
customers, assets 컬렉션 전체 삭제
실행: docker compose exec app python scripts/reset_data.py
"""
import os, sys
import firebase_admin
from firebase_admin import credentials, firestore

CRED_PATH = os.path.join(os.path.dirname(__file__), '..', 'firebase-credentials.json')

def delete_collection(db, col, batch_size=100):
    coll_ref = db.collection(col)
    deleted = 0
    while True:
        docs = list(coll_ref.limit(batch_size).stream())
        if not docs:
            break
        for doc in docs:
            doc.reference.delete()
            deleted += 1
        if len(docs) < batch_size:
            break
    return deleted

def main():
    if not os.path.exists(CRED_PATH):
        print(f'ERROR: {CRED_PATH} not found', file=sys.stderr)
        sys.exit(1)
    cred = credentials.Certificate(CRED_PATH)
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    for col in ['customers', 'assets']:
        n = delete_collection(db, col)
        print(f'  ✓ {col}: {n}개 삭제')
    print('완료.')

if __name__ == '__main__':
    main()
