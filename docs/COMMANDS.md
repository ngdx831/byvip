# 命令速查

本文档按用户命令、管理员命令和文本搜索三类整理。

## 用户命令

| 命令 | 说明 |
| --- | --- |
| `/start` | 注册用户或显示欢迎信息。支持推广链接、来路链接、搜索深链和编号深链。 |
| `/me` | 查看个人中心，包括用户类型、余额、积分、VIP 到期时间和推广链接。 |
| `/pay` | 创建 VIP 支付订单，生成随机验证金额并启动支付检测任务。 |
| `/help` | 显示搜索帮助。 |
| `/about` | 显示服务介绍。 |
| `/nav` | 显示频道导航。 |
| `/cs` | 显示人工客服说明。 |
| `/sub` | 查看当前订阅规则。 |
| `/sub <条件>` | 添加订阅规则，普通用户最多 1 条，VIP 用户最多 5 条。 |
| `/delsub` | 删除当前用户的所有订阅规则。 |

## 回复键盘按钮

私聊 Bot 时会显示固定回复键盘：

- 频道导航
- 个人中心
- 服务介绍
- 订阅推送
- 人工客服
- 搜索帮助

这些按钮由 `handlers/user_commands.py` 中的 `get_reply_keyboard()` 和 `handle_keyboard_button()` 处理。

## 搜索输入

编号搜索：

```text
251221123045
```

支持 9 位或 12 位纯数字。

条件搜索：

```text
上海 学生 165 50 20 B
成都 良家 可跨省
广东 人妻 170 C
```

解析规则：

- 城市和省份通过 `city_tag_mapping.json` 匹配。
- 标签通过 `city_tag_mapping.json` 匹配。
- 年龄范围：15-35。
- 体重范围：60-140 斤。
- 身高范围：141-195 cm。
- 杯罩范围：A-H。
- 无法识别的关键词会提示用户，并转发给客服。

## 订阅命令示例

查看订阅：

```text
/sub
```

添加订阅：

```text
/sub 上海 学生 165 50 20
/sub 成都 可跨省 20
/sub 广东 18-25 160-170
```

删除订阅：

```text
/delsub
```

订阅规则由 `handlers/user_commands.py` 中的 `parse_subscription_keywords()` 解析。后台任务每小时扫描最近 1 小时新入库的帖子，命中订阅条件后直接推送给用户。

## 管理员命令

| 命令 | 说明 |
| --- | --- |
| `/addvip <user_id> [days]` | 为用户开通 VIP。不传 `days` 时使用 `VIP_DURATION_DAYS`。 |
| `/delvip <user_id>` | 取消用户 VIP，降为普通用户。 |
| `/bal <user_id> <±amount>` | 调整用户余额，单位 USDT。 |
| `/cash <user_id> <±points>` | 调整用户积分。 |
| `/ban <user_id>` | 拉黑用户。 |
| `/unban <user_id>` | 解除拉黑。 |
| `/stats` | 查看简版用户统计。 |
| `/fullstats` | 查看完整统计，包含用户、订单、订阅、推广和采集库数据。 |
| `/linktop` | 查看来路统计 TOP 10。 |
| `/user <user_id>` | 查看用户详情。 |
| `/adminhelp` | 显示管理员帮助。 |
| `/testpush` | 测试推送所有符合条件的用户。 |
| `/testpush <user_id>` | 测试推送指定用户。 |

管理员权限由 `utils/auth.py` 中的 `admin_only` 校验，管理员 ID 配置在 `ADMIN_USER_IDS`。

## 深链格式

推广链接：

```text
https://t.me/<BOT_USERNAME>?start=invite<user_id>
```

来路统计链接：

```text
https://t.me/<BOT_USERNAME>?start=link_xiaohongshu
```

搜索深链：

```text
https://t.me/<BOT_USERNAME>?start=searchchengdu_xuesheng
```

编号深链：

```text
https://t.me/<BOT_USERNAME>?start=251221123045
```
