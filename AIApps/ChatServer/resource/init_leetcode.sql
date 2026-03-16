CREATE TABLE IF NOT EXISTS `study_records` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `user_id` bigint(20) NOT NULL,
  `problem_id` int(11) NOT NULL,
  `problem_title` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `difficulty` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `stage` int(11) NOT NULL DEFAULT '0',
  `last_review_time` bigint(20) NOT NULL DEFAULT '0',
  `next_review_time` bigint(20) NOT NULL DEFAULT '0',
  `status` int(11) NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`),
  KEY `idx_user_next_review` (`user_id`,`next_review_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
