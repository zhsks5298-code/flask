"""
fake_data.py — 시연용 가짜 데이터 생성 스크립트
30일치 센서 + 검사 + 분류 + 이벤트 + 알람 데이터를 생성합니다.
개발/시연 중에만 사용하세요. 운영 환경에서 실행 금지!

가스 기준:
  - 0~9   : 정상 (normal)
  - 10~39 : 위험 (warning)
  - 40+   : 비상 (critical)

사용법:
    cd Flask
    python scripts/fake_data.py
    → MySQL root 비밀번호 입력
"""

import os
import sys
import pymysql
import random
import uuid
from datetime import datetime, timedelta

# 프로젝트 루트를 path에 추가
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))


def get_connection():
    return pymysql.connect(
        host='localhost',
        user='root',
        password=input("Enter MySQL root password: "),
        database='manufacturing',
        charset='utf8mb4'
    )


def fake_sensor_readings(cur, count=15000):
    """30일치 센서 데이터 (온도/습도/가스)"""
    print(f"  센서 데이터 {count}건 생성 중...")
    now = datetime.now()

    for i in range(count):
        ts = now - timedelta(seconds=(count - i) * 172)
        temp = round(23 + random.gauss(0, 2), 1)
        hum = round(52 + random.gauss(0, 5), 1)

        roll = random.random()
        if roll < 0.85:
            gas = round(random.uniform(1, 9), 1)
        elif roll < 0.95:
            gas = round(random.uniform(10, 39), 1)
        else:
            gas = round(random.uniform(40, 55), 1)

        if random.random() < 0.03:
            temp = round(random.uniform(36, 42), 1)

        if gas >= 40:
            status = 'critical'
        elif gas >= 10:
            status = 'warning'
        else:
            status = 'normal'

        cur.execute("""
            INSERT INTO sensor_readings
            (timestamp, temperature, humidity, gas_value, gas_status, source, quality)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (ts, temp, hum, gas, status, 'RPi_01', 'good'))


def fake_inspections(cur, count=9000):
    """30일치 검사 결과 + 분류 결과"""
    print(f"  검사/분류 데이터 {count}건 생성 중...")
    now = datetime.now()

    product_types = ['transistor', 'capacitor', 'regulator']
    defect_details = [
        'pin_bent', 'solder_bridge', 'missing_pin', 'crack',
        'surface_scratch', 'misalignment', None, None, None
    ]

    for i in range(count):
        ts = now - timedelta(seconds=(count - i) * 288)
        ptype = random.choice(product_types)
        corr_id = str(uuid.uuid4())
        result = random.choices(['pass', 'defect', 'hold'], weights=[98, 1, 1])[0]
        yolo_conf = round(random.uniform(0.65, 0.99), 3)
        final_conf = round(yolo_conf + random.uniform(-0.05, 0.05), 3)
        final_conf = max(0.0, min(1.0, final_conf))

        defect = random.choice(defect_details) if result == 'defect' else None
        cam2 = result == 'hold' or (result == 'defect' and random.random() < 0.3)
        inference = random.randint(25, 120)

        cur.execute("""
            INSERT INTO inspection_results
            (timestamp, correlation_id, product_type, product_id, result, yolo_class, yolo_confidence,
             final_confidence, defect_detail, cam2_used, inference_time_ms, model_version,
             environment_temp, environment_humidity)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            ts, corr_id, ptype, f"SN-2026-{1000+i}", result, ptype, yolo_conf,
            final_conf, defect, cam2, inference, 'yolov8n_v2',
            round(23 + random.gauss(0, 1), 1),
            round(52 + random.gauss(0, 3), 1)
        ))

        insp_id = cur.lastrowid

        sensor_map = {'pass': 'S6', 'defect': 'S4', 'hold': 'S5'}
        expected_sensor = sensor_map[result]
        verify = random.choices(
            ['success', 'wrong_bin', 'timeout', 'skipped'],
            weights=[90, 4, 4, 2]
        )[0]
        actual = expected_sensor if verify == 'success' else random.choice(['S4', 'S5', 'S6', 'none'])
        timing = random.randint(400, 2500)

        cur.execute("""
            INSERT INTO sorting_results
            (inspection_id, correlation_id, timestamp, expected_route, actual_sensor,
             expected_sensor, verification_result, timing_ms)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (insp_id, corr_id, ts, result, actual, expected_sensor, verify, timing))


def fake_events(cur, count=1500):
    """30일치 시스템 이벤트 로그"""
    print(f"  이벤트 로그 {count}건 생성 중...")
    now = datetime.now()

    event_templates = [
        ('state_transition', 'info', 'system', 'IDLE → RUNNING 전환', 'system'),
        ('state_transition', 'info', 'system', 'RUNNING → IDLE 전환', 'system'),
        ('inspection_complete', 'info', 'yolo_engine', '배치 검사 50건 완료', 'system'),
        ('model_loaded', 'info', 'yolo_engine', 'yolov8n_v2 모델 로드 완료', 'system'),
        ('sensor_warning', 'warning', 'safety_monitor', '가스 농도 15ppm 경고 수준', 'system'),
        ('sensor_critical', 'critical', 'safety_monitor', '가스 농도 45ppm 비상 수준', 'system'),
        ('sorting_error', 'warning', 'sorting_verifier', '분류 검증 타임아웃 발생', 'system'),
        ('rpi_reconnect', 'warning', 'mqtt_handler', 'RPi MQTT 재연결됨', 'system'),
        ('user_login', 'info', 'flask.auth', 'admin 로그인', 'admin'),
        ('user_logout', 'info', 'flask.auth', 'admin 로그아웃', 'admin'),
        ('config_changed', 'info', 'flask.admin', 'gas_warning 값 변경: 10→15', 'admin'),
        ('conveyor_stop', 'critical', 'arduino_serial', 'E-stop 버튼 눌림', 'system'),
        ('conveyor_start', 'info', 'arduino_serial', '컨베이어 재시작', 'operator'),
    ]

    for i in range(count):
        ts = now - timedelta(seconds=(count - i) * 1728)
        template = random.choice(event_templates)
        etype, sev, src, msg, actor = template

        cur.execute("""
            INSERT INTO event_log
            (timestamp, event_type, severity, source, message, actor)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (ts, etype, sev, src, msg, actor))


def fake_alarms(cur):
    """알람 데이터 — active 2건 + acknowledged 3건"""
    print("  알람 데이터 생성 중...")
    now = datetime.now()

    active_alarms = [
        ('high_temp', 'critical', '서버룸 온도 38.5°C — 임계값 초과', 'sensor_01'),
        ('gas_warning', 'warning', '가스 농도 25ppm — 경고 수준', 'sensor_01'),
    ]
    for atype, sev, msg, src in active_alarms:
        cur.execute("""
            INSERT INTO alarm_log
            (timestamp, alarm_type, severity, message, source, state)
            VALUES (%s, %s, %s, %s, %s, 'active')
        """, (now - timedelta(minutes=random.randint(5, 60)), atype, sev, msg, src))

    ack_alarms = [
        ('high_temp', 'critical', '온도 과열 감지 (36.2°C)', 'sensor_01', 'admin'),
        ('sorting_fail', 'warning', '분류 오류 3회 연속 발생', 'sorting_verifier', 'admin'),
        ('gas_critical', 'critical', '가스 농도 42ppm 비상 감지', 'sensor_01', 'admin'),
    ]
    for atype, sev, msg, src, ack_by in ack_alarms:
        ts = now - timedelta(hours=random.randint(2, 12))
        ack_ts = ts + timedelta(minutes=random.randint(3, 30))
        cur.execute("""
            INSERT INTO alarm_log
            (timestamp, alarm_type, severity, message, source, state,
             acknowledged_at, acknowledged_by)
            VALUES (%s, %s, %s, %s, %s, 'acknowledged', %s, %s)
        """, (ts, atype, sev, msg, src, ack_ts, ack_by))


def main():
    print("=" * 50)
    print("  MFG Dashboard — 시연용 가짜 데이터 생성")
    print("  주의: 개발/시연 환경에서만 사용하세요!")
    print("=" * 50)
    print()

    conn = get_connection()
    cur = conn.cursor()

    print("\n[1/4] 센서 데이터 생성...")
    fake_sensor_readings(cur, count=15000)

    print("[2/4] 검사 + 분류 데이터 생성...")
    fake_inspections(cur, count=9000)

    print("[3/4] 이벤트 로그 생성...")
    fake_events(cur, count=1500)

    print("[4/4] 알람 데이터 생성...")
    fake_alarms(cur)

    conn.commit()
    cur.close()
    conn.close()

    print()
    print("=" * 50)
    print("  완료! 생성된 데이터 (30일치, 양품률 98%):")
    print(f"    센서 데이터:   15,000건")
    print(f"    검사 결과:      9,000건")
    print(f"    분류 결과:      9,000건")
    print(f"    이벤트 로그:    1,500건")
    print(f"    알람 (active):      2건")
    print(f"    알람 (ack):         3건")
    print("=" * 50)
    print("  http://localhost:5001 에서 확인하세요!")


if __name__ == '__main__':
    main()
