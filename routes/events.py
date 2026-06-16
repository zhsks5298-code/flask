from flask import Blueprint, render_template, request
from flask_login import login_required
from models.event import EventLog
from extensions import db
from routes import require_role

events_bp = Blueprint('events', __name__)

@events_bp.route('/')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    sev = request.args.get('severity', '')
    etype = request.args.get('event_type', '')

    q = EventLog.query

    if sev:
        q = q.filter_by(severity=sev)
    if etype:
        q = q.filter_by(event_type=etype)

    pagination = q.order_by(EventLog.timestamp.desc()).paginate(
        page=page, per_page=50, error_out=False
    )

    # event_type 목록을 DB에서 동적으로 가져오기
    event_types = db.session.query(EventLog.event_type).distinct().order_by(EventLog.event_type).all()
    event_types = [e[0] for e in event_types]

    return render_template('events/index.html',
                           pagination=pagination,
                           sev=sev,
                           etype=etype,
                           event_types=event_types)

@events_bp.route('/audit')
@login_required
@require_role('maintainer')
def audit():
    page = request.args.get('page', 1, type=int)
    logs = EventLog.query.order_by(EventLog.id.desc()).paginate(
        page=page, per_page=50, error_out=False
    )
    return render_template('events/audit.html', logs=logs)