"""
会员Bot主程序 - 纯回复键盘版本
所有交互使用 Reply Keyboard（输入框上方的固定按钮）
"""
import logging
import asyncio
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ChatMemberHandler,
    filters
)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

from config.settings import TELEGRAM_BOT_TOKEN, CUSTOMER_SERVICE_CHAT_ID, MONITORED_GROUP_ID

from handlers.user_commands import (
    cmd_start, cmd_me, cmd_pay, cmd_help, cmd_about,
    cmd_nav, cmd_cs, cmd_sub, cmd_delsub, 
    handle_callback_query, handle_keyboard_button
)

from handlers.admin_commands import (
    cmd_addvip, cmd_delvip, cmd_bal, cmd_cash,
    cmd_ban, cmd_unban, cmd_stats, cmd_linktop,
    cmd_user, cmd_adminhelp, cmd_testpush, cmd_fullstats
)

from handlers.search_handler import handle_search_page_callback
from handlers.customer_service import handle_customer_service_message
from listeners.group_listener import handle_group_message
from services.whitelist import check_and_leave_non_whitelist
from services.subscription_pusher import get_pusher
from services.payment_checker import get_payment_checker
from database.models import init_database
from database.operations import check_and_expire_vip
from config.settings import USER_DATABASE_PATH

# ==================== 消息过滤器 ====================

async def message_filter(update: Update, context):
    """
    消息分发器
    优先处理回复键盘按钮点击
    """
    if not update.message:
        return
    
    # 1. 客服群消息
    if update.effective_chat.id == CUSTOMER_SERVICE_CHAT_ID:
        await handle_customer_service_message(update, context)
        return
    
    # 2. 交流群消息
    if update.effective_chat.id == MONITORED_GROUP_ID:
        await handle_group_message(update, context)
        return
    
    # 3. 私聊消息
    if update.effective_chat.type == 'private' and update.message.text:
        text = update.message.text.strip()
        
        # ✅ 更新键盘按钮列表（支持 emoji 前缀）
        keyboard_buttons = [
            "频道导航", "📢 频道导航",
            "个人中心", "👤 个人中心",
            "服务介绍", "📖 服务介绍",
            "订阅推送", "📬 订阅推送",  # ← 新增
            "人工客服", "📞 人工客服",
            "搜索帮助", "❓ 搜索帮助",
            "用户统计", "📊 用户统计",
            "管理员帮助", "🔧 管理员帮助",
        ]
        
        if text in keyboard_buttons:
            # 处理键盘按钮点击
            await handle_keyboard_button(update, context)
        else:
            # 普通文本消息，按搜索处理
            from handlers.search_handler import handle_text_message
            await handle_text_message(update, context)

async def callback_query_filter(update: Update, context):
    """回调查询分发器"""
    query = update.callback_query
    data = query.data
    
    # 翻页按钮
    if data.startswith('search_page_'):
        await handle_search_page_callback(update, context)
        return
    
    # 其他回调（兼容性）
    await handle_callback_query(update, context)

async def error_handler(update: Update, context):
    """错误处理器"""
    logger.error(f"Update {update} caused error {context.error}")
    
    if update and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "⚠️ 发生错误，请稍后重试或联系客服"
            )
        except:
            pass

# ==================== 主程序 ====================

def main():
    """主程序入口"""
    
    logger.info("初始化数据库...")
    init_database(USER_DATABASE_PATH)
    
    logger.info("启动Bot...")
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # ========== 用户命令 ==========
    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("me", cmd_me))
    application.add_handler(CommandHandler("pay", cmd_pay))
    application.add_handler(CommandHandler("help", cmd_help))
    application.add_handler(CommandHandler("about", cmd_about))
    application.add_handler(CommandHandler("nav", cmd_nav))
    application.add_handler(CommandHandler("cs", cmd_cs))
    application.add_handler(CommandHandler("sub", cmd_sub))
    application.add_handler(CommandHandler("delsub", cmd_delsub))
    
    # ========== 管理员命令 ==========
    application.add_handler(CommandHandler("addvip", cmd_addvip))
    application.add_handler(CommandHandler("delvip", cmd_delvip))
    application.add_handler(CommandHandler("bal", cmd_bal))
    application.add_handler(CommandHandler("cash", cmd_cash))
    application.add_handler(CommandHandler("ban", cmd_ban))
    application.add_handler(CommandHandler("unban", cmd_unban))
    application.add_handler(CommandHandler("stats", cmd_stats))
    application.add_handler(CommandHandler("fullstats", cmd_fullstats))
    application.add_handler(CommandHandler("linktop", cmd_linktop))
    application.add_handler(CommandHandler("user", cmd_user))
    application.add_handler(CommandHandler("adminhelp", cmd_adminhelp))
    application.add_handler(CommandHandler("testpush", cmd_testpush))
    
    # ========== 消息处理 ==========
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            message_filter
        )
    )
    
    # ========== 回调查询（仅用于翻页）==========
    application.add_handler(CallbackQueryHandler(callback_query_filter))
    
    # ========== 白名单检查 ==========
    application.add_handler(
        ChatMemberHandler(
            check_and_leave_non_whitelist,
            ChatMemberHandler.MY_CHAT_MEMBER
        )
    )
    
    # ========== 错误处理 ==========
    application.add_error_handler(error_handler)
    
    # ========== 启动后初始化 ==========
    async def post_init(application):
        """Bot启动后的初始化"""
        logger.info("启动订阅推送服务...")
        bot = application.bot
        pusher = get_pusher(bot)
        application.create_task(pusher.schedule_loop())

        logger.info("恢复待支付订单监控...")
        checker = get_payment_checker(bot)
        checker.resume_pending_payments()

        async def vip_expiry_loop():
            while True:
                try:
                    expired_count = check_and_expire_vip()
                    if expired_count:
                        logger.info("已过期VIP用户数: %s", expired_count)
                except Exception as e:
                    logger.error("VIP到期检查失败: %s", e)
                await asyncio.sleep(3600)

        application.create_task(vip_expiry_loop())
        logger.info("✅ 订阅推送服务启动成功")
    
    application.post_init = post_init
    
    logger.info("=" * 50)
    logger.info("🚀 Bot启动成功！")
    logger.info("📱 纯回复键盘模式（输入框上方按钮）")
    logger.info("🔍 搜索强制验证映射表")
    logger.info("=" * 50)
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
