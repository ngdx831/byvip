# 数据库说明

项目使用 SQLite，并依赖两个数据库。

## 数据库分工

| 数据库 | 路径配置 | 维护方 | 用途 |
| --- | --- | --- | --- |
| 会员库 | `USER_DATABASE_PATH` | 会员 Bot | 用户、订单、订阅、推广、客服话题映射。 |
| 采集库 | `COLLECTOR_DATABASE_PATH` | 采集 Bot | 帖子、标签、媒体数据。本项目只读。 |

## 会员库

会员库由 `database/models.py` 初始化。

### users

用户表。

| 字段 | 说明 |
| --- | --- |
| `id` | 自增主键。 |
| `user_id` | Telegram 用户 ID，唯一。 |
| `username` | Telegram 用户名。 |
| `user_type` | 用户类型：`normal`、`vip`、`blacklist`。 |
| `balance` | 账户余额，单位 USDT。 |
| `credits` | 积分。 |
| `referrer_id` | 推荐人 Telegram 用户 ID。 |
| `referral_count` | 推广人数。 |
| `referral_source` | 来路链接标识。 |
| `vip_expires_at` | VIP 到期时间。 |
| `last_subscription_push` | 最近一次订阅推送时间，用于记录每小时推送任务的执行结果。 |
| `created_at` | 创建时间。 |

### payments

支付订单表。

| 字段 | 说明 |
| --- | --- |
| `id` | 自增主键，也是订单 ID。 |
| `user_id` | 用户 Telegram ID。 |
| `amount_usdt` | VIP 标价金额。 |
| `verification_amount` | 用户实际需要转账的随机验证金额。 |
| `status` | 订单状态：`pending`、`completed`、`expired` 等。 |
| `wallet_address` | 收款地址。 |
| `created_at` | 创建时间。 |
| `completed_at` | 完成时间。 |

### subscriptions

订阅规则表。普通用户最多保留 1 条活跃订阅，VIP 用户最多保留 5 条活跃订阅。

| 字段 | 说明 |
| --- | --- |
| `id` | 自增主键。 |
| `user_id` | 用户 Telegram ID。 |
| `city` | 城市或省份条件。 |
| `age_min` / `age_max` | 年龄范围。 |
| `height_min` / `height_max` | 身高范围。 |
| `weight_min` / `weight_max` | 体重范围。 |
| `tags` | 标签列表，逗号分隔。 |
| `time_slot` | 历史字段，当前订阅推送统一按小时扫描，不再按时间段过滤。 |
| `is_active` | 是否启用。 |
| `created_at` | 创建时间。 |

### referral_stats

来路统计表。

| 字段 | 说明 |
| --- | --- |
| `id` | 自增主键。 |
| `link_code` | 来路标识，例如 `link_xiaohongshu`。 |
| `click_count` | 点击数。 |
| `register_count` | 注册数。 |
| `created_at` | 创建时间。 |

### user_topics

客服话题映射表。

| 字段 | 说明 |
| --- | --- |
| `user_id` | Telegram 用户 ID。 |
| `topic_id` | 客服群中的话题 ID。 |
| `created_at` | 创建时间。 |

## 采集库

采集库由采集 Bot 维护，本项目通过 `services/post_fetcher.py` 只读查询。订阅推送任务每小时扫描最近 1 小时新入库的正常帖子。

### posts

帖子表。

| 字段 | 说明 |
| --- | --- |
| `id` | 自增主键。 |
| `post_number` | 帖子编号，唯一。 |
| `source_channel_id` | 来源频道 ID。 |
| `source_message_link` | 来源消息链接。 |
| `source_message_ids` | 来源消息 ID 列表。 |
| `province` | 省份。 |
| `city` | 城市。 |
| `age` | 年龄。 |
| `cup_size` | 杯罩。 |
| `height` | 身高。 |
| `weight` | 体重。 |
| `pocket_money` | 零花钱字段。 |
| `main_channel_link` | 主频道消息链接。 |
| `video_channel_link` | 验证视频消息链接。 |
| `status` | 状态，正常内容应为 `normal`。 |
| `created_at` | 创建时间。 |

### tags

标签表。

| 字段 | 说明 |
| --- | --- |
| `id` | 自增主键。 |
| `name` | 标签名称，唯一。 |

### post_tags

帖子和标签关联表。

| 字段 | 说明 |
| --- | --- |
| `id` | 自增主键。 |
| `post_id` | 帖子 ID。 |
| `tag_id` | 标签 ID。 |

### media

媒体文件表。

| 字段 | 说明 |
| --- | --- |
| `id` | 自增主键。 |
| `post_id` | 帖子 ID。 |
| `type` | 媒体类型。 |
| `r2_url` | R2 文件地址。 |
| `telegram_file_id` | Telegram 文件 ID。 |
| `created_at` | 创建时间。 |

## 常用检查命令

查看会员库用户数：

```sql
SELECT COUNT(*) FROM users;
```

查看 VIP 用户：

```sql
SELECT user_id, username, vip_expires_at
FROM users
WHERE user_type = 'vip'
ORDER BY vip_expires_at DESC;
```

查看待支付订单：

```sql
SELECT *
FROM payments
WHERE status = 'pending'
ORDER BY created_at DESC;
```

查看采集库最近帖子：

```sql
SELECT post_number, province, city, age, height, weight, status, created_at
FROM posts
ORDER BY created_at DESC
LIMIT 20;
```

## 备份建议

至少备份会员库：

```bash
cp /www/wwwroot/byvip/database/users.db /www/wwwroot/byvip/database/users_backup_$(date +%Y%m%d).db
```

采集库是否需要备份，由采集 Bot 的部署方案决定。
