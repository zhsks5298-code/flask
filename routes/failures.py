"""
실패 사례 갤러리 (defect / hold) — 운영자/품질팀 검토용.

데이터 소스: inspection_results (DB) — A안.
D 멤버가 별도로 만드는 failure_gallery.html 정적 산출물은
나중에 templates/failures/external.html 또는 iframe 으로 임베드.
"""
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request
from flask_login import login_required
from models.inspection import InspectionResult

failures_bp = Blueprint('failures', __name__)


@failures_bp.route('/')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    result_filter   = request.args.get('result', 'all')      # all / defect / hold
    product_filter  = request.args.get('product_type', '')   # ''(전체) / 모델별
    period_filter   = request.args.get('period', 'week')     # today / week / month / all

    query = InspectionResult.query

    # 1. result 필터 (기본은 defect+hold 둘 다)
    if result_filter == 'defect':
        query = query.filter(func.lower(InspectionResult.result) == 'defect')
    elif result_filter == 'hold':
        query = query.filter(InspectionResult.result == 'hold')
    else:  # all
        query = query.filter(InspectionResult.result.in_(['defect', 'hold']))

    # 2. product_type 필터
    if product_filter:
        query = query.filter(InspectionResult.product_type == product_filter)

    # 3. 기간 필터
    now = datetime.utcnow()
    if period_filter == 'today':
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        query = query.filter(InspectionResult.timestamp >= start)
    elif period_filter == 'week':
        query = query.filter(InspectionResult.timestamp >= now - timedelta(days=7))
    elif period_filter == 'month':
        query = query.filter(InspectionResult.timestamp >= now - timedelta(days=30))
    # 'all' 은 필터 안 걸음

    pagination = query.order_by(InspectionResult.timestamp.desc()).paginate(
        page=page, per_page=24, error_out=False
    )

    # 카운트 요약 (현재 필터 기준)
    total_defect = sum(1 for i in pagination.items if i.result == 'defect')
    total_hold   = sum(1 for i in pagination.items if i.result == 'hold')

    return render_template(
        'failures/index.html',
        pagination=pagination,
        result_filter=result_filter,
        product_filter=product_filter,
        period_filter=period_filter,
        total_defect=total_defect,
        total_hold=total_hold,
    )
