from flask import Blueprint, render_template, request
from flask_login import login_required
from models.inspection import SortingResult
from extensions import db

sorting_bp = Blueprint('sorting', __name__)

@sorting_bp.route('/')
@login_required
def index():
    # 1. 파라미터 가져오기
    page = request.args.get('page', 1, type=int)
    filter_v = request.args.get('verification_result', '')

    # 2. 기본 쿼리
    query = SortingResult.query

    # 3. 필터링 로직 (HTML의 select name="verification_result"와 매칭)
    if filter_v:
        query = query.filter(SortingResult.verification_result == filter_v)

    # 4. 페이지네이션 (10개씩 최신순)
    pagination = query.order_by(SortingResult.timestamp.desc()).paginate(
        page=page, per_page=10, error_out=False
    )

    return render_template('sorting/index.html', 
                           pagination=pagination, 
                           filter_v=filter_v)