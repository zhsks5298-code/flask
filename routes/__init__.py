from functools import wraps
from flask import redirect, url_for, flash
from flask_login import current_user

def require_role(role: str):
    """최소 역할 요구 데코레이터. viewer < operator < maintainer < admin"""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not current_user.has_role(role):
                flash(f'이 기능은 {role} 이상 권한이 필요합니다.', 'warning')
                return redirect(url_for('dashboard.index'))
            return f(*args, **kwargs)
        return wrapper
    return decorator