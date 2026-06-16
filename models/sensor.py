from datetime import datetime, timezone, timedelta
from extensions import db

KST = timezone(timedelta(hours=9))

def now_kst():
    return datetime.now(KST).replace(tzinfo=None)

class SensorReading(db.Model):
    __tablename__ = 'sensor_readings'
    
    id = db.Column(db.BigInteger, primary_key=True)
    timestamp = db.Column(db.DateTime, default=now_kst)
    temperature = db.Column(db.Float)
    humidity = db.Column(db.Float)
    gas_value = db.Column(db.Integer)
    gas_status = db.Column(db.Enum('normal','warning','critical'), default='normal')
    source = db.Column(db.String(30))
    quality = db.Column(db.Enum('good','stale','uncertain','bad'), default='good')
    seq = db.Column(db.BigInteger)