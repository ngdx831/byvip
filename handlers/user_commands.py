"""
用户命令处理器 - 修复版
✅ 修复 /sub 命令：支持添加订阅
✅ 使用 Reply Keyboard（输入框上方按钮）
"""
import os
import sys
import random
from datetime import datetime

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import (
    HEIGHT_TOLERANCE, WEIGHT_TOLERANCE, AGE_TOLERANCE,
    DEFAULT_CREDITS, REFERRAL_CREDITS, VIP_PRICE_USDT,
    USDT_WALLET_ADDRESS, VERIFICATION_AMOUNT_MIN, VERIFICATION_AMOUNT_MAX,
    ADMIN_USER_IDS, VIP_DURATION_DAYS,
)
from config.messages import (
    WELCOME_MESSAGE, SEARCH_HELP, SERVICE_INTRO,
    CUSTOMER_SERVICE_MESSAGE, SUBSCRIPTION_INTRO, NAVIGATION_TEXT,
    NAV_CONFIG, SERVICE_CONFIG,
)
from database.operations import (
    create_user, get_user, create_payment,
    get_subscription_count, delete_all_subscriptions,
    get_user_subscriptions, create_subscription,
)
from services.mapper import (
    parse_search_link,
    match_city_with_variants,
    match_tag_with_variants,
)
from services.query_parser import parse_subscription_keywords as parse_subscription_keywords_service
from services.payment_checker import get_payment_checker
from services.subscription_rules import get_subscription_limit
from utils.auth import check_blacklist
from utils.html_utils import escape_html
from utils.message_formatter import format_user_info

# ==================== 回复键盘（输入框上方的按钮）====================

def get_reply_keyboard():
    """
    创建回复键盘（管理员和普通用户都一样）
    """
    keyboard = [
        [
            KeyboardButton("📢 频道导航"),
            KeyboardButton("👤 个人中心"),
            KeyboardButton("📖 服务介绍"),
        ],
        [
            KeyboardButton("📬 订阅推送"),
            KeyboardButton("📞 人工客服"),
            KeyboardButton("❓ 搜索帮助"),
        ],
    ]
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False,
    )

# ==================== Inline 按钮生成 ====================

def generate_nav_keyboard():
    """
    生成导航 Inline Keyboard
    """
    try:
        keyboard = []
        for row in NAV_CONFIG["buttons"]:
            button_row = []
            for btn in row:
                button_row.append(
                    InlineKeyboardButton(
                        text=btn["text"],
                        url=btn["url"]
                    )
                )
            keyboard.append(button_row)
        
        return InlineKeyboardMarkup(keyboard)
    except Exception as e:
        print(f"❌ 生成导航键盘失败: {e}")
        return None

def generate_service_keyboard():
    """
    生成服务介绍 Inline Keyboard
    """
    try:
        keyboard = []
        for btn_config in SERVICE_CONFIG["buttons"]:
            if btn_config["type"] == "url":
                # URL 按钮
                keyboard.append([
                    InlineKeyboardButton(
                        text=btn_config["text"],
                        url=btn_config["url"]
                    )
                ])
            elif btn_config["type"] == "action":
                # 回调按钮
                keyboard.append([
                    InlineKeyboardButton(
                        text=btn_config["text"],
                        callback_data=f"svc_{btn_config['action']}"
                    )
                ])
        
        return InlineKeyboardMarkup(keyboard)
    except Exception as e:
        print(f"❌ 生成服务介绍键盘失败: {e}")
        return None

# ==================== /start 命令 ====================

@check_blacklist
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /start 命令 - 显示欢迎消息和回复键盘
    """
    user_id = update.effective_user.id
    username = update.effective_user.username
    args = context.args

    # 处理特殊链接
    if args and len(args) > 0:
        param = (args[0] or "").strip()

        # 1) 推广链接：invite123456
        if param.startswith("invite"):
            try:
                referrer_id = int(param[6:])
            except Exception:
                referrer_id = None

            if referrer_id:
                await handle_referral_start(update, context, user_id, username, referrer_id)
                return
            # 解析失败就当普通 start 往下走

        # 2) 来路统计：link_xxx
        if param.startswith("link_"):
            link_code = param
            await handle_link_start(update, context, user_id, username, link_code)
            return

        # 3) 搜索/编号深链：searchxxx / 纯数字编号
        parsed = parse_search_link(param)
        if parsed:
            # ✅ 关键修复：深链场景也要先保证用户已注册（静默注册，不发欢迎语）
            if not get_user(user_id):
                create_user(user_id, username)

            if parsed.get("type") == "number":
                await handle_number_start(update, context, parsed["post_number"])
                return

            if parsed.get("type") == "search":
                # ✅ 避免“search但没解析出任何关键词”导致无响应
                has_keywords = bool(parsed.get("city")) or bool(parsed.get("tags"))
                if has_keywords:
                    await handle_search_start(update, context, parsed)
                    return
                # 没关键词就当普通 start 往下走

    # 普通 start
    user = get_user(user_id)
    is_admin = user_id in ADMIN_USER_IDS

    if not user:
        create_user(user_id, username)
        welcome_msg = (
            f"🎉 <b>欢迎新用户！</b>\n\n"
            f"已为您注册账号，赠送 {DEFAULT_CREDITS} 积分\n\n"
            f"{WELCOME_MESSAGE}"
        )
    else:
        welcome_msg = WELCOME_MESSAGE

    # 管理员额外提示（仅在消息中，不改变键盘）
    if is_admin:
        welcome_msg += "\n\n" + "━" * 30 + "\n"
        welcome_msg += "🔧 <b>管理员权限</b>\n"
        welcome_msg += "使用 /adminhelp 查看管理员命令"

    keyboard = get_reply_keyboard()
    await update.message.reply_text(
        welcome_msg,
        parse_mode="HTML",
        reply_markup=keyboard,
    )


# ==================== 处理键盘按钮点击 ====================

async def handle_keyboard_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    处理回复键盘按钮点击
    """
    text = update.message.text.strip()
    
    # 移除 emoji 前缀进行匹配
    text_clean = text.replace("📢 ", "").replace("👤 ", "").replace("📖 ", "")
    text_clean = text_clean.replace("📬 ", "").replace("📞 ", "").replace("❓ ", "")
    
    if "频道导航" in text or "导航" in text_clean:
        # ✅ 使用配置生成导航
        keyboard = generate_nav_keyboard()
        if keyboard:
            await update.message.reply_text(
                NAV_CONFIG["text"],
                parse_mode="HTML",
                reply_markup=keyboard
            )
        else:
            await update.message.reply_text(
                NAV_CONFIG.get("fallback_text", "导航暂时不可用"),
                parse_mode="HTML"
            )
    
    elif "个人中心" in text or "中心" in text_clean:
        await cmd_me(update, context)
    
    elif "服务介绍" in text or "介绍" in text_clean:
        # ✅ 使用配置生成服务介绍
        keyboard = generate_service_keyboard()
        if keyboard:
            await update.message.reply_text(
                SERVICE_CONFIG["text"],
                parse_mode="HTML",
                reply_markup=keyboard
            )
        else:
            await update.message.reply_text(
                "服务介绍暂时不可用",
                parse_mode="HTML"
            )
    
    elif "订阅推送" in text or "订阅" in text_clean:
        await cmd_sub(update, context)
    
    elif "人工客服" in text or "客服" in text_clean:
        await update.message.reply_text(CUSTOMER_SERVICE_MESSAGE, parse_mode="HTML")
    
    elif "搜索帮助" in text or "帮助" in text_clean:
        await update.message.reply_text(SEARCH_HELP, parse_mode="HTML")
    
    else:
        # 其他文本，按搜索处理
        from handlers.search_handler import handle_text_message
        await handle_text_message(update, context)

# ==================== 推广链接处理 ====================

async def handle_referral_start(update, context, user_id, username, referrer_id):
    """处理推广链接"""
    user = get_user(user_id)
    keyboard = get_reply_keyboard()
    
    if user:
        await update.message.reply_text(
            f"👋 欢迎回来！\n\n{WELCOME_MESSAGE}",
            parse_mode="HTML",
            reply_markup=keyboard,
        )
        return

    referrer = get_user(referrer_id)
    if not referrer:
        create_user(user_id, username)
        await update.message.reply_text(
            f"🎉 <b>欢迎新用户！</b>\n\n{WELCOME_MESSAGE}",
            parse_mode="HTML",
            reply_markup=keyboard,
        )
        return

    create_user(user_id, username, referrer_id=referrer_id)
    await update.message.reply_text(
        f"🎉 <b>欢迎新用户！</b>\n\n"
        f"通过推广链接注册成功！\n"
        f"您和推荐人各获得 {REFERRAL_CREDITS} 积分 🎁\n\n"
        f"{WELCOME_MESSAGE}",
        parse_mode="HTML",
        reply_markup=keyboard,
    )

    try:
        await context.bot.send_message(
            chat_id=referrer_id,
            text=f"🎉 推广成功！获得 {REFERRAL_CREDITS} 积分！",
            parse_mode="HTML",
        )
    except:
        pass

async def handle_link_start(update, context, user_id, username, link_code):
    """处理来路统计链接"""
    from database.operations import track_referral_click
    track_referral_click(link_code)

    user = get_user(user_id)
    keyboard = get_reply_keyboard()
    
    if not user:
        create_user(user_id, username, referral_source=link_code)
    
    await update.message.reply_text(
        WELCOME_MESSAGE,
        parse_mode="HTML",
        reply_markup=keyboard,
    )

async def handle_number_start(update, context, post_number):
    """处理编号链接"""
    from handlers.search_handler import handle_number_search
    await handle_number_search(update, context, post_number)

async def handle_search_start(update, context, search_data):
    """处理搜索链接"""
    keywords = []
    if search_data.get("city"):
        keywords.append(search_data["city"])
    if search_data.get("tags"):
        keywords.extend(search_data["tags"])

    if keywords:
        from handlers.search_handler import handle_condition_search
        search_text = " ".join(keywords)
        await handle_condition_search(update, context, search_text)

# ==================== 其他命令 ====================

@check_blacklist
async def cmd_me(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """个人中心"""
    user_id = update.effective_user.id
    user = get_user(user_id)

    if not user:
        await update.message.reply_text("⚠️ 请先发送 /start 注册")
        return

    message = format_user_info(user)
    await update.message.reply_text(message, parse_mode="HTML")

@check_blacklist
async def cmd_pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """充值VIP"""
    user_id = update.effective_user.id
    user = get_user(user_id)

    if not user:
        await update.message.reply_text("⚠️ 请先发送 /start 注册")
        return

    if user["user_type"] == "vip":
        await update.message.reply_text(
            f"💎 您已是VIP\n\n到期: {user.get('vip_expires_at', '未知')}"
        )
        return

    verification_amount = round(
        random.uniform(VERIFICATION_AMOUNT_MIN, VERIFICATION_AMOUNT_MAX), 2
    )

    order_id = create_payment(
        user_id=user_id,
        amount_usdt=VIP_PRICE_USDT,
        verification_amount=verification_amount,
        wallet_address=USDT_WALLET_ADDRESS,
    )

    message = f"""
💳 <b>VIP充值</b>

<b>订单信息：</b>
• 订单号：<code>{order_id}</code>
• 金额：<code>{verification_amount}</code> USDT (TRC20)
• 时长：{VIP_DURATION_DAYS}天

<b>收款地址：</b>
<code>{USDT_WALLET_ADDRESS}</code>

<b>支付说明：</b>
1️⃣ 请使用TRC20网络转账
2️⃣ 转账金额必须完全匹配：<code>{verification_amount}</code> USDT
3️⃣ 转账后系统自动检测（约5-10分钟）
4️⃣ 到账后自动升级VIP

⚠️ 注意：
• 金额不匹配将无法自动到账
• 24小时内未支付订单将自动取消
• 如有问题请联系客服
"""
    await update.message.reply_text(message, parse_mode="HTML")

    payment_data = {
        "id": order_id,
        "user_id": user_id,
        "verification_amount": verification_amount,
        "amount_usdt": VIP_PRICE_USDT,
        "created_at": str(datetime.now()),
    }

    checker = get_payment_checker(context.bot)
    checker.start_monitoring(payment_data)

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """搜索帮助"""
    await update.message.reply_text(SEARCH_HELP, parse_mode="HTML")

async def cmd_about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """服务介绍"""
    await update.message.reply_text(SERVICE_INTRO, parse_mode="HTML")

async def cmd_nav(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """频道导航"""
    await update.message.reply_text(NAVIGATION_TEXT, parse_mode="HTML")

@check_blacklist
async def cmd_cs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """人工客服"""
    await update.message.reply_text(CUSTOMER_SERVICE_MESSAGE, parse_mode="HTML")

# ==================== 订阅推送功能 ====================

@check_blacklist
async def cmd_sub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    订阅推送
    用法：
    - /sub                    显示当前订阅
    - /sub 上海 学生 165 50   添加订阅
    """
    user_id = update.effective_user.id
    user = get_user(user_id)

    if not user:
        await update.message.reply_text("⚠️ 请先发送 /start 注册")
        return

    # 无参数：显示当前订阅
    if not context.args:
        await show_current_subscriptions(update, context, user_id)
        return
    
    # 有参数：添加订阅
    await add_subscription(update, context, user_id, context.args)

async def show_current_subscriptions(update, context, user_id):
    """
    显示当前订阅
    """
    subscriptions = get_user_subscriptions(user_id)
    sub_count = len(subscriptions)
    user = get_user(user_id)
    subscription_limit = get_subscription_limit(user)

    # 简化的订阅介绍
    message = """
📬 <b>订阅推送功能</b>

设置筛选条件，系统会自动推送匹配的最新信息！

<b>可设置条件：</b>
• 城市/省份（如：成都、四川）
• 年龄（如：20）
• 身高（如：165）
• 体重（如：50）
• 标签（如：学生、良家）

<b>设置示例：</b>
<code>/sub 上海 学生 165 50 20</code>

普通用户最多设置 <b>1个订阅规则</b>，VIP用户最多设置 <b>5个订阅规则</b>。
"""

    if sub_count > 0:
        message += f"\n<b>━━━━━━━━━━━━━━━━━━━━</b>\n"
        message += f"<b>您的订阅规则（{sub_count}/{subscription_limit}）：</b>\n\n"
        
        for i, sub in enumerate(subscriptions, 1):
            conditions = []
            
            # 城市/省份
            if sub.get('city'):
                conditions.append(f"📍 {sub['city']}")
            
            # 年龄
            if sub.get('age_min') and sub.get('age_max'):
                conditions.append(f"👤 {sub['age_min']}-{sub['age_max']}岁")
            
            # 身高
            if sub.get('height_min') and sub.get('height_max'):
                conditions.append(f"📏 {sub['height_min']}-{sub['height_max']}cm")
            
            # 体重
            if sub.get('weight_min') and sub.get('weight_max'):
                conditions.append(f"⚖️ {sub['weight_min']}-{sub['weight_max']}斤")
            
            # 标签
            if sub.get('tags'):
                tags_list = sub['tags'].split(',') if sub['tags'] else []
                if tags_list:
                    conditions.append(f"🏷 {', '.join(tags_list)}")
            
            message += f"{i}. " + " | ".join(conditions) + "\n"
        
        message += f"\n💡 使用 <code>/delsub</code> 删除所有订阅"
    else:
        message += f"\n<b>━━━━━━━━━━━━━━━━━━━━</b>\n"
        message += f"<b>当前订阅：</b>0/{subscription_limit}\n"
        message += f"\n💡 使用以下格式添加订阅：\n"
        message += f"<code>/sub 上海 学生 165 50 20</code>"

    await update.message.reply_text(message, parse_mode="HTML")

async def add_subscription(update, context, user_id, args):
    """
    添加订阅
    
    支持的条件：
    - 城市/省份：成都、四川
    - 标签：学生、良家、可跨省
    - 年龄：18、20、22（自动±2岁）
    - 身高：160、165、170（自动±4cm）
    - 体重：50、60、70（自动±4斤）
    """
    # 检查订阅数量限制
    sub_count = get_subscription_count(user_id)
    user = get_user(user_id)
    subscription_limit = get_subscription_limit(user)
    
    if sub_count >= subscription_limit:
        await update.message.reply_text(
            f"⚠️ 订阅数量已达上限（{subscription_limit}个）\n\n"
            f"请先使用 <code>/delsub</code> 删除旧订阅",
            parse_mode="HTML"
        )
        return
    
    # 解析关键词
    search_text = " ".join(args)
    keywords = search_text.split()
    
    if not keywords:
        await update.message.reply_text(
            "❌ 请输入订阅条件\n\n"
            "格式: <code>/sub 城市 标签 身高 体重 年龄</code>\n"
            "示例: <code>/sub 上海 学生 165 50 20</code>",
            parse_mode="HTML"
        )
        return
    
    # 解析订阅条件
    sub_data, unknown_keywords = parse_subscription_keywords(keywords)
    
    # 检查无法识别的关键词
    if unknown_keywords:
        await update.message.reply_text(
            f"⚠️ 无法识别以下关键词:\n<code>{escape_html(', '.join(unknown_keywords))}</code>\n\n"
            f"<b>支持的条件:</b>\n"
            f"• 城市: 北京、上海、成都、广州...\n"
            f"• 省份: 广东、浙江、四川...\n"
            f"• 标签: 学生、人妻、良家、可跨省...\n"
            f"• 年龄: 18、20、22...（15-35岁）\n"
            f"• 身高: 160、165、170...（141-195cm）\n"
            f"• 体重: 50、60、70...（60-140斤）\n\n"
            f"<b>示例:</b>\n"
            f"<code>/sub 上海 学生 165 50 20</code>",
            parse_mode="HTML"
        )
        return
    
    # 检查是否有有效条件
    if not any([
        sub_data.get('city'),
        sub_data.get('age_min'),
        sub_data.get('height_min'),
        sub_data.get('weight_min'),
        sub_data.get('tags')
    ]):
        await update.message.reply_text(
            "❌ 请至少输入一个有效条件\n\n"
            "示例: <code>/sub 上海 学生 165 50 20</code>",
            parse_mode="HTML"
        )
        return
    
    # 添加用户ID
    sub_data['user_id'] = user_id
    
    # 创建订阅
    try:
        sub_id = create_subscription(user_id, sub_data)
        
        if sub_id:
            # 生成订阅摘要
            conditions = []
            
            if sub_data.get('city'):
                conditions.append(f"📍 {sub_data['city']}")
            
            if sub_data.get('age_min') and sub_data.get('age_max'):
                conditions.append(f"👤 {sub_data['age_min']}-{sub_data['age_max']}岁")
            
            if sub_data.get('height_min') and sub_data.get('height_max'):
                conditions.append(f"📏 {sub_data['height_min']}-{sub_data['height_max']}cm")
            
            if sub_data.get('weight_min') and sub_data.get('weight_max'):
                conditions.append(f"⚖️ {sub_data['weight_min']}-{sub_data['weight_max']}斤")
            
            if sub_data.get('tags'):
                tags_list = sub_data['tags']
                conditions.append(f"🏷 {', '.join(tags_list)}")
            
            await update.message.reply_text(
                f"✅ <b>订阅添加成功！</b>\n\n"
                f"<b>订阅条件：</b>\n" + " | ".join(conditions) + "\n\n"
                f"<b>当前订阅：</b>{sub_count + 1}/{subscription_limit}\n\n"
                f"💡 使用 <code>/sub</code> 查看所有订阅\n"
                f"💡 使用 <code>/delsub</code> 删除所有订阅",
                parse_mode="HTML"
            )
        else:
            await update.message.reply_text(
                "❌ 订阅添加失败\n\n请稍后重试或联系客服",
                parse_mode="HTML"
            )
    
    except Exception as e:
        print(f"❌ 创建订阅失败: {e}")
        await update.message.reply_text(
            f"❌ 订阅创建失败: {str(e)}\n\n请联系客服",
            parse_mode="HTML"
        )

def parse_subscription_keywords(keywords: list) -> tuple:
    """
    解析订阅关键词（带严格验证）
    
    验证规则：
    - 标签必须在映射表中
    - 身高: 141-195cm
    - 体重: 60-140斤
    - 年龄: 15-35岁
    
    返回: (sub_data, unknown_keywords)
    """
    return parse_subscription_keywords_service(keywords)

@check_blacklist
async def cmd_delsub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    删除订阅
    """
    user_id = update.effective_user.id
    user = get_user(user_id)
    
    if not user:
        await update.message.reply_text("⚠️ 请先发送 /start 注册")
        return
    
    # 删除所有订阅
    try:
        deleted_count = delete_all_subscriptions(user_id)
        
        if deleted_count > 0:
            await update.message.reply_text(
                f"✅ 已删除 {deleted_count} 个订阅规则\n\n"
                f"💡 使用 <code>/sub 城市 标签 身高</code> 添加新订阅",
                parse_mode="HTML"
            )
        else:
            await update.message.reply_text(
                "ℹ️ 您当前没有订阅规则\n\n"
                "💡 使用 <code>/sub 城市 标签 身高</code> 添加订阅",
                parse_mode="HTML"
            )
    except Exception as e:
        print(f"❌ 删除订阅失败: {e}")
        await update.message.reply_text(
            f"❌ 删除订阅失败: {str(e)}\n\n请联系客服",
            parse_mode="HTML"
        )

# ==================== 服务介绍回调处理 ====================

async def handle_service_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    处理服务介绍的 Inline 按钮回调
    """
    query = update.callback_query
    await query.answer()
    
    # 解析回调数据
    data = query.data
    
    if data == "svc_about":
        # 关于我们
        await query.message.reply_text(
            SERVICE_CONFIG["about_us_text"],
            parse_mode="HTML"
        )
    
    elif data == "svc_custom":
        # 关于私人定制
        await query.message.reply_text(
            SERVICE_CONFIG["custom_text"],
            parse_mode="HTML"
        )
    
    else:
        await query.message.reply_text("未知操作")

# ==================== 回调处理（兼容旧代码）====================

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    处理按钮回调
    """
    query = update.callback_query
    data = query.data
    
    # 服务介绍回调
    if data.startswith("svc_"):
        await handle_service_callback(update, context)
        return
    
    # 其他回调（兼容性）
    await query.answer("请使用搜索功能")
