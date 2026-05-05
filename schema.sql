-- ============================================================
--  قاعدة بيانة   المنقذ الذكي
--  Smart Survival Watch Database Schema
-- ============================================================

CREATE DATABASE IF NOT EXISTS smart_watch_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE smart_watch_db;

-- ============================================================
-- جدول المستخدمين
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL COMMENT 'الاسم الكامل',
    email VARCHAR(150) NOT NULL UNIQUE COMMENT 'البريد الإلكتروني',
    phone VARCHAR(20) COMMENT 'رقم الهاتف',
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('admin', 'user', 'rescue_team') DEFAULT 'user' COMMENT 'دور المستخدم',
    avatar VARCHAR(255) DEFAULT NULL,
    is_active TINYINT(1) DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB COMMENT='جدول المستخدمين';

-- ============================================================
-- جدول الأجهزة (الساعات الذكية)
-- ============================================================
CREATE TABLE IF NOT EXISTS devices (
    id INT AUTO_INCREMENT PRIMARY KEY,
    device_id VARCHAR(50) NOT NULL UNIQUE COMMENT 'معرف الجهاز الفريد',
    user_id INT NOT NULL,
    device_name VARCHAR(100) NOT NULL COMMENT 'اسم الجهاز',
    serial_number VARCHAR(100) UNIQUE COMMENT 'الرقم التسلسلي',
    firmware_version VARCHAR(20) DEFAULT '1.0.0',
    battery_level INT DEFAULT 100 COMMENT 'مستوى البطارية %',
    solar_charging TINYINT(1) DEFAULT 0 COMMENT 'حالة الشحن الشمسي',
    satellite_connected TINYINT(1) DEFAULT 0 COMMENT 'اتصال الأقمار الصناعية',
    is_active TINYINT(1) DEFAULT 1,
    last_seen TIMESTAMP NULL,
    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB COMMENT='جدول الأجهزة الذكية';

-- ============================================================
-- جدول بيانات الموقع (GPS)
-- ============================================================
CREATE TABLE IF NOT EXISTS location_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    device_id INT NOT NULL,
    latitude DECIMAL(10, 8) NOT NULL COMMENT 'خط العرض',
    longitude DECIMAL(11, 8) NOT NULL COMMENT 'خط الطول',
    altitude DECIMAL(8, 2) DEFAULT 0 COMMENT 'الارتفاع بالأمتار',
    accuracy DECIMAL(8, 2) DEFAULT 0 COMMENT 'دقة الموقع بالأمتار',
    satellite_count INT DEFAULT 0 COMMENT 'عدد الأقمار الصناعية المتصلة',
    speed DECIMAL(6, 2) DEFAULT 0 COMMENT 'السرعة كم/ساعة',
    heading DECIMAL(5, 2) DEFAULT 0 COMMENT 'الاتجاه بالدرجات',
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
) ENGINE=InnoDB COMMENT='سجلات الموقع الجغرافي';

-- ============================================================
-- جدول رصد الأجهزة المحيطة (Bluetooth/WiFi Scan)
-- ============================================================
CREATE TABLE IF NOT EXISTS nearby_devices (
    id INT AUTO_INCREMENT PRIMARY KEY,
    device_id INT NOT NULL COMMENT 'الساعة الذكية',
    detected_signal_type ENUM('bluetooth', 'wifi', 'cellular') DEFAULT 'bluetooth',
    signal_strength INT DEFAULT 0 COMMENT 'قوة الإشارة dBm',
    estimated_distance DECIMAL(8, 2) COMMENT 'المسافة المقدرة بالأمتار',
    device_mac VARCHAR(20) COMMENT 'عنوان MAC للجهاز المكتشف',
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
) ENGINE=InnoDB COMMENT='الأجهزة المكتشفة في المحيط';

-- ============================================================
-- جدول نداءات الاستغاثة (SOS Alerts)
-- ============================================================
CREATE TABLE IF NOT EXISTS sos_alerts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    device_id INT NOT NULL,
    user_id INT NOT NULL,
    alert_type ENUM('manual', 'auto', 'no_nearby_devices', 'low_battery') DEFAULT 'manual',
    latitude DECIMAL(10, 8) COMMENT 'موقع الاستغاثة - خط العرض',
    longitude DECIMAL(11, 8) COMMENT 'موقع الاستغاثة - خط الطول',
    nearby_devices_count INT DEFAULT 0 COMMENT 'عدد الأجهزة المكتشفة',
    nearest_device_distance DECIMAL(8, 2) COMMENT 'أقرب جهاز بالأمتار',
    message TEXT COMMENT 'رسالة الاستغاثة',
    battery_at_alert INT COMMENT 'مستوى البطارية وقت الاستغاثة',
    status ENUM('active', 'responding', 'resolved', 'cancelled') DEFAULT 'active',
    rescue_team_id INT NULL COMMENT 'فريق الإنقاذ المعين',
    response_notes TEXT COMMENT 'ملاحظات الاستجابة',
    resolved_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB COMMENT='نداءات الاستغاثة';

-- ============================================================
-- جدول فرق الإنقاذ
-- ============================================================
CREATE TABLE IF NOT EXISTS rescue_teams (
    id INT AUTO_INCREMENT PRIMARY KEY,
    team_name VARCHAR(100) NOT NULL COMMENT 'اسم الفريق',
    region VARCHAR(100) COMMENT 'منطقة العمل',
    contact_phone VARCHAR(20) COMMENT 'هاتف التواصل',
    contact_email VARCHAR(150) COMMENT 'بريد التواصل',
    team_leader VARCHAR(100) COMMENT 'قائد الفريق',
    members_count INT DEFAULT 0 COMMENT 'عدد الأعضاء',
    is_available TINYINT(1) DEFAULT 1 COMMENT 'متاح للمهام',
    latitude DECIMAL(10, 8) COMMENT 'موقع الفريق',
    longitude DECIMAL(11, 8) COMMENT 'موقع الفريق',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB COMMENT='فرق الإنقاذ';

-- ============================================================
-- جدول استجابات فرق الإنقاذ
-- ============================================================
CREATE TABLE IF NOT EXISTS rescue_responses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sos_id INT NOT NULL,
    team_id INT NOT NULL,
    responded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    estimated_arrival INT COMMENT 'الوقت المقدر للوصول بالدقائق',
    actual_arrival TIMESTAMP NULL,
    status ENUM('dispatched', 'en_route', 'arrived', 'completed') DEFAULT 'dispatched',
    notes TEXT,
    FOREIGN KEY (sos_id) REFERENCES sos_alerts(id) ON DELETE CASCADE,
    FOREIGN KEY (team_id) REFERENCES rescue_teams(id) ON DELETE CASCADE
) ENGINE=InnoDB COMMENT='استجابات فرق الإنقاذ';

-- ============================================================
-- جدول إشعارات النظام
-- ============================================================
CREATE TABLE IF NOT EXISTS notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    type ENUM('sos', 'device', 'system', 'rescue') DEFAULT 'system',
    is_read TINYINT(1) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB COMMENT='الإشعارات';

-- ============================================================
-- بيانات تجريبية
-- ============================================================

-- فرق الإنقاذ
INSERT INTO rescue_teams (team_name, region, contact_phone, team_leader, members_count, latitude, longitude) VALUES
('فريق الإنقاذ الجبلي - الرياض', 'الرياض', '0112345678', 'العقيد أحمد الشمري', 12, 24.7136, 46.6753),
('وحدة الإنقاذ البرية - جدة', 'جدة', '0126789012', 'المقدم سالم العمري', 8, 21.4858, 39.1925),
('فريق الطوارئ الصحراوية - الدمام', 'الدمام', '0138901234', 'الرائد فهد القحطاني', 10, 26.4207, 50.0888),
('وحدة الإنقاذ الجوي - أبها', 'أبها', '0177890123', 'المقدم خالد الزهراني', 6, 18.2164, 42.5053);

-- مستخدم تجريبي (كلمة المرور: Admin@123)
INSERT INTO users (full_name, email, phone, password_hash, role) VALUES
('مشرف النظام', 'admin@smartwatch.sa', '0500000000', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMUdfufEX2G2nZ0iGWBiQPxjea', 'admin'),
('محمد العتيبي', 'mohammed@example.com', '0501234567', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMUdfufEX2G2nZ0iGWBiQPxjea', 'user'),
('سارة الحربي', 'sara@example.com', '0507654321', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMUdfufEX2G2nZ0iGWBiQPxjea', 'user');
