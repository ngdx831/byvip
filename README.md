# 会员 Bot

这是一个基于 `python-telegram-bot` 的 Telegram 会员服务 Bot。项目负责用户注册、VIP 权限、积分消费、条件搜索、订阅推送、客服转接、推广统计、USDT 支付检测和管理员运营命令。

## 主要功能

- 用户系统：自动注册、个人中心、黑名单、积分和余额管理。
- VIP 系统：开通 VIP、到期时间管理、VIP 专属订阅推送。
- 搜索系统：支持编号搜索和条件搜索，条件包含城市、省份、标签、年龄、身高、体重和杯罩。
- 内容转发：从采集 Bot 数据库读取帖子，并复制主频道内容和验证视频。
- 订阅推送：普通用户可设置 1 条订阅，VIP 用户可设置 5 条订阅；系统每小时扫描新入库帖子并推送匹配内容。
- 客服系统：用户私聊转发到客服群话题，客服在话题内回复即可回传用户。
- 推广系统：支持邀请链接和来路链接，统计点击、注册和推广奖励。
- 支付检测：通过 TronGrid 检测 TRC20 USDT 转账金额，到账后自动开通 VIP。
- 管理员命令：用户查询、加减 VIP、余额调整、积分调整、统计和测试推送。

## 技术栈

- Python 3.11+
- python-telegram-bot 21.7
- aiohttp 3.9.1
- SQLite
- TronGrid API

## 项目结构

```text
byvip/
├── main.py                    # Bot 启动入口，注册命令和消息分发器
├── requirements.txt           # Python 依赖
├── config/
│   ├── settings.py            # 运行配置，包含 Token、频道、数据库路径等
│   ├── settings.example.py    # 配置样例，不包含真实敏感信息
│   ├── messages.py            # Bot 文案和按钮配置
│   └── city_tag_mapping.json  # 城市、标签和容错映射
├── database/
│   ├── models.py              # 数据库建表逻辑
│   ├── operations.py          # 用户、订单、订阅和统计数据操作
│   └── users.db               # 用户数据库，运行后生成或维护
├── handlers/
│   ├── user_commands.py       # 用户命令和回复键盘处理
│   ├── admin_commands.py      # 管理员命令
│   ├── search_handler.py      # 编号搜索、条件搜索和分页
│   └── customer_service.py    # 客服群话题转发
├── listeners/
│   └── group_listener.py      # 交流群自动回复
├── services/
│   ├── mapper.py              # 城市和标签映射
│   ├── post_fetcher.py        # 只读采集库查询
│   ├── payment_checker.py     # USDT 支付检测
│   ├── subscription_pusher.py # 订阅推送任务
│   └── whitelist.py           # Bot 群组白名单检查
├── utils/
│   ├── auth.py                # 管理员和黑名单校验
│   ├── pagination.py          # 搜索结果分页按钮
│   └── message_formatter.py   # 消息格式化
└── docs/
    ├── DEPLOYMENT.md          # 部署指南
    ├── CONFIGURATION.md       # 配置说明
    ├── COMMANDS.md            # 命令速查
    └── DATABASE.md            # 数据库说明
```

## 快速开始

### 1. 安装依赖

```bash
cd /www/wwwroot/byvip
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. 配置项目

参考 `config/settings.example.py` 检查 `config/settings.py`，至少确认以下配置：

- `TELEGRAM_BOT_TOKEN`
- `ADMIN_USER_IDS`
- `MAIN_CHANNEL_ID`
- `VIDEO_VERIFY_CHANNEL_ID`
- `CUSTOMER_SERVICE_CHAT_ID`
- `ANNOUNCEMENT_TOPIC_ID`
- `MONITORED_GROUP_ID`
- `USDT_WALLET_ADDRESS`
- `BOT_USERNAME`
- `USER_DATABASE_PATH`
- `COLLECTOR_DATABASE_PATH`

详细说明见 [配置说明](docs/CONFIGURATION.md)。

### 3. 初始化数据库

```bash
python database/models.py
```

线上运行时，`main.py` 也会在启动时调用 `init_database(USER_DATABASE_PATH)`。

### 4. 启动 Bot

```bash
python main.py
```

推荐上线时使用 `systemd` 或 `screen` 常驻运行，具体步骤见 [部署指南](docs/DEPLOYMENT.md)。

## 常用命令

用户命令：

- `/start`：注册或进入首页。
- `/me`：查看个人中心。
- `/pay`：创建 VIP 支付订单。
- `/help`：查看搜索帮助。
- `/sub`：查看或添加订阅，普通用户最多 1 条，VIP 用户最多 5 条。
- `/delsub`：删除订阅。

管理员命令：

- `/addvip <user_id> [days]`：开通 VIP。
- `/delvip <user_id>`：取消 VIP。
- `/bal <user_id> <±amount>`：调整余额。
- `/cash <user_id> <±points>`：调整积分。
- `/stats`：查看简版统计。
- `/fullstats`：查看完整统计。

完整命令见 [命令速查](docs/COMMANDS.md)。

## 搜索说明

编号搜索：

```text
251221123045
```

条件搜索：

```text
上海 学生 165 50 20 B
成都 良家 可跨省
广东 人妻 170 C
```

系统会通过 `config/city_tag_mapping.json` 做城市、标签和容错匹配。无法识别的关键词会转发给客服处理。

## 数据库关系

本项目使用两个 SQLite 数据库：

- 会员库：`USER_DATABASE_PATH`，默认线上路径为 `/www/wwwroot/byvip/database/users.db`。
- 采集库：`COLLECTOR_DATABASE_PATH`，默认线上路径为 `/www/wwwroot/bycjbot/database/post.db`，本项目只读。

会员库由本项目维护；采集库由采集 Bot 维护。订阅推送任务每小时查询最近 1 小时的新帖子，匹配用户订阅后直接推送。详细表结构见 [数据库说明](docs/DATABASE.md)。

## 运行前检查

- Bot Token 可用，且 Bot 没有被目标频道或群组限制。
- Bot 已加入主频道、验证视频频道、客服群和监听群。
- 客服群已开启话题功能，并配置了正确的公告话题 ID。
- 采集库路径存在，运行用户对采集库有读取权限。
- `city_tag_mapping.json` 已包含需要支持的城市和标签。
- 服务器可以访问 Telegram API 和 TronGrid API。
- 数据库和日志已纳入备份计划。

## 安全提醒

`config/settings.py` 当前是运行配置文件，里面可能包含真实 Token、群组 ID 和收款地址。不要把真实配置上传到公开仓库。新环境建议先复制 `config/settings.example.py` 的结构，再填入自己的配置。

## 文档

- [部署指南](docs/DEPLOYMENT.md)
- [配置说明](docs/CONFIGURATION.md)
- [命令速查](docs/COMMANDS.md)
- [数据库说明](docs/DATABASE.md)
