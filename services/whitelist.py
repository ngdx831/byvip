"""
白名单管理服务
防止bot被拉进垃圾群
"""
from telegram import Update
from telegram.ext import ContextTypes
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import WHITELIST_CHATS

# ==================== 白名单检查 ====================

async def check_and_leave_non_whitelist(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    """
    检查bot是否在白名单群组中
    如果不在，自动退出
    """
    # 检查是否是新加入的群组
    if update.my_chat_member:
        new_status = update.my_chat_member.new_chat_member.status
        chat_id = update.my_chat_member.chat.id
        chat_title = update.my_chat_member.chat.title
        
        # 如果bot被添加到群组
        if new_status in ['member', 'administrator']:
            # 检查是否在白名单中
            if chat_id not in WHITELIST_CHATS:
                try:
                    # 发送退出消息
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text="⚠️ 此bot仅限指定群组使用\n"
                             "如有需要请联系管理员"
                    )
                    
                    # 退出群组
                    await context.bot.leave_chat(chat_id)
                    
                    print(f"已退出非白名单群组: {chat_title} ({chat_id})")
                except Exception as e:
                    print(f"退出群组失败: {e}")

async def is_whitelisted_chat(chat_id: int) -> bool:
    """
    检查chat_id是否在白名单中
    """
    return chat_id in WHITELIST_CHATS

# ==================== 动态白名单管理 ====================

def add_to_whitelist(chat_id: int):
    """
    添加到白名单
    """
    if chat_id not in WHITELIST_CHATS:
        WHITELIST_CHATS.append(chat_id)

def remove_from_whitelist(chat_id: int):
    """
    从白名单移除
    """
    if chat_id in WHITELIST_CHATS:
        WHITELIST_CHATS.remove(chat_id)

def get_whitelist() -> list:
    """
    获取白名单列表
    """
    return WHITELIST_CHATS.copy()
