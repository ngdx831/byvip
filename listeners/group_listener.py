"""
交流群监听器
监听指定群组，自动回复特定关键词
"""
from telegram import Update
from telegram.ext import ContextTypes
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import MONITORED_GROUP_ID, BOT_USERNAME
from config.messages import NAVIGATION_TEXT, CUSTOMER_SERVICE_MESSAGE  # ← 移除 get_navigation_keyboard
from services.mapper import match_city_with_variants, generate_search_link
from telegram import InlineKeyboardButton, InlineKeyboardMarkup  # ← 添加这个

# ==================== 群组消息监听 ====================

async def handle_group_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    """
    监听交流群消息
    - "导航" → 发送导航信息
    - "客服" → 发送客服信息
    - 城市/省份名 → 发送搜索链接
    """
    # 只处理指定群组
    if update.effective_chat.id != MONITORED_GROUP_ID:
        return
    
    # 获取消息文本
    if not update.message or not update.message.text:
        return
    
    text = update.message.text.strip()
    
    # 1. 导航关键词
    if text in ['导航', '频道', '链接']:
        try:
            # ← 直接发送文本，不使用键盘
            await update.message.reply_text(
                NAVIGATION_TEXT,
                parse_mode='HTML'
            )
        except Exception as e:
            print(f"回复导航失败: {e}")
        return
    
    # 2. 客服关键词
    if text in ['客服', '联系客服', '人工', '人工客服']:
        try:
            await update.message.reply_text(
                CUSTOMER_SERVICE_MESSAGE,
                parse_mode='HTML'
            )
        except Exception as e:
            print(f"回复客服失败: {e}")
        return
    
    # 3. 检查是否是城市/省份
    city = match_city_with_variants(text)
    
    if city:
        # 生成搜索链接
        search_link = generate_search_link(city=city)
        
        # ← 使用 Inline Keyboard（群组中可以用）
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(
                f"🔍 搜索 {city}",
                url=search_link
            )]
        ])
        
        try:
            await update.message.reply_text(
                f"🔍 点击按钮搜索 <b>{city}</b> 的信息",
                parse_mode='HTML',
                reply_markup=keyboard
            )
        except Exception as e:
            print(f"回复城市搜索失败: {e}")
        return

# ==================== 群组命令处理 ====================

async def handle_group_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    command: str
):
    """
    处理群组中的特定命令
    """
    # 只处理指定群组
    if update.effective_chat.id != MONITORED_GROUP_ID:
        return
    
    # 可以添加一些群组专用命令
    # 例如: /群统计 /群规则 等
    pass