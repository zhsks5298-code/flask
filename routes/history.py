from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
from extensions import db
from sqlalchemy import text

history_bp = Blueprint('history', __name__)


@history_bp.route('/')
@login_required
def index():
    return render_template('history/index.html')


@history_bp.route('/api/sensor')
@login_required
def api_sensor():
    date = request.args.get('date', '')

    if date:
        where = "WHERE DATE(timestamp) = :date"
        params = {'date': date}
    else:
        where = "WHERE DATE(timestamp) = CURDATE()"
        params = {}

    sql = text(f"""
        SELECT
            FLOOR(HOUR(timestamp) / 2) * 2  AS bucket_hour,
            ROUND(AVG(temperature), 1)  AS temp_avg,
            ROUND(MIN(temperature), 1)  AS temp_min,
            ROUND(MAX(temperature), 1)  AS temp_max,
            ROUND(AVG(humidity), 1)     AS humid_avg,
            ROUND(MIN(humidity), 1)     AS humid_min,
            ROUND(MAX(humidity), 1)     AS humid_max,
            ROUND(AVG(gas_value), 1)    AS gas_avg,
            ROUND(MIN(gas_value), 1)    AS gas_min,
            ROUND(MAX(gas_value), 1)    AS gas_max
        FROM sensor_readings
        {where}
        GROUP BY bucket_hour
        ORDER BY bucket_hour ASC
    """)

    rows = db.session.execute(sql, params).fetchall()

    labels = [f"{int(r[0]):02d}:00" for r in rows]

    return jsonify({
        'labels':    labels,
        'temp': {
            'avg': [float(r[1]) if r[1] is not None else None for r in rows],
            'min': [float(r[2]) if r[2] is not None else None for r in rows],
            'max': [float(r[3]) if r[3] is not None else None for r in rows],
        },
        'humidity': {
            'avg': [float(r[4]) if r[4] is not None else None for r in rows],
            'min': [float(r[5]) if r[5] is not None else None for r in rows],
            'max': [float(r[6]) if r[6] is not None else None for r in rows],
        },
        'gas': {
            'avg': [float(r[7]) if r[7] is not None else None for r in rows],
            'min': [float(r[8]) if r[8] is not None else None for r in rows],
            'max': [float(r[9]) if r[9] is not None else None for r in rows],
        },
        'count': len(rows),
        'date':  date or 'today',
    })