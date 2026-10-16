"""
지정한 계정을 관리자(role: admin)로 설정. users/{uid} 문서가 없으면 생성.

사용법:
  python scripts/set_admin.py karismawan1977@gmail.com
  python scripts/set_admin.py someone@gmail.com --role user   # 관리자 해제
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

CRED_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'firebase-credentials.json')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('email')
    parser.add_argument('--role', default='admin', choices=['admin', 'user'])
    args = parser.parse_args()

    firebase_admin.initialize_app(credentials.Certificate(CRED_PATH))
    db = firestore.client()

    user = auth.get_user_by_email(args.email)
    ref = db.collection('users').document(user.uid)
    data = {'email': user.email, 'role': args.role}
    if not ref.get().exists:
        data.update({
            'displayName': user.display_name or '',
            'photoURL':    user.photo_url or '',
            'created_at':  firestore.SERVER_TIMESTAMP,
        })
    ref.set(data, merge=True)
    print(f'{user.email} ({user.uid}) -> role: {args.role}')


if __name__ == '__main__':
    main()
