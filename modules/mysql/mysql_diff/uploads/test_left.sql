-- 示例数据库表结构
CREATE TABLE `users` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `username` varchar(50) NOT NULL,
  `email` varchar(100) NOT NULL,
  `age` int(11) DEFAULT NULL,
  `status` enum('active','inactive') DEFAULT 'active',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`),
  KEY `idx_email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 示例数据
INSERT INTO `users` VALUES (1, 'alice', 'alice@example.com', 25, 'active', '2024-01-01 10:00:00');
INSERT INTO `users` VALUES (2, 'bob', 'bob@example.com', 30, 'active', '2024-01-02 11:00:00');
INSERT INTO `users` VALUES (3, 'charlie', 'charlie@example.com', 35, 'inactive', '2024-01-03 12:00:00');
INSERT INTO `users` VALUES (4, 'david', 'david@example.com', 28, 'active', '2024-01-04 13:00:00');
INSERT INTO `users` VALUES (5, 'eve', 'eve@example.com', 22, 'active', '2024-01-05 14:00:00');
