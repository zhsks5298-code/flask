import json
from datetime import datetime, timedelta
from flask import Blueprint, render_template
from flask_login import login_required
from sqlalchemy import func
from extensions import db
from models.inspection import InspectionResult
from models.event import AlarmLog, EventLog
from routes.sensors import api_data

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@login_required
def index():
    # 1. 최신 센서 데이터 (센서 API와 동일한 소스)
    sensor_response = api_data()
    sensor_json = json.loads(sensor_response.get_data(as_text=True))
    latest = sensor_json.get('latest', {})

    class SensorSnapshot:
        def __init__(self, d):
            self.temperature = d.get('temp')
            self.humidity = d.get('humidity')
            gas = float(d.get('gas', 0) or 0)
            self.gas_value = round(gas, 1)
            self.gas_status = 'normal' if gas < 400 else 'warning' if gas < 700 else 'danger'

    latest_sensor = SensorSnapshot(latest)

    # 2. 오늘 생산 통계 (PASS/DEFECT/HOLD)
    # ✅ datetime.utcnow() 로 통일 — DB 저장 기준과 일치
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    today_stats = db.session.query(
        InspectionResult.result,
        func.count(InspectionResult.id)
    ).filter(
        InspectionResult.timestamp >= today_start
    ).group_by(InspectionResult.result).all()

    stats = {'pass': 0, 'defect': 0, 'hold': 0}
    for result, count in today_stats:
        key = result.name if hasattr(result, 'name') else result
        key = key.lower()  # ← 이 한 줄 추가
        if key in stats:
            stats[key] = count
    stats['total'] = sum(stats.values())

    # 양품률 계산
    stats['yield_rate'] = round((stats['pass'] / stats['total'] * 100), 1) if stats['total'] > 0 else 0

    # 3. 활성 알람 (최근 5건)
    active_alarms = AlarmLog.query.filter_by(state='active')\
                            .order_by(AlarmLog.timestamp.desc()).limit(5).all()

    # 4. 최근 시스템 이벤트 (최근 8건)
    recent_events = EventLog.query.order_by(EventLog.timestamp.desc()).limit(8).all()

    return render_template('dashboard/index.html',
        latest_sensor=latest_sensor,
        stats=stats,
        active_alarms=active_alarms,
        recent_events=recent_events
    )
