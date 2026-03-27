-- 示例数据库表结构（略有不同）
CREATE TABLE `users` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `username` varchar(50) NOT NULL,
  `email` varchar(100) NOT NULL,
  `age` int(11) DEFAULT NULL,
  `phone` varchar(20) DEFAULT NULL,
  `status` enum('active','inactive','pending') DEFAULT 'active',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`),
  KEY `idx_email` (`email`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 示例数据（有差异）
INSERT INTO `users` VALUES (1, 'alice', 'alice@example.com', 26, NULL, 'active', '2024-01-01 10:00:00');
INSERT INTO `users` VALUES (2, 'bob', 'bob@example.com', 30, '1234567890', 'active', '2024-01-02 11:00:00');
INSERT INTO `users` VALUES (3, 'charlie', 'charlie@example.com', 35, NULL, 'inactive', '2024-01-03 12:00:00');
INSERT INTO `users` VALUES (4, 'david', 'david_new@example.com', 28, NULL, 'active', '2024-01-04 13:00:00');
INSERT INTO `users` VALUES (6, 'frank', 'frank@example.com', 40, NULL, 'pending', '2024-01-06 15:00:00');
