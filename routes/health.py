from datetime import datetime, timedelta
from flask import Blueprint, render_template
from flask_login import login_required
from sqlalchemy import text
from extensions import db
from models.sensor import SensorReading  # 경로 상세화
from models.event import EventLog        # 경로 상세화

health_bp = Blueprint('health', __name__)

@health_bp.route('/')
@login_required
def index():
    # 1. DB 상태 체크
    try:
        db.session.execute(text('SELECT 1'))
        db_ok = True
    except Exception:
        db_ok = False

    # 2. 라즈베리파이(엣지 장치) 통신 상태 체크
    latest = SensorReading.query.order_by(SensorReading.timestamp.desc()).first()
    rpi_ok = False
    rpi_age = None
    if latest:
        # 마지막 수신 데이터와의 시간 차이 계산
        rpi_age = int((datetime.utcnow() - latest.timestamp).total_seconds())
        rpi_ok = rpi_age < 60 # 60초 이내 데이터가 있으면 정상

    # 3. 최근 1시간 이내 심각한 에러 발생 건수
    since = datetime.utcnow() - timedelta(hours=1)
    error_count = EventLog.query.filter(
        EventLog.severity.in_(['critical', 'emergency']),
        EventLog.timestamp >= since
    ).count()

    return render_template('health/index.html',
        db_ok=db_ok, rpi_ok=rpi_ok, rpi_age=rpi_age, error_count=error_count)