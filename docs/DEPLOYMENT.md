# 部署指南

本文档说明如何在 Linux 服务器上部署会员 Bot。默认项目目录为 `/www/wwwroot/byvip`。

## 1. 上传代码

```bash
ssh root@your_server_ip
mkdir -p /www/wwwroot/byvip
cd /www/wwwroot/byvip
```

将项目文件上传到 `/www/wwwroot/byvip`。如果服务器上已有旧版本，建议先备份 `database/users.db` 和 `config/settings.py`。

## 2. 创建运行环境

```bash
cd /www/wwwroot/byvip
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

依赖安装完成后，可用以下命令确认包版本：

```bash
python -m pip show python-telegram-bot aiohttp
```

## 3. 配置 Bot

编辑 `config/settings.py`，至少确认：

```python
TELEGRAM_BOT_TOKEN = "你的 Bot Token"
ADMIN_USER_IDS = [123456789]

USER_DATABASE_PATH = "/www/wwwroot/byvip/database/users.db"
COLLECTOR_DATABASE_PATH = "/www/wwwroot/bycjbot/database/post.db"

MAIN_CHANNEL_ID = -100xxxxxxxxxx
VIDEO_VERIFY_CHANNEL_ID = -100xxxxxxxxxx
CUSTOMER_SERVICE_CHAT_ID = -100xxxxxxxxxx
ANNOUNCEMENT_TOPIC_ID = 123
MONITORED_GROUP_ID = -100xxxxxxxxxx

USDT_WALLET_ADDRESS = "你的 TRC20 USDT 地址"
BOT_USERNAME = "your_bot_username"
```

详细配置见 `docs/CONFIGURATION.md`。

## 4. 初始化会员数据库

```bash
python database/models.py
```

如果使用默认线上路径，运行用户需要有 `/www/wwwroot/byvip/database` 的写入权限。

## 5. 检查采集数据库

本项目会只读访问采集 Bot 数据库：

```bash
ls -lh /www/wwwroot/bycjbot/database/post.db
```

如果文件不存在，条件搜索和编号搜索会失败。请先部署或同步采集 Bot 的 `post.db`。

## 6. 前台测试启动

```bash
python main.py
```

正常情况下会看到类似日志：

```text
初始化数据库...
启动Bot...
Bot启动成功！
```

在 Telegram 私聊 Bot 发送 `/start`、`/me` 和 `/help` 做基础验证。

## 7. 后台运行

### 方式一：screen

```bash
screen -S byvip
cd /www/wwwroot/byvip
source venv/bin/activate
python main.py
```

按 `Ctrl+A`，再按 `D` 退出 screen。重新进入：

```bash
screen -r byvip
```

### 方式二：systemd

创建 `/etc/systemd/system/byvip.service`：

```ini
[Unit]
Description=BYVIP Telegram Bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/www/wwwroot/byvip
ExecStart=/www/wwwroot/byvip/venv/bin/python /www/wwwroot/byvip/main.py
Restart=always
RestartSec=5
User=root

[Install]
WantedBy=multi-user.target
```

启动并设置开机自启：

```bash
systemctl daemon-reload
systemctl enable byvip
systemctl start byvip
systemctl status byvip
```

查看日志：

```bash
journalctl -u byvip -f
```

## 8. BotFather 命令菜单

在 BotFather 中为 Bot 设置命令：

```text
start - 开始使用
me - 个人中心
pay - 充值 VIP
help - 搜索帮助
about - 服务介绍
nav - 频道导航
cs - 人工客服
sub - 订阅推送
delsub - 删除订阅
```

## 9. 功能验收

用户侧：

- `/start` 能注册用户。
- `/me` 能查看积分、余额、VIP 状态。
- `/help` 能显示搜索说明。
- 发送编号能查询帖子。
- 发送条件搜索能返回分页结果。
- `/pay` 能创建支付订单。

管理员侧：

- `/adminhelp` 能显示管理员命令。
- `/stats` 能返回统计。
- `/addvip <user_id> 30` 能开通 VIP。
- `/testpush <user_id>` 能触发订阅推送测试。
- 普通用户能添加 1 条订阅，VIP 用户能添加 5 条订阅。
- 订阅推送服务每小时扫描最近 1 小时新入库帖子，并向匹配用户推送。

客服侧：

- 用户发送无法识别的关键词后，消息能转发到客服群话题。
- 客服在用户话题中回复后，消息能回传给用户。
- 公告话题中发送内容时，能按代码逻辑推送给用户。

## 10. 数据备份

建议每天备份会员库：

```bash
cp /www/wwwroot/byvip/database/users.db /www/wwwroot/byvip/database/users_backup_$(date +%Y%m%d).db
```

crontab 示例：

```cron
0 2 * * * cp /www/wwwroot/byvip/database/users.db /www/wwwroot/byvip/database/users_backup_$(date +\%Y\%m\%d).db
```

## 11. 常见问题

### Bot 收不到消息

检查 Bot Token、Bot 是否被用户拉黑、服务器是否能访问 Telegram、`run_polling` 是否正常运行。

### 搜索不到结果

检查 `COLLECTOR_DATABASE_PATH` 是否正确，采集库是否存在，运行用户是否有读取权限，采集库中的 `posts.status` 是否为 `normal`。

### 客服系统不工作

检查客服群是否开启话题功能，`CUSTOMER_SERVICE_CHAT_ID` 和 `ANNOUNCEMENT_TOPIC_ID` 是否正确，Bot 是否有群管理员权限。

### 支付检测不到账

检查 `USDT_WALLET_ADDRESS` 是否为 TRC20 地址，服务器是否能访问 TronGrid，用户转账金额是否和订单验证金额完全一致。
