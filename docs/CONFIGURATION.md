# 配置说明

项目配置集中在 `config/settings.py`。新环境可参考 `config/settings.example.py`。

## Bot 配置

| 配置项 | 说明 | 是否必填 |
| --- | --- | --- |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token，从 BotFather 获取。 | 是 |
| `ADMIN_USER_IDS` | 管理员 Telegram 用户 ID 列表。 | 是 |
| `BOT_USERNAME` | Bot 用户名，不包含 `@`。 | 是 |

## 数据库配置

| 配置项 | 说明 | 是否必填 |
| --- | --- | --- |
| `USER_DATABASE_PATH` | 会员 Bot 自己维护的 SQLite 数据库路径。 | 是 |
| `COLLECTOR_DATABASE_PATH` | 采集 Bot 的帖子数据库路径，本项目只读。 | 是 |

默认线上路径：

```python
USER_DATABASE_PATH = "/www/wwwroot/byvip/database/users.db"
COLLECTOR_DATABASE_PATH = "/www/wwwroot/bycjbot/database/post.db"
```

## 频道和群组配置

| 配置项 | 说明 | 是否必填 |
| --- | --- | --- |
| `MAIN_CHANNEL_ID` | 主频道 ID，用于复制主频道帖子内容。 | 是 |
| `VIDEO_VERIFY_CHANNEL_ID` | 验证视频频道 ID。 | 是 |
| `CUSTOMER_SERVICE_CHAT_ID` | 客服群 ID。 | 是 |
| `ANNOUNCEMENT_TOPIC_ID` | 客服群公告话题 ID。 | 是 |
| `MONITORED_GROUP_ID` | 交流群 ID，群内关键词会触发自动回复。 | 是 |
| `WHITELIST_CHATS` | 允许 Bot 留在其中的群组或频道。 | 是 |

`WHITELIST_CHATS` 默认包含客服群、交流群、主频道和验证视频频道。Bot 被拉进其他群时，会通过 `services/whitelist.py` 自动离开。

## VIP 和积分配置

| 配置项 | 说明 | 默认值 |
| --- | --- | --- |
| `VIP_PRICE_USDT` | VIP 标价，单位 USDT。 | `100` |
| `VIP_DURATION_DAYS` | VIP 有效期，单位天。 | `360` |
| `DEFAULT_CREDITS` | 新用户默认积分。 | `5` |
| `REFERRAL_CREDITS` | 推广注册后双方获得的积分。 | `5` |
| `REFERRAL_BONUS_BALANCE` | 被推广用户开通 VIP 后，推荐人获得的余额奖励。 | `10` |
| `CREDITS_PER_VIDEO` | 非 VIP 查看验证视频消耗的积分。 | `1` |

注意：当前部分文案中可能写着「30 天」或「月」。如果调整 `VIP_DURATION_DAYS`，也要同步检查 `config/messages.py` 和支付提示文案。

## USDT 支付配置

| 配置项 | 说明 | 默认值 |
| --- | --- | --- |
| `USDT_WALLET_ADDRESS` | TRC20 USDT 收款地址。 | 需要替换 |
| `PAYMENT_CHECK_INTERVAL_SECONDS` | 单订单检测间隔，单位秒。 | `15` |
| `PAYMENT_TIMEOUT_MINUTES` | 订单超时时间，单位分钟。 | `10` |
| `VERIFICATION_AMOUNT_MIN` | 随机验证金额下限。 | `99.00` |
| `VERIFICATION_AMOUNT_MAX` | 随机验证金额上限。 | `99.99` |

支付检测逻辑位于 `services/payment_checker.py`，会调用 TronGrid 查询最近 TRC20 USDT 转账记录。用户转账金额需要与订单中的验证金额匹配。

## 订阅推送配置

| 配置项 | 说明 | 默认值 |
| --- | --- | --- |
| `SUBSCRIPTION_PUSH_ENABLED` | 是否启用订阅推送。 | `True` |
| `SUBSCRIPTION_PUSH_INTERVAL_MINUTES` | 每个用户之间的推送间隔，避免触发 Telegram 频率限制。 | `2` |
| `SUBSCRIPTION_SEARCH_HOURS` | 每轮推送扫描最近多少小时的新入库帖子。 | `1` |
| `NORMAL_MAX_SUBSCRIPTIONS` | 普通用户最多订阅规则数。 | `1` |
| `VIP_MAX_SUBSCRIPTIONS` | VIP 用户最多订阅规则数。 | `5` |

订阅推送任务每小时运行一次。每轮任务会扫描最近 `SUBSCRIPTION_SEARCH_HOURS` 小时内新入库、状态为 `normal` 的帖子，匹配用户的活跃订阅后直接推送。

## 搜索配置

| 配置项 | 说明 | 默认值 |
| --- | --- | --- |
| `SEARCH_RESULTS_PER_PAGE` | 搜索结果每页数量。 | `10` |
| `SEARCH_MAX_RESULTS` | 单次搜索最多返回数量。 | `50` |
| `HEIGHT_TOLERANCE` | 身高匹配浮动范围，单位 cm。 | `4` |
| `WEIGHT_TOLERANCE` | 体重匹配浮动范围，单位斤。 | `4` |
| `AGE_TOLERANCE` | 年龄匹配浮动范围，单位岁。 | `2` |

城市、标签和容错词在 `config/city_tag_mapping.json` 中维护。修改映射后需要重启 Bot。

## 安全建议

- 不要把真实 `TELEGRAM_BOT_TOKEN` 提交到公开仓库。
- 不要公开 `USDT_WALLET_ADDRESS` 以外的管理配置。
- 数据库备份文件不要放在可公开访问的目录。
- 如果多人协作，建议把真实配置迁移为环境变量或独立私有配置文件。
