-- AI Revenue Recovery Agent — MySQL Schema
-- Run with: mysql -u root -p < schema.sql   (after CREATE DATABASE revenue_recovery)

CREATE DATABASE IF NOT EXISTS revenue_recovery CHARACTER SET utf8mb4;
USE revenue_recovery;

CREATE TABLE IF NOT EXISTS customers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    email VARCHAR(160) NOT NULL,
    phone VARCHAR(20),
    past_successful_payments INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS transactions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    payment_method VARCHAR(30),
    status ENUM('success','failed','recovered') NOT NULL DEFAULT 'failed',
    failure_reason VARCHAR(60),
    attempt_number INT DEFAULT 1,
    razorpay_reference VARCHAR(80),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id),
    INDEX idx_txn_customer (customer_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS checkout_sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    cart_value DECIMAL(10,2) NOT NULL,
    status ENUM('in_progress','abandoned','recovered') NOT NULL DEFAULT 'abandoned',
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    abandoned_at TIMESTAMP NULL,
    FOREIGN KEY (customer_id) REFERENCES customers(id),
    INDEX idx_checkout_customer (customer_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS subscriptions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    plan_name VARCHAR(60),
    amount DECIMAL(10,2) NOT NULL,
    billing_cycle VARCHAR(20) DEFAULT 'monthly',
    renewal_date DATE,
    status ENUM('active','failed','recovered','cancelled') NOT NULL DEFAULT 'failed',
    failure_reason VARCHAR(60),
    retry_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id),
    INDEX idx_sub_customer (customer_id)
) ENGINE=InnoDB;

-- Unified source of truth for every at-risk revenue event & dashboard metrics
CREATE TABLE IF NOT EXISTS recovery_cases (
    id INT AUTO_INCREMENT PRIMARY KEY,
    scenario_type ENUM('failed_payment','checkout_dropoff','failed_subscription') NOT NULL,
    source_id INT NOT NULL,           -- FK into transactions / checkout_sessions / subscriptions
    customer_id INT NOT NULL,
    amount_at_risk DECIMAL(10,2) NOT NULL,
    status ENUM('DETECTED','ANALYZING','ACTION_TAKEN','PENDING_RETRY',
                'RECOVERED','FAILED','ESCALATED','STOPPED') NOT NULL DEFAULT 'DETECTED',
    retry_count INT DEFAULT 0,
    notification_count INT DEFAULT 0,
    max_retries INT DEFAULT 2,
    recovered_amount DECIMAL(10,2) DEFAULT 0,
    last_action_at TIMESTAMP NULL,
    next_retry_after TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id),
    INDEX idx_cases_status (status),
    INDEX idx_cases_type (scenario_type)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS recovery_actions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    recovery_case_id INT NOT NULL,
    ai_recommended_action VARCHAR(30),
    ai_confidence DECIMAL(4,3),
    ai_reasoning TEXT,
    ai_source VARCHAR(20),              -- 'llm' or 'fallback_heuristic'
    final_action VARCHAR(30) NOT NULL,  -- what the guardrail engine actually approved
    guardrail_overridden BOOLEAN DEFAULT FALSE,
    guardrail_note TEXT,
    result ENUM('pending','success','failed') DEFAULT 'pending',
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (recovery_case_id) REFERENCES recovery_cases(id),
    INDEX idx_actions_case (recovery_case_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS audit_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    recovery_case_id INT,
    event VARCHAR(80) NOT NULL,
    actor ENUM('system','ai','merchant') NOT NULL DEFAULT 'system',
    detail TEXT,
    amount DECIMAL(10,2),
    status_at_event VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (recovery_case_id) REFERENCES recovery_cases(id),
    INDEX idx_audit_case_time (recovery_case_id, created_at)
) ENGINE=InnoDB;
