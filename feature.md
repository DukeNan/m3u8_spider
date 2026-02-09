1. mysql数据表信息，其中status=(0: 未下载，1：下载成功，2：下载失败)
```sql
CREATE TABLE `movie_info` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `number` varchar(255) DEFAULT NULL,
  `status` int(5) DEFAULT '0' COMMENT '0:默认,1:下载完成,2:部分下载',
  `title` text,
  `summary` text,
  `url` text,
  `m3u8_address` text,
  `provider` varchar(255) DEFAULT NULL,
  `homepage` text,
  `director` varchar(255) DEFAULT NULL,
  `actors` json DEFAULT NULL,
  `thumb_url` text,
  `big_thumb_url` text,
  `cover_url` text,
  `big_cover_url` text,
  `preview_video_url` text,
  `preview_video_hls_url` text,
  `preview_images` json DEFAULT NULL,
  `maker` varchar(255) DEFAULT NULL,
  `label` varchar(255) DEFAULT NULL,
  `series` varchar(255) DEFAULT NULL,
  `genres` json DEFAULT NULL,
  `score` float DEFAULT NULL,
  `runtime` int(11) DEFAULT NULL,
  `release_date` date DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `m3u8_update_time` timestamp NULL DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `index_number` (`number`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=2322 DEFAULT CHARSET=utf8mb4;
```
2. 读取mysql表记录（status=0），将m3u8_address是m3u8的地址，以及number作为文件名，进行下载，并校验完成性，更新字段status
  1. 校验完整：status=1
  2. 校验不完整：status=2
3. 支持循环下载，当前scrapy运行失败，或者校验不完整，能继续往下下载, 所有表记录更新完成，就停止进程