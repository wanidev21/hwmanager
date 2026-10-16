"""
kb_articles / tech_domains / tech_topics / tech_notes / releases
→ user_id 없는 기존 문서에 현재 로그인 유저의 uid를 일괄 기록
"""
import os
import sys
import firebase_admin
from firebase_admin import credentials, firestore, auth

CRED_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'firebase-credentials.json')
COLLECTIONS = ['kb_articles', 'tech_domains', 'tech_topics', 'tech_notes', 'releases']

def migrate(target_email: str):
    cred = credentials.Certificate(CRED_PATH)
    firebase_admin.initialize_app(cred)
    db = firestore.client()

    user = auth.get_user_by_email(target_email)
    uid  = user.uid
    print(f"대상 유저: {target_email}  UID: {uid}\n")

    total = 0
    for col in COLLECTIONS:
        docs = list(db.collection(col).stream())
        migrated = 0
        for doc in docs:
            data = doc.to_dict()
            if not data.get('user_id'):
                db.collection(col).document(doc.id).update({'user_id': uid})
                migrated += 1
        total += migrated
        print(f"  {col:<22}: {len(docs)}개 문서 중 {migrated}개 이전")

    print(f"\n완료: 총 {total}개 문서에 user_id 기록됨")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('사용법: python scripts/migrate_user_owned_collections.py <대상 이메일>')
        sys.exit(1)
    migrate(sys.argv[1])
