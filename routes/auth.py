from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
import bcrypt
from extensions import db
from models import User, EventLog, LoginHistory

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        user = User.query.filter_by(username=username).first()
        ip = request.remote_addr
        ua = request.headers.get('User-Agent', '')[:255]
        
        # 사용자 없음
        if not user:
            db.session.add(LoginHistory(
                username=username, event_type='login_fail',
                ip_address=ip, user_agent=ua, fail_reason='user_not_found'
            ))
            db.session.commit()
            flash('로그인 정보가 올바르지 않습니다.', 'danger')
            return render_template('auth/login.html')
        
        # 계정 잠금 확인
        if user.is_locked():
            flash('계정 잠금. 잠금 해제까지 대기 필요.', 'danger')
            return render_template('auth/login.html')
        
        # 비밀번호 확인
        if not bcrypt.checkpw(password.encode(), user.password_hash.encode()):
            user.failed_login_count += 1
            if user.failed_login_count >= 5:
                user.locked_until = datetime.utcnow() + timedelta(minutes=30)
            
            db.session.add(LoginHistory(
                username=username, user_id=user.id, event_type='login_fail',
                ip_address=ip, user_agent=ua, fail_reason='wrong_password'
            ))
            db.session.commit()
            flash('로그인 정보가 올바르지 않습니다.', 'danger')
            return render_template('auth/login.html')
        
        # 비활성 계정
        if not user.is_active:
            flash('비활성화된 계정입니다.', 'warning')
            return render_template('auth/login.html')
        
        # 로그인 성공
        user.failed_login_count = 0
        user.locked_until = None
        user.last_login_at = datetime.utcnow()
        
        db.session.add(LoginHistory(
            username=username, user_id=user.id, event_type='login_success',
            ip_address=ip, user_agent=ua
        ))
        db.session.commit()  # User + LoginHistory 먼저 커밋

        # ✅ EventLog.write() 사용 — hash chain 유지
        EventLog.write(
            event_type='user_login',
            severity='info',
            source='flask.auth',
            message=f'{username} 로그인 (IP: {ip})',
            actor=username
        )
        
        login_user(user)
        return redirect(url_for('dashboard.index'))
    
    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    username = current_user.username
    
    db.session.add(LoginHistory(
        username=username, user_id=current_user.id, event_type='logout',
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent', '')[:255]
    ))
    db.session.commit()  # LoginHistory 먼저 커밋

    # ✅ EventLog.write() 사용 — hash chain 유지
    EventLog.write(
        event_type='user_logout',
        severity='info',
        source='flask.auth',
        message=f'{username} 로그아웃',
        actor=username
    )
    
    logout_user()
    flash('로그아웃 되었습니다.', 'info')
    return redirect(url_for('auth.login'))
