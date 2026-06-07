"""
权限验证工具
"""
from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import ADMIN_USER_IDS
from database.operations import get_user

def admin_only(func):
    """
    管理员权限装饰器
    """
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        
        if user_id not in ADMIN_USER_IDS:
            await update.message.reply_text("⚠️ 此命令仅限管理员使用")
            return
        
        return await func(update, context, *args, **kwargs)
    
    return wrapper

def vip_only(func):
    """
    VIP权限装饰器
    """
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        user = get_user(user_id)
        
        if not user or user['user_type'] != 'vip':
            await update.message.reply_text(
                "⚠️ 此功能需要VIP权限\n\n"
                "使用 /pay 充值VIP"
            )
            return
        
        return await func(update, context, *args, **kwargs)
    
    return wrapper

def check_blacklist(func):
    """
    黑名单检查装饰器
    """
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        user = get_user(user_id)
        
        if user and user['user_type'] == 'blacklist':
            await update.message.reply_text("🚫 您已被加入黑名单，无法使用此功能")
            return
        
        return await func(update, context, *args, **kwargs)
    
    return wrapper

def check_credits(required_credits: int):
    """
    积分检查装饰器
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            user_id = update.effective_user.id
            user = get_user(user_id)
            
            if not user:
                await update.message.reply_text("⚠️ 请先发送 /start 注册")
                return
            
            if user['credits'] < required_credits:
                await update.message.reply_text(
                    f"⚠️ 积分不足\n\n"
                    f"需要: {required_credits} 积分\n"
                    f"当前: {user['credits']} 积分\n\n"
                    f"💡 获取积分方式：\n"
                    f"• 充值VIP（无限使用）\n"
                    f"• 推广好友（每人5积分）"
                )
                return
            
            return await func(update, context, *args, **kwargs)
        
        return wrapper
    return decorator

async def is_admin(user_id: int) -> bool:
    """检查是否是管理员"""
    return user_id in ADMIN_USER_IDS

async def is_vip(user_id: int) -> bool:
    """检查是否是VIP"""
    user = get_user(user_id)
    return user and user['user_type'] == 'vip'

async def is_blacklisted(user_id: int) -> bool:
    """检查是否被拉黑"""
    user = get_user(user_id)
    return user and user['user_type'] == 'blacklist'
