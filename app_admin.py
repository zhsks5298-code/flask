from flask import Flask
from sqlalchemy import text                       # ← 누락되어 있던 import
from config import DevelopmentConfig
from extensions import db, login_manager, socketio
from models import User, AlarmLog
import json, os, threading
import paho.mqtt.client as mqtt
from datetime import datetime, timedelta


def create_app(config_class=DevelopmentConfig):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)
    socketio.init_app(app, async_mode='threading', cors_allowed_origins='*')

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    @app.context_processor
    def inject_globals():
        count = 0
        db_ok = False
        rpi_ok = False
        mqtt_ok = mqtt_state.get('connected', False)   # ← 실시간 연결 상태 반영

        try:
            db.session.execute(text('SELECT 1'))
            db_ok = True
            count = AlarmLog.query.filter_by(state='active').count()

            from models.sensor import SensorReading
            latest = SensorReading.query.order_by(SensorReading.timestamp.desc()).first()
            if latest:
                rpi_ok = (datetime.utcnow() - latest.timestamp).total_seconds() < 60
        except Exception:
            pass

        return {
            'active_alarm_count': count,
            'db_ok': db_ok,
            'rpi_ok': rpi_ok,
            'mqtt_ok': mqtt_ok,
            'base_template': 'base_admin.html', 
        }

    from routes.auth import auth_bp
    from routes.dashboard import dashboard_bp
    from routes.events import events_bp
    from routes.admin import admin_bp
    from routes.health import health_bp
    from routes.history import history_bp
    from routes.stats import stats_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(events_bp, url_prefix='/events')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(health_bp, url_prefix='/health')
    app.register_blueprint(history_bp, url_prefix='/history')
    app.register_blueprint(stats_bp, url_prefix='/stats')

    with app.app_context():
        start_mqtt_subscriber(app)

    return app


# ── MQTT ──
BROKER_HOST = os.getenv('MQTT_BROKER_HOST', '127.0.0.1')
BROKER_PORT = int(os.getenv('MQTT_BROKER_PORT', 1883))
MQTT_USER   = os.getenv('MQTT_FLASK_USER', 'mfg_flask')
MQTT_PASS   = os.getenv('MQTT_FLASK_PASS', '2222')

# 모듈 전역 — context_processor 에서 참조
mqtt_state = {'connected': False}


def start_mqtt_subscriber(app):
    def on_connect(client, userdata, flags, reason_code, properties=None):
        if reason_code == 0:
            mqtt_state['connected'] = True
            client.subscribe('mfg/line1/env/#', qos=0)
            client.subscribe('mfg/line1/inspection/result', qos=1)
            client.subscribe('mfg/line1/sorting/result', qos=1)
            client.subscribe('mfg/line1/stats/production', qos=0)
            client.subscribe('mfg/line1/alarm/#', qos=1)
            client.subscribe('mfg/line1/status/#', qos=1)
            print(f"[MQTT] connected to {BROKER_HOST}:{BROKER_PORT}")
        else:
            mqtt_state['connected'] = False
            print(f"[MQTT] connect failed rc={reason_code}")

    def on_disconnect(client, userdata, *args):
        mqtt_state['connected'] = False
        print("[MQTT] disconnected")

    def on_message(client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            topic   = msg.topic

            socketio.emit('sensor_update', {
                'topic': topic, 'payload': payload
            }, namespace='/realtime')

            # 토픽별 분리 채널 (브라우저가 구독 분리 가능)
            if topic.startswith('mfg/line1/env/'):
                socketio.emit('env_update', payload, namespace='/realtime')
            elif topic.startswith('mfg/line1/alarm/'):
                socketio.emit('alarm_update', payload, namespace='/realtime')

            if topic == 'mfg/line1/inspection/result':
                with app.app_context():
                    from models.inspection import InspectionResult
                    verdict = payload.get('verdict', '').lower()
                    inspected_at = payload.get('inspected_at')
                    ts = (
                        datetime.fromisoformat(inspected_at.replace('Z', '+00:00'))
                        if inspected_at else datetime.utcnow()
                    )
                    result = InspectionResult(
                        result=verdict,
                        timestamp=ts,
                    )
                    db.session.add(result)
                    db.session.commit()
                socketio.emit('inspection_update', payload, namespace='/realtime')

            elif topic == 'mfg/line1/stats/production':
                socketio.emit('stats_update', payload, namespace='/realtime')

        except Exception as e:
            print(f"MQTT 처리 오류: {e}")

    def run():
        with app.app_context():
            client = mqtt.Client(
                callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
                client_id='flask-admin',
                clean_session=False
            )
            client.username_pw_set(MQTT_USER, MQTT_PASS)
            client.will_set(
                'mfg/line1/status/flask/online',
                json.dumps({'online': False}), qos=1, retain=True
            )
            client.on_connect = on_connect
            client.on_disconnect = on_disconnect
            client.on_message = on_message

            # broker 가 죽어 있어도 Flask 자체는 떠야 함 → 재연결 루프
            while True:
                try:
                    client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
                    client.publish(
                        'mfg/line1/status/flask/online',
                        json.dumps({'online': True}), qos=1, retain=True
                    )
                    client.loop_forever()
                except Exception as e:
                    mqtt_state['connected'] = False
                    print(f"[MQTT] connect error: {e} — retry in 5s")
                    import time as _t; _t.sleep(5)

    t = threading.Thread(target=run, daemon=True)
    t.start()


if __name__ == '__main__':
    app = create_app()
    socketio.run(app, host='0.0.0.0', port=5003, debug=False, use_reloader=False, allow_unsafe_werkzeug=True)
