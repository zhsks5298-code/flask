from flask import Blueprint, render_template, request
from flask_login import login_required
from models.inspection import InspectionResult 
from extensions import db
from datetime import datetime

inspections_bp = Blueprint('inspections', __name__)

@inspections_bp.route('/')
@login_required
def index():
    # 1. 브라우저에서 넘어온 페이지 번호 및 필터값 읽기
    page = request.args.get('page', 1, type=int)
    result_filter = request.args.get('result', '')
    product_filter = request.args.get('product_type', '')

    # 2. 기본 쿼리 설정 (InspectionResult 모델 사용)
    query = InspectionResult.query

    # 3. 필터 조건이 있다면 쿼리에 추가
    if result_filter:
        query = query.filter(InspectionResult.result == result_filter)
    if product_filter:
        query = query.filter(InspectionResult.product_type == product_filter)

    # 4. 중요: pagination 객체 생성 (HTML에서 'pagination'이라는 이름을 기대함)
    # 한 페이지에 10개씩 최신순으로 정렬하여 가져옵니다.
    pagination = query.order_by(InspectionResult.timestamp.desc()).paginate(
        page=page, per_page=10, error_out=False
    )

    # 5. HTML로 변수 전달 (여기서 변수명이 pagination이어야 에러가 안 남)
    return render_template('inspections/index.html', 
                           pagination=pagination, 
                           result_filter=result_filter, 
                           product_filter=product_filter)

@inspections_bp.route('/<int:id>')
@login_required
def detail(id):
    # correlation_id로 먼저 조회 시도, 없으면 inspection_id로 폴백
    record = InspectionResult.query.get_or_404(id)
    
    # 관련 sorting 결과 조회 (correlation_id 우선, inspection_id 폴백)
    from models.inspection import SortingResult
    sorting = None
    if record.correlation_id:
        sorting = SortingResult.query.filter_by(correlation_id=record.correlation_id).first()
    if not sorting:
        sorting = SortingResult.query.filter_by(inspection_id=record.id).first()
    
    return render_template('inspections/detail.html', i=record, insp=record, sorting=sorting)