from extensions import db

class SystemConfig(db.Model):
    __tablename__ = 'system_config'
    config_key = db.Column(db.String(100), primary_key=True)
    config_value = db.Column(db.String(255), nullable=False)
    data_type = db.Column(
        db.Enum('int', 'float', 'bool', 'string'),
        default='string'
    )
    unit = db.Column(db.String(20))
    category = db.Column(db.String(30))
    description = db.Column(db.Text)
    min_value = db.Column(db.Float)
    max_value = db.Column(db.Float)
    is_editable = db.Column(db.Boolean, default=True)
    updated_at = db.Column(
        db.DateTime,
        default=db.func.current_timestamp(),
        onupdate=db.func.current_timestamp()
    )
    updated_by = db.Column(db.String(50), default='system')

class ProductMaster(db.Model):
    __tablename__ = 'product_master'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    product_type = db.Column(
        db.Enum('transistor', 'capacitor', 'regulator', 'unknown'),
        unique=True
    )
    display_name = db.Column(db.String(50), nullable=False)
    expected_pin_count = db.Column(db.Integer)
    pin_count_tolerance = db.Column(db.Integer, default=0)
    min_roi_area = db.Column(db.Integer)
    max_roi_area = db.Column(db.Integer)
    confidence_threshold = db.Column(db.Float, default=0.85)
    is_active = db.Column(db.Boolean, default=True)
    description = db.Column(db.Text)
    sample_image_path = db.Column(db.String(255))