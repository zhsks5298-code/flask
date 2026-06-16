from app import create_app
from extensions import db
from models import User

app = create_app()
with app.app_context():
    # admin 사용자 찾기
    user = User.query.filter_by(username='admin').first()
    if user:
        user.failed_login_count = 0
        user.locked_until = None
        db.session.commit()
        print("성공! admin 계정의 잠금이 해제되었습니다.")
    else:
        print("오류: admin 계정을 찾을 수 없습니다.")