"""
통계 페이지 — KPI 카드 4개 + 차트 3개.

차트는 페이지 진입 시 서버에서 한 번에 다 계산해 템플릿에 박아 넣음.
(별도 API 호출 없음. 5초 polling 필요해지면 그때 /stats/api/* 추가.)
"""
from datetime import datetime, timedelta
from flask import Blueprint, render_template
from flask_login import login_required
from sqlalchemy import func
from extensions import db
from models.inspection import InspectionResult

stats_bp = Blueprint('stats', __name__)


@stats_bp.route('/')
@login_required
def index():
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    hour_ago    = now - timedelta(hours=1)
    day_ago     = now - timedelta(hours=24)

    # ────────────────────────────────────────────────────
    # 1. 오늘 verdict 분포 (도넛 차트)
    # ────────────────────────────────────────────────────
    today_rows = db.session.query(
        InspectionResult.result,
        func.count(InspectionResult.id),
    ).filter(
        InspectionResult.timestamp >= today_start
    ).group_by(InspectionResult.result).all()

    verdict_counts = {'pass': 0, 'defect': 0, 'hold': 0}
    for r, c in today_rows:
        key = r.value if hasattr(r, 'value') else (r.name if hasattr(r, 'name') else str(r))
        key = key.lower()
        if key in verdict_counts:
            verdict_counts[key] = c

    today_total = sum(verdict_counts.values())
    pass_rate   = round(verdict_counts['pass'] / today_total * 100, 1) if today_total else 0.0

    # ────────────────────────────────────────────────────
    # 2. KPI: 시간당 처리량 (최근 1h), 평균 추론 시간 (오늘)
    # ────────────────────────────────────────────────────
    hourly_rate = db.session.query(func.count(InspectionResult.id)).filter(
        InspectionResult.timestamp >= hour_ago
    ).scalar() or 0

    avg_inference_ms = db.session.query(
        func.avg(InspectionResult.inference_time_ms)
    ).filter(
        InspectionResult.timestamp >= today_start,
        InspectionResult.inference_time_ms.isnot(None),
    ).scalar()
    avg_inference_ms = round(float(avg_inference_ms), 1) if avg_inference_ms else 0.0

    kpi = {
        'pass_rate':       pass_rate,
        'today_total':     today_total,
        'hourly_rate':     hourly_rate,
        'avg_inference':   avg_inference_ms,
    }

    # ────────────────────────────────────────────────────
    # 3. 최근 24h 시간당 처리량 (라인 차트)
    # ────────────────────────────────────────────────────
    hourly_rows = db.session.execute(db.text("""
        SELECT DATE_FORMAT(timestamp, '%Y-%m-%d %H:00') AS bucket,
               COUNT(*) AS cnt
        FROM inspection_results
        WHERE timestamp >= :since
        GROUP BY bucket
        ORDER BY bucket ASC
    """), {'since': day_ago}).fetchall()

    hourly_labels = [r[0][-5:] for r in hourly_rows]   # 'HH:00' 만 추출
    hourly_counts = [r[1] for r in hourly_rows]

    # ────────────────────────────────────────────────────
    # 4. 제품별 처리량 (오늘) — 막대 차트
    # ────────────────────────────────────────────────────
    product_rows = db.session.query(
        InspectionResult.product_type,
        func.count(InspectionResult.id),
    ).filter(
        InspectionResult.timestamp >= today_start,
        InspectionResult.product_type.isnot(None),
    ).group_by(InspectionResult.product_type).all()

    product_labels = []
    product_counts = []
    for pt, c in product_rows:
        key = pt.value if hasattr(pt, 'value') else (pt.name if hasattr(pt, 'name') else str(pt))
        product_labels.append(key)
        product_counts.append(c)

    return render_template(
        'stats/index.html',
        kpi=kpi,
        verdict_counts=verdict_counts,
        hourly_labels=hourly_labels,
        hourly_counts=hourly_counts,
        product_labels=product_labels,
        product_counts=product_counts,
    )
