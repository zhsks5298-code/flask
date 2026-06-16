from datetime import datetime, time, timedelta, timezone
import os
import random
from flask import Blueprint, render_template, jsonify, session
from flask_login import login_required
from models import SensorReading

sensors_bp = Blueprint('sensors', __name__)

KST = timezone(timedelta(hours=9))

INFLUX_URL    = os.getenv('INFLUX_URL', 'http://localhost:8086')
INFLUX_TOKEN  = os.getenv('INFLUX_TOKEN')
INFLUX_ORG    = os.getenv('INFLUX_ORG', 'mfg')
INFLUX_BUCKET = os.getenv('INFLUX_BUCKET', 'line1-telemetry')

def query_influx_sensors(minutes: int = 30):
    if not INFLUX_TOKEN:
        return None
    try:
        from influxdb_client import InfluxDBClient
        query = f'''
        from(bucket: "{INFLUX_BUCKET}")
          |> range(start: -{minutes}m)
          |> filter(fn: (r) => r._measurement == "mqtt_consumer")
          |> filter(fn: (r) => r._field == "value")
          |> filter(fn: (r) => r.topic =~ /temperature|humidity|gas/)
          |> aggregateWindow(every: 1m, fn: mean, createEmpty: false)
          |> pivot(rowKey:["_time"], columnKey: ["topic"], valueColumn: "_value")
          |> sort(columns: ["_time"])
        '''
        with InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG) as client:
            tables = client.query_api().query(query)
            results = []
            for table in tables:
                for record in table.records:
                    row = {'time': record.get_time().astimezone(KST).strftime('%H:%M')}
                    # topic 컬럼에서 temperature/humidity/gas 값 추출
                    for key, val in record.values.items():
                        if 'temperature' in key:
                            row['temperature'] = val
                        elif 'humidity' in key:
                            row['humidity'] = val
                        elif 'gas' in key:
                            row['gas'] = val
                    results.append(row)
            return results if results else None
    except Exception as e:
        print(f"InfluxDB 쿼리 오류: {e}")
        return None

@sensors_bp.route('/')
@login_required
def index():
    today = datetime.now().date()
    session.pop('mock_data', None)
    return render_template('sensors/index.html', target_date=today.strftime('%Y-%m-%d'))

@sensors_bp.route('/api/data')
@login_required
def api_data():
    # 1. InfluxDB 시도
    influx_data = query_influx_sensors(30)
    if influx_data:
        temp_data = [r for r in influx_data if r.get('temperature') is not None]
        humi_data = [r for r in influx_data if r.get('humidity') is not None]
        gas_data  = [r for r in influx_data if r.get('gas') is not None]

        base = temp_data or humi_data or gas_data
        if not base:
            pass 
        else:
            recent = base[-10:]
            return jsonify({
                'labels':      [r['time'] for r in recent],
                'temperature': [r.get('temperature') for r in temp_data[-10:]],
                'humidity':    [r.get('humidity') for r in humi_data[-10:]],
                'gas':         [r.get('gas') for r in gas_data[-10:]],
                'latest': {
                    'temp':     temp_data[-1]['temperature'] if temp_data else 0.0,
                    'humidity': humi_data[-1]['humidity']    if humi_data else 0.0,
                    'gas':      gas_data[-1]['gas']          if gas_data  else 0.0,
                }
            })

    # 2. MySQL fallback
    today = datetime.now().date()
    start_dt = datetime.combine(today, time(0, 0, 0))
    end_dt   = datetime.combine(today, time(23, 59, 59))
    readings = SensorReading.query.filter(
        SensorReading.timestamp.between(start_dt, end_dt)
    ).order_by(SensorReading.timestamp.desc()).limit(50).all()

    if not readings:
        # 3. mock fallback
        now = datetime.now()
        if 'mock_data' not in session:
            mock_data = {
                'labels': [(now - timedelta(minutes=i*2)).strftime('%H:%M') for i in range(9, -1, -1)],
                'temp':   [round(random.uniform(22.0, 26.0), 1) for _ in range(10)],
                'humi':   [round(random.uniform(45.0, 55.0), 1) for _ in range(10)],
                'gas':    [round(random.uniform(5.0, 15.0),  1) for _ in range(10)]
            }
        else:
            mock_data = session['mock_data']
            mock_data['temp'][-1]   = round(random.uniform(22.0, 26.0), 1)
            mock_data['humi'][-1]   = round(random.uniform(45.0, 55.0), 1)
            mock_data['gas'][-1]    = round(random.uniform(5.0, 15.0),  1)
            mock_data['labels'][-1] = now.strftime('%H:%M')
        session['mock_data'] = mock_data
        return jsonify({
            'labels':      mock_data['labels'],
            'temperature': mock_data['temp'],
            'humidity':    mock_data['humi'],
            'gas':         mock_data['gas'],
            'latest': {'temp': mock_data['temp'][-1], 'humidity': mock_data['humi'][-1], 'gas': mock_data['gas'][-1]}
        })

    # 4. MySQL 데이터 처리
    temp_valid = [r for r in readings if r.temperature is not None]
    humi_valid = [r for r in readings if r.humidity    is not None]
    gas_valid  = [r for r in readings if r.gas_value   is not None]
    labels     = [r.timestamp.strftime('%H:%M') for r in readings[:10]][::-1]
    return jsonify({
        'labels':      labels,
        'temperature': [r.temperature for r in temp_valid[:10]][::-1],
        'humidity':    [r.humidity    for r in humi_valid[:10]][::-1],
        'gas':         [r.gas_value   for r in gas_valid[:10]][::-1],
        'latest': {
            'temp':     temp_valid[0].temperature if temp_valid else 0.0,
            'humidity': humi_valid[0].humidity    if humi_valid else 0.0,
            'gas':      gas_valid[0].gas_value    if gas_valid  else 0.0,
        }
    })