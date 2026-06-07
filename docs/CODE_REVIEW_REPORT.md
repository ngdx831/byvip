# BYVIP 项目代码审查报告

审查日期：2026-06-07

## 审查范围

本次主要审查业务逻辑、功能实现错误、边界条件、安全风险和测试可运行性。重点查看了 Bot 入口、用户命令、管理员命令、搜索、订阅推送、支付检测、客服转发、数据库操作和配置文档。

## 配置文件修改约定

`config/settings.py` 属于本地真实运行配置文件，通常不应由代码审查或功能修复流程直接修改。后续如果需要调整 `settings.py`，必须先向项目负责人确认；默认只修改 `config/settings.example.py`、文档或通过环境变量/部署说明给出建议。

本次修复中曾改动过 `config/settings.py`，原因是审查报告指出真实 Bot Token 和钱包地址存在泄露风险。但如果该文件不会上传 GitHub，更合适的处理方式是：保留本地 `settings.py`，确保 `.gitignore` 排除它，并只在示例配置和文档中说明安全做法。

已验证：

- `py -m py_compile main.py`：通过
- `py -m py_compile database\models.py database\operations.py handlers\user_commands.py handlers\admin_commands.py handlers\search_handler.py handlers\customer_service.py listeners\group_listener.py services\subscription_pusher.py services\post_fetcher.py services\payment_checker.py services\mapper.py services\whitelist.py utils\auth.py utils\pagination.py utils\message_formatter.py`：通过
- `py -m unittest discover -s tests -v`：默认 Windows GBK 控制台下失败，设置 `PYTHONIOENCODING=utf-8` 后 3 个测试通过
- `py -c "import telegram; print(telegram.__version__)"`：当前本地环境未安装 `python-telegram-bot`

## 总体结论

项目主体结构清晰，命令处理、数据层、搜索服务、订阅推送和支付检测已经拆成独立模块，基本方向是对的。但当前存在几类会直接影响线上功能的风险：

1. 支付核销缺少交易唯一性和重启恢复，可能漏单或重复开通 VIP。
2. VIP 到期逻辑定义了但没有被调度，会员可能永不过期。
3. 搜索/订阅的体重解析与帮助文案冲突，示例命令会失败。
4. 多处 HTML 消息未转义，用户输入或数据库字段可能导致 Telegram 发送失败。
5. 真实 Bot Token、数据库和运行产物直接放在项目里，存在泄露和部署风险。

建议优先修复支付、VIP 到期、搜索解析和 HTML 转义，再补充针对这些路径的自动化测试。

## 必须修复

### 1. 支付核销只按金额和时间匹配，可能一笔交易核销多个订单

位置：

- `services/payment_checker.py:66-99`
- `services/payment_checker.py:107-126`
- `database/operations.py:249-263`

问题：

当前 `check_single_payment` 只判断收款地址、金额和交易时间；`payments` 表没有保存 `tx_id/hash`，`complete_payment` 也没有限定订单必须仍是 `pending`。如果两个用户或同一用户产生相同 `verification_amount`，同一笔链上转账可能让多个监控任务都判断为已支付，从而重复开通 VIP、重复加余额、重复给推荐奖励。

建议：

- 在 `payments` 表增加 `tx_id`、`payer_address`、`expired_at`、`completed_at`、`status` 索引。
- 核销时使用数据库事务：`UPDATE payments SET status='completed', tx_id=? WHERE id=? AND status='pending' AND tx_id IS NULL`。
- 对 `tx_id` 建唯一索引，确保同一笔链上交易只能核销一个订单。
- 生成验证金额时检查当前 pending 订单，避免短时间内金额重复。

### 2. Bot 重启后不会恢复 pending 订单监控

位置：

- `handlers/user_commands.py:403-412`
- `database/operations.py:271-297`
- `main.py:171-180`

问题：

订单只在用户执行 `/pay` 后通过内存任务 `checker.start_monitoring(payment_data)` 监控。进程重启后，`active_tasks` 清空，数据库里已有的 `pending` 订单不会重新进入监控。虽然 `get_pending_payments` 已经存在，但没有在启动流程中使用。

建议：

- 在 `post_init` 中加载未过期的 pending 订单并恢复监控。
- 订单超时时写回数据库状态，例如 `expired`。
- 用户再次 `/pay` 时提示已有未过期订单，或自动取消旧订单后再创建新订单。

### 3. 超时订单仍保持 pending，统计和恢复逻辑会失真

位置：

- `services/payment_checker.py:190-204`
- `database/operations.py:271-297`

问题：

监控超时只通知用户并退出任务，没有更新订单状态。这样后台统计会一直把旧订单算作 pending；如果后续补上重启恢复逻辑，还可能恢复已经过期的订单。

建议：

- 增加 `expire_payment(payment_id)`，超时时把状态更新为 `expired`。
- `get_pending_payments` 过滤未过期订单。
- 管理员详情和统计中区分 `pending`、`completed`、`expired`、`cancelled`。

### 4. VIP 到期检查函数没有被调用，VIP 可能永不过期

位置：

- `database/operations.py:206-226`
- 全局搜索结果显示 `check_and_expire_vip` 没有调用点

问题：

代码提供了 `check_and_expire_vip()`，但启动流程、定时任务和用户鉴权都没有调用它。过期用户的 `user_type` 会长期保持 `vip`，搜索验证视频和订阅上限都会继续按 VIP 处理。

建议：

- 在 Bot 启动后创建定时任务，每小时执行一次 `check_and_expire_vip()`。
- 在 `get_user` 或 VIP 鉴权路径中增加轻量校验：发现 `vip_expires_at < now` 时降级。
- 管理员手动 `/delvip` 时同步清空或保留明确的 `vip_expires_at` 策略。

### 5. 搜索和订阅示例里的 `50` 会被判定为体重超出范围

位置：

- `config/messages.py:19-22`
- `config/messages.py:44-47`
- `handlers/search_handler.py:475-491`
- `handlers/user_commands.py:471-480`
- `handlers/user_commands.py:711-731`
- `services/mapper.py:91-140`

问题：

帮助文案和示例多次使用 `50` 表示体重，但解析逻辑把体重限定为 `60-140` 斤，因此 `成都 处女 50 20`、`/sub 上海 学生 165 50 20` 都会失败。项目里已经有 `parse_number_with_unit()`，支持 `50kg`、`50公斤`、`100斤`，但搜索和订阅解析没有调用它。

建议：

- 先统一业务单位：如果用户习惯输入 kg，则把无单位 `50` 解释为 kg 并转换成斤；如果坚持斤，则文案示例不要出现 `50`。
- 在 `parse_search_keywords_strict` 和 `parse_subscription_keywords` 里优先调用 `parse_number_with_unit`。
- 给典型输入加测试：`50`、`50kg`、`100斤`、`165cm`、`1.65m`、`18岁`。

### 6. 用户输入和数据库字段直接拼进 HTML 消息，可能导致发送失败

位置：

- `handlers/customer_service.py:108-120`
- `handlers/customer_service.py:209-217`
- `utils/message_formatter.py:93-142`
- `handlers/search_handler.py:359-377`

问题：

代码大量使用 `parse_mode='HTML'`，但用户消息、客服回复、用户名、搜索关键词、帖子字段、链接等没有做 HTML escape。用户只要发送 `<abc`、`&`、`<b>` 等内容，就可能触发 Telegram `BadRequest: can't parse entities`，导致客服转发、搜索结果或公告推送失败。

建议：

- 统一增加 `html_escape()` 工具，使用 `html.escape(text, quote=True)`。
- 所有来自用户、客服、数据库和外部采集库的字段先 escape，再拼到 HTML 文案。
- URL 字段额外校验协议和格式，避免非法链接破坏 `<a href="">`。

### 7. 配置文件包含真实 Bot Token 和敏感运行配置

位置：

- `config/settings.py:7`
- `config/settings.py:36`
- `database/users.db`

问题：

`settings.py` 中包含真实 Telegram Bot Token、管理员 ID、群组 ID 和收款地址。项目目录中也包含 `database/users.db`。如果该项目被提交、打包或给第三方查看，会造成凭证和用户数据泄露。

建议：

- 立即轮换 Telegram Bot Token。
- 把真实配置改为环境变量读取，例如 `os.environ["TELEGRAM_BOT_TOKEN"]`。
- 保留 `settings.example.py` 作为样例，真实 `settings.py` 加入 `.gitignore`。
- 不要把 `database/users.db`、`__pycache__`、`.test_tmp` 放入版本管理或交付包。

## 建议修改

### 8. 支付金额、VIP 时长和文案不一致

位置：

- `config/settings.py:26-40`
- `handlers/user_commands.py:379-399`
- `services/payment_checker.py:147-158`
- `config/messages.py:90-95`

问题：

配置中 `VIP_PRICE_USDT = 100`、`VIP_DURATION_DAYS = 360`，但 `/pay` 文案显示“时长：30天”；服务介绍写“100 USDT/月”；支付成功文案写“订阅推送（最多2个规则）”，配置实际是 5。另一个疑点是用户实际被要求转账 `verification_amount`，范围是 99.00-99.99，但订单金额和余额增加按 100 处理。

建议：

- 所有文案统一从配置变量渲染，不写死 30 天、月、2 个规则。
- 明确 `verification_amount` 是“实际应付金额”还是“验证小数金额”。如果 VIP 是 100 USDT，建议生成 `100.xx` 或 `99.xx` 时同步订单金额、收入统计和提示。
- 如果余额不是用户可提现/可消费资产，不建议支付成功后 `update_user_balance(user_id, amount)`，避免用户误解为充值余额。

### 9. 推荐人开通 VIP 奖励可能被重复发放

位置：

- `services/payment_checker.py:131-144`
- `config/settings.py:30`

问题：

配置注释写的是“推广用户的新用户开 VIP 时奖励余额”，但当前逻辑只要被推荐用户有 `referrer_id`，每次支付成功都会给推荐人发奖励。用户过期后再次购买，也会重复奖励。

建议：

- 增加字段记录首单奖励是否已发放，例如 `referral_bonus_paid_at`。
- 或按订单表查询该用户是否已有 completed VIP 订单，只对第一笔成功订单发推荐奖励。

### 10. 统计格式化在 0 用户时会除零

位置：

- `utils/message_formatter.py:310-323`

问题：

`format_stats` 直接计算 `stats['vip_users'] / stats['total_users']`。新库、测试库或用户清空后调用 `/stats` 会抛 `ZeroDivisionError`。

建议：

- 参考 `format_detailed_stats` 的写法，先判断 `total_users > 0`。
- 增加空库统计测试。

### 11. 搜索分页未使用配置项

位置：

- `config/settings.py:58-59`
- `handlers/search_handler.py:400-401`
- `handlers/search_handler.py:539`

问题：

配置了 `SEARCH_RESULTS_PER_PAGE` 和 `SEARCH_MAX_RESULTS`，但搜索逻辑写死 `limit=50` 和 `page_size=10`。后续调整配置不会生效。

建议：

- 从 `config.settings` 导入并使用 `SEARCH_MAX_RESULTS`、`SEARCH_RESULTS_PER_PAGE`。
- 测试覆盖配置变更后的分页行为。

### 12. 订阅推送只有成功发送时才标记，本小时无匹配内容会反复检查

位置：

- `services/subscription_pusher.py:60-87`
- `database/operations.py:479-496`

问题：

如果某用户本小时没有匹配新内容，`push_to_user` 直接返回，不调用 `mark_user_pushed`。这会导致该用户在同一小时内仍被 `get_users_need_push_this_hour()` 选中；虽然调度循环每小时跑一次，手动测试或异常重试时会重复扫描。

建议：

- 区分 `last_subscription_checked_at` 和 `last_subscription_pushed_at`。
- 至少在本轮检查结束后记录 checked 时间，避免同一小时重复查同一用户。

### 13. 多标签搜索使用 OR，可能不符合用户对多条件筛选的预期

位置：

- `services/post_fetcher.py:146-164`
- `services/post_fetcher.py:258-270`

问题：

用户搜索 `上海 学生 良家`，直觉上可能希望同时满足“学生”和“良家”，但当前 SQL 是命中任一标签即可。订阅推送也采用 `IN (...)`，同样是 OR 语义。

建议：

- 明确业务预期：多标签是“任一命中”还是“全部命中”。
- 如果要全部命中，改为按 `post_id` 分组并 `HAVING COUNT(DISTINCT t.name)=len(tags)`。
- 帮助文案中明确“多个标签满足任一即可”或“必须全部满足”。

### 14. 客服转发媒体会丢失原 caption

位置：

- `handlers/customer_service.py:123-137`
- `handlers/customer_service.py:219-234`

问题：

用户或客服发送带 caption 的图片/视频时，代码先发送一条文本，再单独发送媒体，但媒体本身 caption 没有保留。客服处理上下文时可能看不到图片对应说明。

建议：

- 对媒体消息直接使用 `copy_message` 或 `forward_message` 到对应话题/用户。
- 如果需要自定义头部信息，可将用户信息作为第一条，再复制原始消息。

## 仅供参考

### 15. 数据库表缺少约束，容易产生非法业务状态

位置：

- `database/models.py:20-70`

建议：

- 给 `user_type`、`payments.status` 增加 CHECK 约束。
- 给 `credits`、`balance` 增加非负约束或在更新时限制不能扣成负数。
- 给订阅数限制增加数据库或事务级保护，避免并发创建超过上限。

### 16. Windows 默认控制台会因为 emoji 打印导致测试失败

位置：

- `database/models.py:114`

现象：

`py -m unittest discover -s tests -v` 在默认 GBK 输出下失败：

```text
UnicodeEncodeError: 'gbk' codec can't encode character '\u2705'
```

设置 `PYTHONIOENCODING=utf-8` 后测试通过。

建议：

- 用 logging 替代直接 print，并避免在库函数初始化时输出 emoji。
- CI 环境显式设置 `PYTHONIOENCODING=utf-8`。

### 17. 本地环境缺少运行依赖

现象：

`py -c "import telegram; print(telegram.__version__)"` 报 `ModuleNotFoundError: No module named 'telegram'`。

建议：

- 在本地或 CI 中执行 `pip install -r requirements.txt`。
- 增加 README 中的虚拟环境和依赖安装步骤。

## 建议修复顺序

1. 立即轮换 Bot Token，并改造配置读取，移除真实数据库和缓存产物。
2. 修复支付核销：交易唯一性、pending 恢复、超时落库、金额文案一致。
3. 接入 VIP 到期检查，补测试。
4. 统一搜索/订阅数值解析和文案，接入 `parse_number_with_unit`。
5. 给所有 HTML 消息增加统一转义。
6. 修复统计除零、分页配置、订阅 checked/pushed 时间。
7. 补充端到端测试：支付核销、VIP 到期、搜索解析、客服转发 HTML 特殊字符、空库统计。
