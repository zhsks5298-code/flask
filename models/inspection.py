from datetime import datetime
from extensions import db

class InspectionResult(db.Model):
    __tablename__ = 'inspection_results'
    id = db.Column(db.BigInteger, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    correlation_id = db.Column(db.String(36), index=True)
    product_type = db.Column(db.Enum('transistor','capacitor','regulator','unknown'))
    product_id = db.Column(db.String(50))
    result = db.Column(db.String(16), nullable=False)
    yolo_class = db.Column(db.String(30))
    yolo_confidence = db.Column(db.Float)
    final_confidence = db.Column(db.Float)
    defect_detail = db.Column(db.String(100))
    cam2_used = db.Column(db.Boolean, default=False)
    inference_time_ms = db.Column(db.Integer)
    model_version = db.Column(db.String(20))
    cam1_image_path = db.Column(db.String(255))
    environment_temp = db.Column(db.Float)
    environment_humidity = db.Column(db.Float)

class SortingResult(db.Model):
    __tablename__ = 'sorting_results'
    id = db.Column(db.BigInteger, primary_key=True)
    inspection_id = db.Column(db.BigInteger, db.ForeignKey('inspection_results.id'))
    correlation_id = db.Column(db.String(36), index=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    expected_route = db.Column(db.String(16), nullable=False)
    actual_sensor = db.Column(db.String(8), default='none')
    expected_sensor = db.Column(db.String(8))
    verification_result = db.Column(db.String(16), default='timeout')
    timing_ms = db.Column(db.Integer)