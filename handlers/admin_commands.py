"""
管理员命令处理器
"""
from telegram import Update
from telegram.ext import ContextTypes
from datetime import datetime, timedelta
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import VIP_DURATION_DAYS
from database.operations import (
    get_user, update_user_type, update_user_balance,
    update_user_credits, set_vip_expires, get_user_stats,
    get_referral_top, get_user_full_info, get_detailed_stats
)
from utils.auth import admin_only
from utils.message_formatter import (
    format_admin_user_detail, format_stats, format_referral_top,
    format_detailed_stats
)
from services.subscription_pusher import get_pusher

# ==================== /addvip 命令 ====================

@admin_only
async def cmd_addvip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    添加VIP
    用法: /addvip <user_id> [days]
    """
    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "⚠️ 用法: <code>/addvip &lt;user_id&gt; [days]</code>\n\n"
            "示例: <code>/addvip 123456789 30</code>",
            parse_mode='HTML'
        )
        return
    
    try:
        user_id = int(context.args[0])
        days = int(context.args[1]) if len(context.args) > 1 else VIP_DURATION_DAYS
        
        # 检查用户是否存在
        user = get_user(user_id)
        if not user:
            await update.message.reply_text(
                "❌ 用户不存在",
                parse_mode='HTML'
            )
            return
        
        # 设置VIP
        success = set_vip_expires(user_id, days)
        
        if success:
            await update.message.reply_text(
                f"✅ 已为用户 <code>{user_id}</code> 开通VIP\n"
                f"时长: {days}天",
                parse_mode='HTML'
            )
        else:
            await update.message.reply_text(
                "❌ 操作失败",
                parse_mode='HTML'
            )
    except ValueError:
        await update.message.reply_text(
            "❌ 参数错误，请输入有效的数字",
            parse_mode='HTML'
        )

# ==================== /delvip 命令 ====================

@admin_only
async def cmd_delvip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    删除VIP
    用法: /delvip <user_id>
    """
    if not context.args:
        await update.message.reply_text(
            "⚠️ 用法: <code>/delvip &lt;user_id&gt;</code>",
            parse_mode='HTML'
        )
        return
    
    try:
        user_id = int(context.args[0])
        
        success = update_user_type(user_id, 'normal')
        
        if success:
            await update.message.reply_text(
                f"✅ 已将用户 <code>{user_id}</code> 降为普通用户",
                parse_mode='HTML'
            )
        else:
            await update.message.reply_text(
                "❌ 操作失败",
                parse_mode='HTML'
            )
    except ValueError:
        await update.message.reply_text(
            "❌ 参数错误，请输入有效的用户ID",
            parse_mode='HTML'
        )

# ==================== /bal 命令 ====================

@admin_only
async def cmd_bal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    调整余额
    用法: /bal <user_id> <±amount>
    """
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "⚠️ 用法: <code>/bal &lt;user_id&gt; &lt;±amount&gt;</code>\n\n"
            "示例: <code>/bal 123456789 +100</code>",
            parse_mode='HTML'
        )
        return
    
    try:
        user_id = int(context.args[0])
        amount = float(context.args[1])
        
        success = update_user_balance(user_id, amount)
        
        if success:
            await update.message.reply_text(
                f"✅ 已为用户 <code>{user_id}</code> 调整余额\n"
                f"变化: {amount:+.2f} USDT",
                parse_mode='HTML'
            )
        else:
            await update.message.reply_text(
                "❌ 操作失败",
                parse_mode='HTML'
            )
    except ValueError:
        await update.message.reply_text(
            "❌ 参数错误",
            parse_mode='HTML'
        )

# ==================== /cash 命令 ====================

@admin_only
async def cmd_cash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    调整积分
    用法: /cash <user_id> <±points>
    """
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "⚠️ 用法: <code>/cash &lt;user_id&gt; &lt;±points&gt;</code>\n\n"
            "示例: <code>/cash 123456789 +10</code>",
            parse_mode='HTML'
        )
        return
    
    try:
        user_id = int(context.args[0])
        points = int(context.args[1])
        
        success = update_user_credits(user_id, points)
        
        if success:
            await update.message.reply_text(
                f"✅ 已为用户 <code>{user_id}</code> 调整积分\n"
                f"变化: {points:+d} 积分",
                parse_mode='HTML'
            )
        else:
            await update.message.reply_text(
                "❌ 操作失败",
                parse_mode='HTML'
            )
    except ValueError:
        await update.message.reply_text(
            "❌ 参数错误",
            parse_mode='HTML'
        )

# ==================== /ban 命令 ====================

@admin_only
async def cmd_ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    拉黑用户
    用法: /ban <user_id>
    """
    if not context.args:
        await update.message.reply_text(
            "⚠️ 用法: <code>/ban &lt;user_id&gt;</code>",
            parse_mode='HTML'
        )
        return
    
    try:
        user_id = int(context.args[0])
        
        success = update_user_type(user_id, 'blacklist')
        
        if success:
            await update.message.reply_text(
                f"✅ 已拉黑用户 <code>{user_id}</code>",
                parse_mode='HTML'
            )
        else:
            await update.message.reply_text(
                "❌ 操作失败",
                parse_mode='HTML'
            )
    except ValueError:
        await update.message.reply_text(
            "❌ 参数错误",
            parse_mode='HTML'
        )

# ==================== /unban 命令 ====================

@admin_only
async def cmd_unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    解除拉黑
    用法: /unban <user_id>
    """
    if not context.args:
        await update.message.reply_text(
            "⚠️ 用法: <code>/unban &lt;user_id&gt;</code>",
            parse_mode='HTML'
        )
        return
    
    try:
        user_id = int(context.args[0])
        
        success = update_user_type(user_id, 'normal')
        
        if success:
            await update.message.reply_text(
                f"✅ 已解除用户 <code>{user_id}</code> 的拉黑",
                parse_mode='HTML'
            )
        else:
            await update.message.reply_text(
                "❌ 操作失败",
                parse_mode='HTML'
            )
    except ValueError:
        await update.message.reply_text(
            "❌ 参数错误",
            parse_mode='HTML'
        )

# ==================== /stats 命令 ====================

@admin_only
async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    用户统计（简版）
    """
    stats = get_user_stats()
    message = format_stats(stats)
    
    await update.message.reply_text(
        message,
        parse_mode='HTML'
    )

# ==================== /fullstats 命令 ====================

@admin_only
async def cmd_fullstats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    全面统计（包含用户、订单、订阅、推广、采集bot数据）
    """
    await update.message.reply_text(
        "📊 正在统计数据...",
        parse_mode='HTML'
    )
    
    stats = get_detailed_stats()
    message = format_detailed_stats(stats)
    
    await update.message.reply_text(
        message,
        parse_mode='HTML'
    )

# ==================== /linktop 命令 ====================

@admin_only
async def cmd_linktop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    来路TOP10
    """
    top_list = get_referral_top(10)
    message = format_referral_top(top_list)
    
    await update.message.reply_text(
        message,
        parse_mode='HTML'
    )

# ==================== /user 命令 ====================

@admin_only
async def cmd_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    查看用户详情
    用法: /user <user_id>
    """
    if not context.args:
        await update.message.reply_text(
            "⚠️ 用法: <code>/user &lt;user_id&gt;</code>",
            parse_mode='HTML'
        )
        return
    
    try:
        user_id = int(context.args[0])
        
        user = get_user_full_info(user_id)
        
        if not user:
            await update.message.reply_text(
                "❌ 用户不存在",
                parse_mode='HTML'
            )
            return
        
        message = format_admin_user_detail(user)
        
        await update.message.reply_text(
            message,
            parse_mode='HTML'
        )
    except ValueError:
        await update.message.reply_text(
            "❌ 参数错误",
            parse_mode='HTML'
        )

# ==================== /adminhelp 命令 ====================

@admin_only
async def cmd_adminhelp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    管理员帮助
    """
    from config.messages import ADMIN_HELP
    
    await update.message.reply_text(
        ADMIN_HELP,
        parse_mode='HTML'
    )

# ==================== /testpush 命令 ====================

@admin_only
async def cmd_testpush(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    测试推送
    用法: 
    - /testpush : 推送所有用户
    - /testpush <user_id> : 推送指定用户
    """
    pusher = get_pusher(context.bot)
    
    if context.args:
        # 推送指定用户
        try:
            user_id = int(context.args[0])
            await update.message.reply_text(
                f"🧪 开始测试推送用户 <code>{user_id}</code>...",
                parse_mode='HTML'
            )
            
            success = await pusher.manual_push(user_id)
            
            if success:
                await update.message.reply_text(
                    "✅ 测试推送完成",
                    parse_mode='HTML'
                )
            else:
                await update.message.reply_text(
                    "❌ 推送失败",
                    parse_mode='HTML'
                )
        except ValueError:
            await update.message.reply_text(
                "❌ 参数错误",
                parse_mode='HTML'
            )
    else:
        # 推送所有用户
        await update.message.reply_text(
            "🧪 开始测试推送所有用户...",
            parse_mode='HTML'
        )
        
        success = await pusher.manual_push()
        
        if success:
            await update.message.reply_text(
                "✅ 测试推送完成",
                parse_mode='HTML'
            )
        else:
            await update.message.reply_text(
                "❌ 推送失败",
                parse_mode='HTML'
            )