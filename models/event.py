from datetime import datetime
from extensions import db
import hashlib

class EventLog(db.Model):
    __tablename__ = 'event_log'
    id = db.Column(db.BigInteger, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    event_type = db.Column(db.String(50), nullable=False)
    severity = db.Column(db.Enum('info','warning','critical','emergency'), 
                         nullable=False, default='info')      # ← default 추가
    source = db.Column(db.String(50), nullable=False, 
                       default='system')                       # ← default 추가
    message = db.Column(db.Text)
    actor = db.Column(db.String(50), default='system')
    details = db.Column(db.JSON)
    reason         = db.Column(db.Text)
    correlation_id = db.Column(db.String(36))
    prev_hash      = db.Column(db.String(64))
    record_hash    = db.Column(db.String(64))

    def compute_hash(self):
        """이 레코드의 hash 계산 (prev_hash 포함)."""
        raw = '|'.join([
            self.prev_hash or '',
            str(self.event_type or ''),
            str(self.severity or ''),
            str(self.source or ''),
            str(self.message or ''),
            str(self.actor or ''),
            str(self.timestamp or ''),
        ])
        return hashlib.sha256(raw.encode()).hexdigest()

    @classmethod
    def write(cls, event_type, severity, source, message,
              actor='system', reason=None, correlation_id=None):
        """hash chain을 유지하면서 레코드 쓰기."""
        last = cls.query.order_by(cls.id.desc()).first()
        prev_hash = last.record_hash if last else None

        log = cls(
            event_type=event_type,
            severity=severity,
            source=source,
            message=message,
            actor=actor,
            reason=reason,
            correlation_id=correlation_id,
            prev_hash=prev_hash,
        )
        log.record_hash = log.compute_hash()
        db.session.add(log)
        db.session.commit()
        return log

class AlarmLog(db.Model):
    __tablename__ = 'alarm_log'   # ← 플레이북 스키마: alarm_log
    id = db.Column(db.BigInteger, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    alarm_type = db.Column(db.String(50), nullable=False)
    severity = db.Column(db.Enum('warning','critical','emergency'), nullable=False)
    message = db.Column(db.Text)
    source = db.Column(db.String(50))
    state = db.Column(db.Enum('active','acknowledged','cleared'), default='active')
    acknowledged_at = db.Column(db.DateTime)
    acknowledged_by = db.Column(db.String(50))
    cleared_at = db.Column(db.DateTime)

class TrainingSample(db.Model):
    __tablename__ = 'training_samples'
    id = db.Column(db.BigInteger, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    image_path = db.Column(db.String(255), nullable=False)
    label_status = db.Column(
        db.Enum('collected','uploaded','labeled','in_dataset','rejected'),
        default='collected'
    )