CREATE DATABASE IF NOT EXISTS pii_project;
USE pii_project;

-- 1. Create Users Table
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    role ENUM('user', 'third_party') NOT NULL
);

-- 2. Create Documents Table
CREATE TABLE IF NOT EXISTS documents (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    raw_text LONGTEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 3. Create PII Entities Table
CREATE TABLE IF NOT EXISTS pii_entities (
    id INT AUTO_INCREMENT PRIMARY KEY,
    document_id INT NOT NULL,
    entity_text VARCHAR(255) NOT NULL,
    entity_type VARCHAR(100) NOT NULL,
    sensitivity ENUM('PERSONAL', 'CONFIDENTIAL', 'NON_SENSITIVE') NOT NULL,
    encrypted_value VARCHAR(512),
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);

-- 4. Create Access Requests Table (Optional, for future use)
CREATE TABLE IF NOT EXISTS access_requests (
    id INT AUTO_INCREMENT PRIMARY KEY,
    document_id INT NOT NULL,
    requester_id INT NOT NULL,
    status ENUM('PENDING', 'APPROVED', 'REJECTED') DEFAULT 'PENDING',
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
    FOREIGN KEY (requester_id) REFERENCES users(id) ON DELETE CASCADE
);

-- INSERT 10 Users ('user' role)
INSERT INTO users (username, password, role) VALUES 
('user1', 'pass1', 'user'),
('user2', 'pass2', 'user'),
('user3', 'pass3', 'user'),
('user4', 'pass4', 'user'),
('user5', 'pass5', 'user'),
('user6', 'pass6', 'user'),
('user7', 'pass7', 'user'),
('user8', 'pass8', 'user'),
('user9', 'pass9', 'user'),
('user10', 'pass10', 'user')
ON DUPLICATE KEY UPDATE username=username;

-- INSERT 10 Third Parties ('third_party' role)
INSERT INTO users (username, password, role) VALUES 
('tp1', 'tpass1', 'third_party'),
('tp2', 'tpass2', 'third_party'),
('tp3', 'tpass3', 'third_party'),
('tp4', 'tpass4', 'third_party'),
('tp5', 'tpass5', 'third_party'),
('tp6', 'tpass6', 'third_party'),
('tp7', 'tpass7', 'third_party'),
('tp8', 'tpass8', 'third_party'),
('tp9', 'tpass9', 'third_party'),
('tp10', 'tpass10', 'third_party')
ON DUPLICATE KEY UPDATE username=username;
