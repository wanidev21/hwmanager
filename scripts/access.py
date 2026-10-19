"""
로그인 허용 계정 관리 (Firestore config/access 문서의 emails 목록).
보안 규칙(firestore.rules의 allowed())과 앱 로그인 검사가 이 목록을 사용한다.
코드·저장소에 이메일을 두지 않기 위해 데이터베이스에 보관.

사용법:
  python scripts/access.py list
  python scripts/access.py add someone@gmail.com
  python scripts/access.py remove someone@gmail.com

※ Google Cloud 콘솔 OAuth 동의 화면의 '테스트 사용자'에도 같은 계정을 추가해야 로그인 가능
   (Calendar 민감 스코프 때문에 테스트 모드)
"""
import os
import sys
import argparse
import warnings

sys.stdout.reconfigure(encoding='utf-8')
warnings.filterwarnings('ignore', category=FutureWarning)

import firebase_admin
from firebase_admin import credentials, firestore

CRED_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'firebase-credentials.json')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['list', 'add', 'remove'])
    parser.add_argument('email', nargs='?')
    args = parser.parse_args()
    if args.command != 'list' and not args.email:
        parser.error('이메일을 입력하세요')

    firebase_admin.initialize_app(credentials.Certificate(CRED_PATH))
    ref = firestore.client().collection('config').document('access')
    snap = ref.get()
    emails = list((snap.to_dict() or {}).get('emails', [])) if snap.exists else []

    if args.command == 'add':
        e = args.email.strip().lower()
        if e not in emails:
            emails.append(e)
    elif args.command == 'remove':
        e = args.email.strip().lower()
        emails = [x for x in emails if x != e]

    if args.command != 'list':
        ref.set({'emails': emails, 'updated_at': firestore.SERVER_TIMESTAMP}, merge=True)

    print(f'허용 계정 {len(emails)}개')
    for e in emails:
        print(' -', e)


if __name__ == '__main__':
    main()
