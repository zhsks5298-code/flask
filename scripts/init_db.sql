-- =============================================================
-- MFG Inspection System — manufacturing DB 초기 스키마
-- 대상: MySQL 8.0+
-- 실행: mysql -u root -p < scripts/init_db.sql
-- =============================================================

CREATE DATABASE IF NOT EXISTS manufacturing
    CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE manufacturing;

-- -------------------------------------------------------------
-- 1. 관리자 사용자 (Flask 로그인 대상)
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS admin_users (
    id                  INT             AUTO_INCREMENT PRIMARY KEY,
    username            VARCHAR(50)     NOT NULL UNIQUE,
    password_hash       VARCHAR(255)    NOT NULL,
    full_name           VARCHAR(50),
    email               VARCHAR(100),
    role                ENUM('viewer','operator','maintainer','admin')
                                        NOT NULL DEFAULT 'viewer',
    is_active           BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at          DATETIME        DEFAULT CURRENT_TIMESTAMP,
    last_login_at       DATETIME        NULL,
    password_changed_at DATETIME        NULL,
    failed_login_count  INT             NOT NULL DEFAULT 0,
    locked_until        DATETIME        NULL,
    INDEX idx_role (role),
    INDEX idx_active (is_active)
) ENGINE=InnoDB;

-- -------------------------------------------------------------
-- 2. 로그인 이력 (감사 로그와 별도)
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS login_history (
    id          BIGINT          AUTO_INCREMENT PRIMARY KEY,
    username    VARCHAR(50)     NOT NULL,
    user_id     INT             NULL,
    event_type  ENUM('login_success','login_fail','logout','session_timeout')
                                NOT NULL,
    ip_address  VARCHAR(45),
    user_agent  VARCHAR(255),
    fail_reason VARCHAR(50),
    timestamp   DATETIME        DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_username (username),
    INDEX idx_timestamp (timestamp),
    INDEX idx_event_type (event_type)
) ENGINE=InnoDB;

-- -------------------------------------------------------------
-- 3. 환경 센서 (RPi → MQTT → Flask/Telegraf 양방향)
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sensor_readings (
    id           BIGINT     AUTO_INCREMENT PRIMARY KEY,
    timestamp    DATETIME   DEFAULT CURRENT_TIMESTAMP,
    temperature  FLOAT,
    humidity     FLOAT,
    gas_value    INT,
    gas_status   ENUM('normal','warning','critical') DEFAULT 'normal',
    source       VARCHAR(30),
    quality      ENUM('good','stale','uncertain','bad') DEFAULT 'good',
    seq          BIGINT,
    INDEX idx_timestamp (timestamp),
    INDEX idx_source_ts (source, timestamp)
) ENGINE=InnoDB;

-- -------------------------------------------------------------
-- 4. 검사 결과 (C# WinForms 가 INSERT, Flask 는 SELECT)
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS inspection_results (
    id                    BIGINT       AUTO_INCREMENT PRIMARY KEY,
    timestamp             DATETIME     DEFAULT CURRENT_TIMESTAMP,
    correlation_id        VARCHAR(36),
    product_type          ENUM('transistor','capacitor','regulator','unknown'),
    product_id            VARCHAR(50),
    result                ENUM('pass','defect','hold') NOT NULL,
    yolo_class            VARCHAR(30),
    yolo_confidence       FLOAT,
    final_confidence      FLOAT,
    defect_detail         VARCHAR(100),
    cam2_used             BOOLEAN      DEFAULT FALSE,
    inference_time_ms     INT,
    model_version         VARCHAR(20),
    cam1_image_path       VARCHAR(255),
    environment_temp      FLOAT,
    environment_humidity  FLOAT,
    INDEX idx_timestamp (timestamp),
    INDEX idx_result (result),
    INDEX idx_product_type (product_type),
    INDEX idx_product_id (product_id),
    INDEX idx_correlation_id (correlation_id)
) ENGINE=InnoDB;

-- -------------------------------------------------------------
-- 5. 분류기 검증 (검사 후 실제로 어떤 빈으로 갔는지)
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sorting_results (
    id                  BIGINT       AUTO_INCREMENT PRIMARY KEY,
    inspection_id       BIGINT,
    correlation_id      VARCHAR(36),
    timestamp           DATETIME     DEFAULT CURRENT_TIMESTAMP,
    expected_route      ENUM('pass','defect','hold') NOT NULL,
    actual_sensor       ENUM('S4','S5','S6','none','wrong') DEFAULT 'none',
    expected_sensor     ENUM('S4','S5','S6','none'),
    verification_result ENUM('success','wrong_bin','timeout','skipped')
                                     DEFAULT 'timeout',
    timing_ms           INT,
    INDEX idx_timestamp (timestamp),
    INDEX idx_verification (verification_result),
    INDEX idx_correlation_id (correlation_id),
    CONSTRAINT fk_sort_inspection
        FOREIGN KEY (inspection_id) REFERENCES inspection_results(id)
        ON DELETE SET NULL
) ENGINE=InnoDB;

-- -------------------------------------------------------------
-- 6. 시스템 이벤트 로그 (hash chain 으로 감사 무결성 보장)
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS event_log (
    id              BIGINT       AUTO_INCREMENT PRIMARY KEY,
    timestamp       DATETIME     DEFAULT CURRENT_TIMESTAMP,
    event_type      VARCHAR(50)  NOT NULL,
    severity        ENUM('info','warning','critical','emergency')
                                 NOT NULL DEFAULT 'info',
    source          VARCHAR(50)  NOT NULL DEFAULT 'system',
    message         TEXT,
    actor           VARCHAR(50)  DEFAULT 'system',
    details         JSON,
    reason          TEXT,
    correlation_id  VARCHAR(36),
    prev_hash       VARCHAR(64),
    record_hash     VARCHAR(64),
    INDEX idx_timestamp (timestamp),
    INDEX idx_severity (severity),
    INDEX idx_event_type (event_type),
    INDEX idx_correlation (correlation_id)
) ENGINE=InnoDB;

-- -------------------------------------------------------------
-- 7. 알람 (현재 발생 중인 비정상 상황)
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS alarm_log (
    id               BIGINT       AUTO_INCREMENT PRIMARY KEY,
    timestamp        DATETIME     DEFAULT CURRENT_TIMESTAMP,
    alarm_type       VARCHAR(50)  NOT NULL,
    severity         ENUM('warning','critical','emergency') NOT NULL,
    message          TEXT,
    source           VARCHAR(50),
    state            ENUM('active','acknowledged','cleared') DEFAULT 'active',
    acknowledged_at  DATETIME,
    acknowledged_by  VARCHAR(50),
    cleared_at       DATETIME,
    INDEX idx_state (state),
    INDEX idx_timestamp (timestamp),
    INDEX idx_severity (severity)
) ENGINE=InnoDB;

-- -------------------------------------------------------------
-- 8. 학습 데이터 수집 (D — YOLO 재학습 파이프라인)
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS training_samples (
    id            BIGINT       AUTO_INCREMENT PRIMARY KEY,
    timestamp     DATETIME     DEFAULT CURRENT_TIMESTAMP,
    image_path    VARCHAR(255) NOT NULL,
    label_status  ENUM('collected','uploaded','labeled','in_dataset','rejected')
                               DEFAULT 'collected',
    INDEX idx_status (label_status)
) ENGINE=InnoDB;

-- -------------------------------------------------------------
-- 9. 시스템 설정 (튜닝 파라미터 — admin 만 수정)
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS system_config (
    config_key   VARCHAR(100) PRIMARY KEY,
    config_value VARCHAR(255) NOT NULL,
    data_type    ENUM('int','float','bool','string') DEFAULT 'string',
    unit         VARCHAR(20),
    category     VARCHAR(30),
    description  TEXT,
    min_value    FLOAT,
    max_value    FLOAT,
    is_editable  BOOLEAN     DEFAULT TRUE,
    updated_at   DATETIME    DEFAULT CURRENT_TIMESTAMP
                             ON UPDATE CURRENT_TIMESTAMP,
    updated_by   VARCHAR(50) DEFAULT 'system',
    INDEX idx_category (category)
) ENGINE=InnoDB;

-- -------------------------------------------------------------
-- 10. 제품 마스터 (product_type 별 검사 기준)
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS product_master (
    id                    INT          AUTO_INCREMENT PRIMARY KEY,
    product_type          ENUM('transistor','capacitor','regulator','unknown') UNIQUE,
    display_name          VARCHAR(50)  NOT NULL,
    expected_pin_count    INT,
    pin_count_tolerance   INT          DEFAULT 0,
    min_roi_area          INT,
    max_roi_area          INT,
    confidence_threshold  FLOAT        DEFAULT 0.85,
    is_active             BOOLEAN      DEFAULT TRUE,
    description           TEXT,
    sample_image_path     VARCHAR(255)
) ENGINE=InnoDB;

-- =============================================================
-- 사용자 권한 분리 (인터페이스 동결: v8 분담 문서 §0.3)
--   root          - DDL (스키마 변경 / 운영 외 사용 금지)
--   mfg_control   - C# WinForms 측. 검사/분류/이벤트 INSERT.
--   mfg_flask     - Flask 측. 전체 SELECT + admin_users / login_history /
--                   alarm_log / event_log / training_samples 만 INSERT/UPDATE.
--   mfg_telegraf  - Telegraf 측. (직접 DB 쓰기 없음. MQTT 만 필요하므로
--                   여기서는 placeholder 만. MQTT ACL 측에서 격리.)
-- =============================================================

-- ⚠️ 비밀번호는 .env 와 일치시킬 것. 운영에서는 강한 비밀번호로 교체.
CREATE USER IF NOT EXISTS 'mfg_control'@'%' IDENTIFIED BY 'control_pass_change_me';
CREATE USER IF NOT EXISTS 'mfg_flask'@'%'   IDENTIFIED BY 'flask_pass_change_me';

-- mfg_control: C# 측. 검사/분류/이벤트/알람 / 센서까지 전부 쓰기.
GRANT SELECT, INSERT, UPDATE ON manufacturing.inspection_results TO 'mfg_control'@'%';
GRANT SELECT, INSERT, UPDATE ON manufacturing.sorting_results    TO 'mfg_control'@'%';
GRANT SELECT, INSERT         ON manufacturing.event_log          TO 'mfg_control'@'%';
GRANT SELECT, INSERT, UPDATE ON manufacturing.alarm_log          TO 'mfg_control'@'%';
GRANT SELECT, INSERT         ON manufacturing.sensor_readings    TO 'mfg_control'@'%';
GRANT SELECT, INSERT, UPDATE ON manufacturing.training_samples   TO 'mfg_control'@'%';
GRANT SELECT                 ON manufacturing.system_config      TO 'mfg_control'@'%';
GRANT SELECT                 ON manufacturing.product_master     TO 'mfg_control'@'%';

-- mfg_flask: 모든 테이블 SELECT, 자기가 관리해야 하는 메타 테이블만 쓰기.
GRANT SELECT                          ON manufacturing.*               TO 'mfg_flask'@'%';
GRANT SELECT, INSERT, UPDATE          ON manufacturing.admin_users     TO 'mfg_flask'@'%';
GRANT SELECT, INSERT                  ON manufacturing.login_history   TO 'mfg_flask'@'%';
GRANT SELECT, INSERT                  ON manufacturing.event_log       TO 'mfg_flask'@'%';
GRANT SELECT, INSERT, UPDATE          ON manufacturing.alarm_log       TO 'mfg_flask'@'%';
GRANT SELECT, INSERT, UPDATE          ON manufacturing.system_config   TO 'mfg_flask'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE  ON manufacturing.training_samples TO 'mfg_flask'@'%';

FLUSH PRIVILEGES;

-- =============================================================
-- 마무리
-- 1. python scripts/seed_data.py     — 마스터 + 테스트 데이터 시드
-- 2. python scripts/create_admin.py  — 별도 admin 추가 (선택)
-- =============================================================
