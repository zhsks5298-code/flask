import os
import sys
import pymysql
import bcrypt
from datetime import datetime, timedelta
import random
from dotenv import load_dotenv

# 부모 폴더(루트 폴더)를 참조할 수 있게 경로 설정
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

load_dotenv()

def get_connection():
    return pymysql.connect(
        host='localhost',
        user='root',
        password=input("Enter MySQL root password: "),
        database='manufacturing',
        charset='utf8mb4'
    )

# --- [기존 기능 1] 제품 마스터 데이터 ---
def seed_product_master(cur):
    products = [
        ('transistor', '트랜지스터', 3, 'TO-92 패키지 3핀 트랜지스터', True),
        ('capacitor', '커패시터', 2, '전해 커패시터 2핀', True),
        ('regulator', '레귤레이터', 3, 'TO-220 패키지 3핀 레귤레이터', True),
        ('unknown', '미분류', None, 'YOLO가 분류 실패한 경우', True),
    ]
    for ptype, name, pins, desc, active in products:
        cur.execute("""
            INSERT IGNORE INTO product_master 
            (product_type, display_name, expected_pin_count, description, is_active)
            VALUES (%s, %s, %s, %s, %s)
        """, (ptype, name, pins, desc, active))

# --- [기존 기능 2] 시스템 설정값 ---
def seed_system_config(cur):
    configs = [
        ('temp_warning', '35', 'int', '°C', 'environment', '온도 경고 임계값', 0, 80),
        ('temp_critical', '40', 'int', '°C', 'environment', '온도 비상 임계값', 0, 80),
        # ... (나머지 설정값들은 동일하게 유지) ...
        ('login_lockout_minutes', '30', 'int', 'min', 'flask', '잠금 해제까지 대기', 5, 1440),
    ]
    for key, val, dtype, unit, cat, desc, mn, mx in configs:
        cur.execute("""
            INSERT IGNORE INTO system_config 
            (config_key, config_value, data_type, unit, category, description, min_value, max_value)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (key, val, dtype, unit, cat, desc, mn, mx))

# --- [기존 기능 3] 관리자 계정 ---
def seed_admin_user(cur):
    username = os.getenv('INITIAL_ADMIN_USERNAME', 'admin')
    password = os.getenv('INITIAL_ADMIN_PASSWORD', 'admin1234!')
    pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    cur.execute("""
        INSERT IGNORE INTO admin_users 
        (username, password_hash, full_name, role, is_active, password_changed_at)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (username, pw_hash, 'System Admin', 'admin', True, datetime.now()))

# --- [새 기능] 테스트용 실시간 데이터 (Dashboard 확인용) ---
def seed_live_data(cur):
    print("Seeding live monitoring data (Sensors, Inspections, Alarms)...")
    
    # 1. 센서 데이터
    for _ in range(10):
        cur.execute("""
            INSERT INTO sensor_readings (temperature, humidity, gas_value, gas_status, source, timestamp)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (random.uniform(22, 28), random.uniform(40, 60), random.randint(200, 400), 'normal', 'RPi_01', datetime.utcnow()))

    # 2. 검사 결과
    results = ['pass', 'defect', 'hold']
    for i in range(15):
        res = random.choice(results)
        cur.execute("""
            INSERT INTO inspection_results (product_type, product_id, result, yolo_confidence, timestamp)
            VALUES (%s, %s, %s, %s, %s)
        """, ('transistor', f"SN-2026-{100+i}", res, random.uniform(0.85, 0.99), datetime.utcnow()))

    # 3. 알람
    cur.execute("""
        INSERT INTO alarm_log (alarm_type, severity, message, source, state, timestamp)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, ('high_temp', 'critical', '서버룸 온도 과열 감지!', 'sensor_01', 'active', datetime.utcnow()))

def main():
    conn = get_connection()
    cur = conn.cursor()
    
    print("Step 1: Seeding Master Data...")
    seed_product_master(cur)
    seed_system_config(cur)
    seed_admin_user(cur)
    
    print("Step 2: Seeding Live Test Data...")
    seed_live_data(cur)
    
    conn.commit()
    cur.close()
    conn.close()
    print("🚀 All Done! 데이터베이스 설정 및 테스트 데이터 주입이 완료되었습니다.")

if __name__ == '__main__':
    main()