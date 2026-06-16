"""
30일분 과거 센서 샘플 데이터 생성.
sensor_readings 테이블에 15분 간격으로 삽입.
하루 96건 x 30일 = 약 2,880건.

사용법: python scripts/seed_history.py
"""
import os
import sys
import pymysql
import math
import random
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
load_dotenv()

DAYS_BACK = 30      # 30일 과거부터
INTERVAL_MIN = 15   # 15분 간격 (2시간 버킷당 8개 → 평균 의미 있음)


def get_connection():
    return pymysql.connect(
        host='localhost',
        user='root',
        password=input("MySQL root 비밀번호: "),
        database='manufacturing',
        charset='utf8mb4'
    )


def generate_readings():
    """현실적인 센서 값 생성 — 하루 주기 패턴 + 랜덤 노이즈."""
    readings = []
    now_utc = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    start = now_utc - timedelta(days=DAYS_BACK)

    # 30일 × 24시간 × (60/15) = 2880 포인트
    total_points = DAYS_BACK * 24 * (60 // INTERVAL_MIN)

    for i in range(total_points):
        ts = start + timedelta(minutes=i * INTERVAL_MIN)
        hour = ts.hour + ts.minute / 60.0  # 0.0 ~ 23.99

        # ── 온도: 기본 24°C, 낮에 +2~3°C, 새벽에 -1~2°C ──
        #    사인 커브로 자연스러운 일교차 시뮬레이션
        daily_cycle = math.sin((hour - 6) / 24 * 2 * math.pi)  # 14시 피크, 02시 저점
        base_temp = 24.5 + daily_cycle * 2.0
        # 날마다 약간 다른 기온 (날씨 변동)
        day_offset = math.sin(i / (96 * 3.7)) * 1.5  # 3~4일 주기 변동
        temp = round(base_temp + day_offset + random.gauss(0, 0.3), 1)
        temp = max(18.0, min(32.0, temp))  # 범위 제한

        # ── 습도: 온도와 대략 역상관 (더우면 건조, 시원하면 습함) ──
        base_humid = 52.0 - daily_cycle * 3.0
        humid = round(base_humid + day_offset * (-0.5) + random.gauss(0, 1.0), 1)
        humid = max(35.0, min(70.0, humid))

        # ── 가스: 평소 2~8 ppm, 가끔 스파이크 (작업 중 or 환기 불량) ──
        base_gas = 5.0
        # 근무 시간(09~18시)에 살짝 높음
        if 9 <= hour <= 18:
            base_gas += 2.0
        # 0.5% 확률로 스파이크 (30~100 ppm)
        if random.random() < 0.005:
            gas = round(random.uniform(30, 100), 1)
        else:
            gas = round(base_gas + random.gauss(0, 1.5), 1)
        gas = max(0.0, gas)

        # gas_status 결정
        if gas >= 50:
            gas_status = 'critical'
        elif gas >= 30:
            gas_status = 'warning'
        else:
            gas_status = 'normal'

        readings.append((
            ts.strftime('%Y-%m-%d %H:%M:%S'),
            temp, humid, round(gas, 1), gas_status, 'RPi_01', 'good'
        ))

    return readings


def main():
    conn = get_connection()
    cur = conn.cursor()

    print(f"Generating {DAYS_BACK} days of sensor data (15-min interval)...")
    readings = generate_readings()
    print(f"Generated {len(readings)} rows. Inserting...")

    # 배치 삽입 (500건씩)
    batch_size = 500
    for i in range(0, len(readings), batch_size):
        batch = readings[i:i + batch_size]
        cur.executemany("""
            INSERT INTO sensor_readings
                (timestamp, temperature, humidity, gas_value, gas_status, source, quality)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, batch)
        conn.commit()
        print(f"  ... {min(i + batch_size, len(readings))} / {len(readings)}")

    # 결과 확인
    cur.execute("""
        SELECT DATE(timestamp) AS d, COUNT(*) AS cnt
        FROM sensor_readings
        GROUP BY d
        ORDER BY d DESC
        LIMIT 5
    """)
    print("\n최근 5일 데이터 건수:")
    for row in cur.fetchall():
        print(f"  {row[0]}  {row[1]}건")

    cur.close()
    conn.close()
    print(f"\n완료! {len(readings)}건 삽입됨.")


if __name__ == '__main__':
    main()
