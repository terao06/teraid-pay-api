CREATE TABLE IF NOT EXISTS visit_sessions (
    visit_session_id BIGINT NOT NULL AUTO_INCREMENT,
    device_id BIGINT NOT NULL,
    start_request_id VARCHAR(64) COLLATE utf8mb4_0900_bin NOT NULL,
    status ENUM('active', 'checkout_processing', 'closed') NOT NULL DEFAULT 'active',
    started_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ended_at DATETIME DEFAULT NULL,
    PRIMARY KEY (visit_session_id),
    CONSTRAINT uq_visit_sessions_device_request UNIQUE (device_id, start_request_id),
    INDEX ix_visit_sessions_device_status (device_id, status),
    FOREIGN KEY (device_id) REFERENCES devices (device_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
