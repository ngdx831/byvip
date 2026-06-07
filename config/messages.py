"""
会员Bot所有文案配置 - 优化版
"""
from config.settings import VIP_PRICE_USDT, VIP_DURATION_DAYS, VIP_MAX_SUBSCRIPTIONS

# ==================== 欢迎消息 ====================
WELCOME_MESSAGE = """
👋 <b>欢迎使用SugerVIP Bot！</b>

🔍 <b>搜索示例</b>

1️⃣ <b>编号搜索</b>：
直接发送9位编号
示例：<code>251200733</code>

2️⃣ <b>条件搜索</b>：
格式：城市 标签 身高 体重 年龄 杯罩
多个条件用<b>空格</b>分隔

示例：
• <code>18 学生 165 B</code>
• <code>成都 处女 50kg 20</code>
• <code>广州 良家 170 C 可跨省</code>

💡 点击下方按钮快速访问功能
"""

# ==================== 搜索帮助 ====================
SEARCH_HELP = """
🔍 <b>搜索帮助</b>

<b>━━━━━━━━━━━━━━━━━━━━</b>

<b>1️⃣ 编号搜索</b>
• 直接发送9位或12位编号
• 示例：<code>251221123045</code>
• 自动转发主频道图文
• VIP自动查看验证视频
• 普通用户消耗1积分查看验证视频

<b>━━━━━━━━━━━━━━━━━━━━</b>

<b>2️⃣ 条件搜索</b>

<b>智能识别：</b>
• 年龄：15-35（如：20、18-25）
• 体重：支持 kg/公斤/斤（如：50kg、100斤、80-100）
• 身高：141-195（如：165、165cm、1.65m、155-170）
• 杯罩：A-H（如：B、C、D）

<b>映射表匹配：</b>
• 城市：北京、上海、广州、深圳、成都等
• 省份：广东、浙江、江苏、四川等
• 标签：学生、人妻、良家、SM、可跨省、可出国等

<b>搜索格式：</b>
城市 标签 身高 体重 年龄 杯罩（空格分隔）

<b>示例：</b>
✅ <code>上海 学生 165 B</code>
✅ <code>成都 人妻 50kg 20</code>
✅ <code>广州 良家 170 C 可跨省</code>

❌ <code>上海学生165B</code>（缺少空格）

<b>━━━━━━━━━━━━━━━━━━━━</b>

⚠️ <b>重要提示</b>：
不在映射表的关键词会自动转发客服处理

💡 输入 /help 随时查看此帮助
"""

# ==================== 服务介绍 ====================
SERVICE_INTRO = f"""
📖 <b>服务介绍</b>

<b>━━━━━━━━━━━━━━━━━━━━</b>

🌟 <b>SugerVIP - 您的专属信息平台</b>

<b>【服务内容】</b>
• 实时更新的优质信息
• 智能搜索和筛选功能
• 真实验证视频保障
• 7×24小时客服支持

<b>━━━━━━━━━━━━━━━━━━━━</b>

<b>【会员特权】</b>

💎 <b>VIP会员享受：</b>
• 无限查看验证视频
• 优先推送最新信息
• 订阅推送功能（最多{VIP_MAX_SUBSCRIPTIONS}个规则）
• 专属客服通道
• 推广奖励（新用户开VIP推荐人得10USDT余额）

👤 <b>普通用户：</b>
• 免费搜索和浏览
• 5积分初始额度
• 每查看1个验证视频消耗1积分
• 推广好友双方各得5积分

<b>━━━━━━━━━━━━━━━━━━━━</b>

<b>【价格】</b>
💰 VIP会员：{VIP_PRICE_USDT} USDT / {VIP_DURATION_DAYS}天（TRC20）

<b>【安全保障】</b>
✅ 所有信息经过人工审核
✅ 验证视频真实可靠
✅ 隐私保护严格到位
✅ 支付安全有保障

<b>━━━━━━━━━━━━━━━━━━━━</b>

使用 /pay 立即充值VIP
"""

# ==================== 导航配置 ====================
NAV_CONFIG = {
    "text": """🎯 欢迎来到【甜心包养】官方频道

💎💎💎 我们争做外网国内资源第一 💎💎💎
真实认证 | 安全保障 | 私密可靠 | 高端甄选

💎💎💎 真诚找包养，就选我们💎💎💎
不看虚假照，不聊假资料，我们只做真实资源！

👇 立即进入【甜心包养】高端包养之选！""",

    # 按钮配置：每个子列表是一行按钮
    "buttons": [
        # 第一行：自动会员机器人（独立一行）
        [
            {"text": "自动会员机器人", "url": "https://t.me/sugervip_bot"},
        ],

        # 第二行：主频道
        [
            {"text": "主频道", "url": "https://t.me/sugerbbb"},
        ],

        # 第三行：关于会员费 + 关于介绍费
        [
            {"text": "关于会员费", "url": "https://t.me/sugerbbb/289?single"},
            {"text": "关于介绍费", "url": "https://t.me/sugerbbb/277?single"},
        ],

        # 省份按钮：四个一行
        [
            {"text": "北京", "url": "https://t.me/+diaB_XNjX1diZTk9"},
            {"text": "上海", "url": "https://t.me/+shvLcRdDY49lOTI9"},
            {"text": "天津", "url": "https://t.me/+P67zj-1wyjtmZDBl"},
            {"text": "重庆", "url": "https://t.me/+IkdY0Cze6SI2ZmNl"},
        ],
        [
            {"text": "广东", "url": "https://t.me/+H4eVTkYEInA2Mzg1"},
            {"text": "福建", "url": "https://t.me/+5pnSNPHFQyRiOGU9"},
            {"text": "浙江", "url": "https://t.me/+HgRg2-TW2Zk1ODll"},
            {"text": "江苏", "url": "https://t.me/+9NMvAvmNB9Q0Nzk1"},
        ],
        [
            {"text": "四川", "url": "https://t.me/+xq-JQh67Td04ZDll"},
            {"text": "山东", "url": "https://t.me/+8srh0ky9PvZkZTA1"},
            {"text": "河北", "url": "https://t.me/+GTZPn-O8WwxmZGU1"},
            {"text": "河南", "url": "https://t.me/+YBuf5JdHMj44MDQ1"},
        ],
        [
            {"text": "安徽", "url": "https://t.me/+djyHL8EfNeY4ZmNl"},
            {"text": "湖北", "url": "https://t.me/+-Q7Jj-GPtaBjNWU1"},
            {"text": "湖南", "url": "https://t.me/+sPG8m2uidIY5MDZl"},
            {"text": "江西", "url": "https://t.me/+P4EFxCOTKwE3ZmI9"},
        ],
        [
            {"text": "广西", "url": "https://t.me/+Qx0-__DZbYAyNDE9"},
            {"text": "辽宁", "url": "https://t.me/+PCtvnU6_sVQ3ODM1"},
            {"text": "吉林", "url": "https://t.me/+m7__pY7RtVpmMTA9"},
            {"text": "山西", "url": "https://t.me/+E6aAvKQI1mo4NmZl"},
        ],
        [
            {"text": "海南", "url": "https://t.me/+JYY1a-zZy7dkMWE1"},
            {"text": "云南", "url": "https://t.me/+2kAUNLi-VogzNWZl"},
            {"text": "贵州", "url": "https://t.me/+WSr22TpVoO41NDFl"},
            {"text": "陕西", "url": "https://t.me/+MEmG2eOlqOM4YTdl"},
        ],
        [
            {"text": "甘肃", "url": "https://t.me/+RPGFNUfRbshkYTI1"},
            {"text": "宁夏", "url": "https://t.me/+wDh8SMHJTnE4ZTVl"},
            {"text": "青海", "url": "https://t.me/+Ry0fbK6kub1lZjc1"},
            {"text": "新疆", "url": "https://t.me/+oveaLXtGTFE3OWJl"},
        ],

        # 最后一行 3 个省份
        [
            {"text": "黑龙江", "url": "https://t.me/+2mCscWEhVzo1OWJl"},
            {"text": "内蒙古", "url": "https://t.me/+ALXBz3CjL3JmYjZl"},
            {"text": "西藏", "url": "https://t.me/+BA509gn0dvw2ZjU9"},
        ],

        # 标签快捷搜索
        [
            {"text": "处女", "url": "https://t.me/sugervip_bot?start=searchchunv"},
            {"text": "学生", "url": "https://t.me/sugervip_bot?start=searchxuesheng"},
            {"text": "SM", "url": "https://t.me/sugervip_bot?start=searchsm"},
            {"text": "外围", "url": "https://t.me/siawaiwei"},
        ],
        [
            {"text": "可跨省", "url": "https://t.me/sugervip_bot?start=searchkekuasheng"},
            {"text": "可出国", "url": "https://t.me/sugervip_bot?start=searchkechuguo"},
        ],

        # 底部：会员机器人 + 客服
        [
            {"text": "会员机器人", "url": "https://t.me/sugervip_bot"},
            {"text": "客服里奥", "url": "https://t.me/suger789"},
            {"text": "客服哈尼", "url": "https://t.me/ZL67689"},
        ],
    ],

    "fallback_text": "频道导航暂时不可用，请稍后再试。",
}

# ==================== 服务介绍配置 ====================
SERVICE_CONFIG = {
    # 主文案
    "text": (
        "📘 <b>服务介绍</b>\n\n"
        "你可以通过下方按钮，查看各项说明：\n"
        "• 关于我们\n"
        "• 关于会费\n"
        "• 关于介绍费\n"
        "• 支付流程\n"
        "• 关于私人定制\n"
    ),

    # 按钮配置
    # type 支持：
    #   - "url"      -> 直接打开链接
    #   - "action"   -> 触发机器人回调
    "buttons": [
        {
            "type": "action",
            "action": "about",
            "text": "📘 关于我们",
        },
        {
            "type": "url",
            "text": "💳 关于会费",
            "url": "https://t.me/sugerbbb/289",
        },
        {
            "type": "url",
            "text": "📨 关于介绍费",
            "url": "https://t.me/sugerbbb/277",
        },
        {
            "type": "url",
            "text": "✅ 支付流程",
            "url": "https://t.me/sugerbbb/34",
        },
        {
            "type": "action",
            "action": "custom",
            "text": "🎯 关于私人定制",
        },
    ],

    # 「关于我们」回调的文案
    "about_us_text": (
        "📘 <b>关于我们</b>\n\n"
        "我们致力于为成熟稳重的绅士与优质真实的女生，"
        "提供一个相对安全、相对私密、相对可靠的撮合渠道。\n\n"
        "所有资料会经过基础筛选和人工复核，但不保证 100% 准确，"
        "请务必理性判断与自我保护，如有疑问可随时联系人工客服。"
    ),

    # 「关于私人定制」回调的文案
    "custom_text": (
        "🎯 <b>关于私人定制</b>\n\n"
        "目前私人定制服务采用一对一人工沟通：\n"
        "• 根据你的城市、预算、频次、偏好进行定制筛选；\n"
        "• 由专属聊手进行长期跟进与维护；\n"
        "• 细节与收费标准以实际沟通为准。\n\n"
        "如有定制需求，请发送 /cs 联系顾问。"
    ),
}

# ==================== 保留旧的文本（兼容性）====================
NAVIGATION_TEXT = NAV_CONFIG["text"]
SERVICE_INTRO = SERVICE_CONFIG["text"]

# ==================== 客服消息 ====================
CUSTOMER_SERVICE_MESSAGE = """
📞 <b>联系客服</b>

<b>━━━━━━━━━━━━━━━━━━━━</b>

请直接发送您的问题，我们会尽快回复！

<b>常见问题：</b>
• 充值相关问题
• 搜索使用问题
• VIP权益问题
• 订阅推送问题
• 其他问题

<b>━━━━━━━━━━━━━━━━━━━━</b>

💡 您也可以直接联系客服：
• 客服里奥：@suger789
• 客服哈尼：@ZL67689

⏰ 客服在线时间：7×24小时
"""

# ==================== 订阅推送消息 ====================
SUBSCRIPTION_INTRO = """
📬 <b>订阅推送功能</b>

设置筛选条件，系统会自动推送匹配的最新信息！

<b>可设置条件：</b>
- 城市/省份（如：成都、四川）
- 年龄（如：20）
- 身高（如：165）
- 体重（如：50）
- 标签（如：学生、良家）

<b>设置示例：</b>
<code>/sub 上海 学生 165 50 20</code>

普通用户最多设置 <b>1个订阅规则</b>，VIP用户最多设置 <b>5个订阅规则</b>。
"""

# ==================== 错误消息 ====================
ERROR_NOT_FOUND = "❌ 未找到该编号的帖子\n\n💡 请检查编号是否正确"

ERROR_OFFLINE = "⚠️ 该帖子已下架"

ERROR_INSUFFICIENT_CREDITS = """
⚠️ 积分不足

查看验证视频需要 {required} 积分
您当前积分：{current}

💡 获取积分方式：
• 充值VIP（无限查看）
• 推广好友（每人5积分）

使用 /pay 充值VIP
"""

ERROR_INVALID_SEARCH_FORMAT = """
❌ 搜索格式错误

请使用以下格式：
• 编号搜索：<code>251221123045</code>
• 条件搜索：<code>成都 学生 165 B</code>（用空格分隔）

💡 输入 /help 查看详细帮助
"""

ERROR_UNKNOWN_KEYWORD = """
⚠️ 无法识别的关键词

您的消息已转发客服处理，请稍候...

💡 输入 /help 查看支持的搜索条件
"""

ERROR_BLACKLISTED = "🚫 您已被加入黑名单，无法使用此功能"

# ==================== 管理员命令消息 ====================
ADMIN_HELP = """
━━━━━━━━━━━━━━━━━━━━
🔧 <b>管理员命令</b>
━━━━━━━━━━━━━━━━━━━━

<b>用户管理：</b>
/addvip &lt;user_id&gt; [days] - 添加VIP
/delvip &lt;user_id&gt; - 删除VIP
/bal &lt;user_id&gt; &lt;±金额&gt; - 调整余额
/cash &lt;user_id&gt; &lt;±积分&gt; - 调整积分
/ban &lt;user_id&gt; - 拉黑用户
/unban &lt;user_id&gt; - 解除拉黑

<b>查询统计：</b>
/stats - 用户统计（简版）
/fullstats - 全面统计（详细）
/linktop - 来路TOP10
/user &lt;user_id&gt; - 查看用户详情

<b>系统功能：</b>
/testpush - 测试推送所有用户
/testpush &lt;user_id&gt; - 测试推送指定用户
/adminhelp - 显示此帮助

<b>客服群专用：</b>
在话题中回复消息，自动转发给对应用户
在公告话题发送消息，推送给所有用户

━━━━━━━━━━━━━━━━━━━━
"""

# ==================== 用户命令消息 ====================
USER_COMMANDS = """
📖 <b>常用命令</b>

<b>基础功能：</b>
/start - 开始使用
/me - 个人中心
/help - 搜索帮助
/about - 服务介绍
/nav - 频道导航

<b>VIP功能：</b>
/pay - 充值VIP
/sub - 订阅推送
/delsub - 删除所有订阅

<b>客服支持：</b>
/cs - 呼叫客服

💡 直接发送编号或搜索条件即可开始搜索！
"""
