from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from extensions import db
from models.event import AlarmLog  # 정확한 경로로 수정
from routes import require_role

alarms_bp = Blueprint('alarms', __name__)

@alarms_bp.route('/')
@login_required
def index():
    # 현재 발생 중인 알람 (Active)
    active = AlarmLog.query.filter_by(state='active').order_by(AlarmLog.timestamp.desc()).all()
    # 이미 확인된 알람 (Acknowledged)
    acknowledged = AlarmLog.query.filter_by(state='acknowledged').order_by(AlarmLog.timestamp.desc()).limit(20).all()
    
    return render_template('alarms/index.html', active=active, acknowledged=acknowledged)

@alarms_bp.route('/acknowledge/<int:alarm_id>', methods=['POST'])
@login_required
@require_role('operator')
def acknowledge(alarm_id):
    alarm = AlarmLog.query.get_or_404(alarm_id)
    if alarm.state == 'active':
        alarm.state = 'acknowledged'
        alarm.acknowledged_at = datetime.utcnow()
        alarm.acknowledged_by = current_user.username
        db.session.commit()
        flash(f'알람 #{alarm_id}을 확인 처리했습니다.', 'success')
    return redirect(url_for('alarms.index'))