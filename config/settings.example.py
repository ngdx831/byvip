"""
会员 Bot 配置样例。

复制本文件中的结构到 settings.py，再填入真实配置。
不要把真实 Token、管理员 ID 和收款地址提交到公开仓库。
"""

# ==================== Bot 配置 ====================
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"  # Telegram Bot Token，从 BotFather 获取
ADMIN_USER_IDS = [123456789]  # 管理员 Telegram 用户 ID 列表，可填写多个

# ==================== 数据库配置 ====================
USER_DATABASE_PATH = "/www/wwwroot/byvip/database/users.db"  # 会员 Bot 用户数据库路径
COLLECTOR_DATABASE_PATH = "/www/wwwroot/bycjbot/database/post.db"  # 采集 Bot 帖子数据库路径

# ==================== 频道配置 ====================
MAIN_CHANNEL_ID = -1000000000000  # 主频道 ID，用于发布或引用主频道内容
VIDEO_VERIFY_CHANNEL_ID = -1000000000000  # 验证视频频道 ID，用于存放验证视频

# ==================== 客服群配置 ====================
CUSTOMER_SERVICE_CHAT_ID = -1000000000000  # 客服群 ID，用于接收客服相关消息
ANNOUNCEMENT_TOPIC_ID = 123  # 客服群公告话题 ID，用于发送公告

# ==================== 监听群配置 ====================
MONITORED_GROUP_ID = -1000000000000  # 交流群 ID，用于监听并自动回复

# ==================== VIP 配置 ====================
VIP_PRICE_USDT = 100  # VIP 价格，单位 USDT
VIP_DURATION_DAYS = 360  # VIP 有效期，单位天
DEFAULT_CREDITS = 5  # 新用户默认积分
REFERRAL_CREDITS = 5  # 推广双方获得的积分
REFERRAL_BONUS_BALANCE = 10  # 被推广用户开通 VIP 后，推广人获得的余额奖励
CREDITS_PER_VIDEO = 1  # 非 VIP 用户查看验证视频消耗的积分

# ==================== USDT 支付配置 ====================
USDT_WALLET_ADDRESS = "YOUR_TRC20_USDT_ADDRESS"  # TRC20 USDT 收款钱包地址
PAYMENT_CHECK_INTERVAL_SECONDS = 15  # 单个订单支付检测间隔，单位秒
PAYMENT_TIMEOUT_MINUTES = 10  # 订单超时时间，单位分钟
VERIFICATION_AMOUNT_MIN = 99.00  # 支付验证金额最小值
VERIFICATION_AMOUNT_MAX = 99.99  # 支付验证金额最大值

# ==================== 订阅推送配置 ====================
SUBSCRIPTION_PUSH_ENABLED = True  # 是否启用订阅推送
SUBSCRIPTION_PUSH_INTERVAL_MINUTES = 2  # 每个用户推送间隔，单位分钟
SUBSCRIPTION_SEARCH_HOURS = 1  # 搜索最近多少小时内的新帖子
NORMAL_MAX_SUBSCRIPTIONS = 1  # 普通用户最多可设置的订阅规则数
VIP_MAX_SUBSCRIPTIONS = 5  # VIP 用户最多可设置的订阅规则数

# ==================== 白名单配置 ====================
WHITELIST_CHATS = [
    CUSTOMER_SERVICE_CHAT_ID,  # 客服群
    MONITORED_GROUP_ID,  # 监听交流群
    MAIN_CHANNEL_ID,  # 主频道
    VIDEO_VERIFY_CHANNEL_ID,  # 验证视频频道
]

# ==================== 搜索配置 ====================
SEARCH_RESULTS_PER_PAGE = 10  # 搜索结果每页显示数量
SEARCH_MAX_RESULTS = 50  # 每次搜索最多返回数量
HEIGHT_TOLERANCE = 4  # 身高搜索浮动范围，单位 cm
WEIGHT_TOLERANCE = 4  # 体重搜索浮动范围，单位斤
AGE_TOLERANCE = 2  # 年龄搜索浮动范围，单位岁

# ==================== 其他配置 ====================
BOT_USERNAME = "your_bot_username"  # Bot 用户名，不包含 @
