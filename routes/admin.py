from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from models import User, ProductMaster, SystemConfig
from routes import require_role

admin_bp = Blueprint('admin', __name__)

# def admin_required(f):
#     @wraps(f)
#     def wrapper(*args, **kwargs):
#         if not current_user.has_role('admin'):
#             flash('관리자 권한이 필요합니다.', 'danger')
#             return redirect(url_for('dashboard.index'))
#         return f(*args, **kwargs)
#     return wrapper

@admin_bp.route('/')
@login_required
@require_role('admin')
def index():
    return redirect(url_for('admin.users'))

@admin_bp.route('/users')
@login_required
@require_role('admin')
def users():
    all_users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=all_users)

@admin_bp.route('/products')
@login_required
@require_role('admin')
def products():
    all_products = ProductMaster.query.order_by(ProductMaster.id).all()
    return render_template('admin/products.html', products=all_products)

@admin_bp.route('/config')
@login_required
@require_role('admin')
def config():
    all_configs = SystemConfig.query.order_by(SystemConfig.category, SystemConfig.config_key).all()
    
    # 카테고리별로 그룹핑
    grouped = {}
    for c in all_configs:
        cat = c.category or '기타'
        if cat not in grouped:
            grouped[cat] = []
        grouped[cat].append(c)
    
    return render_template('admin/config.html', grouped=grouped)