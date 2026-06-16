"""
admin 계정 생성 / 비밀번호 재설정 스크립트.

사용 예:
    python scripts/create_admin.py                    # 인터랙티브
    python scripts/create_admin.py --username admin   # 비밀번호만 인터랙티브
    python scripts/create_admin.py --username admin --password 'NewPass!23'
    python scripts/create_admin.py --reset            # 잠금 해제 + 실패 횟수 초기화
"""
import os
import sys
import argparse
import getpass
from datetime import datetime

import bcrypt
from dotenv import load_dotenv

# 프로젝트 루트를 import path 에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

from app import create_app                                   # noqa: E402
from extensions import db                                    # noqa: E402
from models import User                                      # noqa: E402


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt(rounds=12)).decode()


def upsert_admin(username: str, password: str, role: str = 'admin',
                 full_name: str = 'System Admin'):
    user = User.query.filter_by(username=username).first()
    now = datetime.utcnow()

    if user is None:
        user = User(
            username=username,
            password_hash=hash_password(password),
            full_name=full_name,
            role=role,
            is_active=True,
            created_at=now,
            password_changed_at=now,
            failed_login_count=0,
            locked_until=None,
        )
        db.session.add(user)
        db.session.commit()
        print(f"[+] Created user: {username} (role={role})")
    else:
        user.password_hash = hash_password(password)
        user.role = role
        user.is_active = True
        user.password_changed_at = now
        user.failed_login_count = 0
        user.locked_until = None
        db.session.commit()
        print(f"[~] Updated user: {username} "
              f"(role={role}, lock cleared, password reset)")


def reset_lock(username: str):
    user = User.query.filter_by(username=username).first()
    if user is None:
        print(f"[!] User not found: {username}")
        return
    user.failed_login_count = 0
    user.locked_until = None
    db.session.commit()
    print(f"[+] Lock cleared: {username}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--username', '-u',
                        default=os.getenv('INITIAL_ADMIN_USERNAME', 'admin'))
    parser.add_argument('--password', '-p', default=None,
                        help='평문 비밀번호 (생략 시 인터랙티브 입력)')
    parser.add_argument('--role', '-r', default='admin',
                        choices=['viewer', 'operator', 'maintainer', 'admin'])
    parser.add_argument('--full-name', '-n', default='System Admin')
    parser.add_argument('--reset', action='store_true',
                        help='기존 사용자 잠금 해제 + 실패 횟수만 초기화')
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        if args.reset:
            reset_lock(args.username)
            return

        password = args.password or os.getenv('INITIAL_ADMIN_PASSWORD')
        if not password:
            password = getpass.getpass(f"비밀번호 입력 ({args.username}): ")
            confirm  = getpass.getpass("비밀번호 다시 입력: ")
            if password != confirm:
                print("[!] 비밀번호가 일치하지 않습니다.")
                sys.exit(1)
        if len(password) < 8:
            print("[!] 비밀번호는 최소 8자 이상이어야 합니다.")
            sys.exit(1)

        upsert_admin(args.username, password, args.role, args.full_name)


if __name__ == '__main__':
    main()
