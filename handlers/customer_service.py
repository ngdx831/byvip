"""
客服系统处理器 - 优化版
- 移除普通回复的"已发送给用户"反馈
- 保留公告推送反馈
"""
from telegram import Update, ForumTopic
from telegram.error import BadRequest
from telegram.ext import ContextTypes
import sys
import os
import sqlite3

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import CUSTOMER_SERVICE_CHAT_ID, ANNOUNCEMENT_TOPIC_ID, USER_DATABASE_PATH
from database.operations import get_user, get_all_user_ids
from utils.html_utils import escape_html

# ==================== 话题映射数据库操作 ====================

def get_topic_id(user_id: int) -> int:
    """从数据库获取用户的话题ID"""
    conn = sqlite3.connect(USER_DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT topic_id FROM user_topics WHERE user_id = ?
    ''', (user_id,))
    
    result = cursor.fetchone()
    conn.close()
    
    return result[0] if result else None

def save_topic_id(user_id: int, topic_id: int):
    """保存用户的话题ID到数据库"""
    conn = sqlite3.connect(USER_DATABASE_PATH)
    cursor = conn.cursor()
    
    # 创建表（如果不存在）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_topics (
            user_id INTEGER PRIMARY KEY,
            topic_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 插入或更新
    cursor.execute('''
        INSERT OR REPLACE INTO user_topics (user_id, topic_id)
        VALUES (?, ?)
    ''', (user_id, topic_id))
    
    conn.commit()
    conn.close()

def get_user_id_by_topic(topic_id: int) -> int:
    """根据话题ID查找用户ID"""
    conn = sqlite3.connect(USER_DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT user_id FROM user_topics WHERE topic_id = ?
    ''', (topic_id,))
    
    result = cursor.fetchone()
    conn.close()
    
    return result[0] if result else None

def _is_missing_topic_error(error: Exception) -> bool:
    """Return True when Telegram rejected a deleted or unavailable forum topic."""
    if not isinstance(error, BadRequest):
        return False

    message = str(error).lower()
    return any(
        marker in message
        for marker in (
            "message thread not found",
            "thread not found",
            "topic not found",
            "message thread is closed",
            "thread is closed",
        )
    )

async def _send_user_message_to_topic(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    topic_id: int,
    user_info: str,
    message_text: str,
):
    forward_text = f"{user_info}\n\n📝 {escape_html(message_text)}"

    await context.bot.send_message(
        chat_id=CUSTOMER_SERVICE_CHAT_ID,
        message_thread_id=topic_id,
        text=forward_text,
        parse_mode='HTML'
    )

    # 如果有图片/视频，也转发
    if update.message.photo:
        await context.bot.send_photo(
            chat_id=CUSTOMER_SERVICE_CHAT_ID,
            message_thread_id=topic_id,
            photo=update.message.photo[-1].file_id
        )
    elif update.message.video:
        await context.bot.send_video(
            chat_id=CUSTOMER_SERVICE_CHAT_ID,
            message_thread_id=topic_id,
            video=update.message.video.file_id
        )
    elif update.message.document:
        await context.bot.send_document(
            chat_id=CUSTOMER_SERVICE_CHAT_ID,
            message_thread_id=topic_id,
            document=update.message.document.file_id
        )

# ==================== 转发到客服 ====================

async def forward_to_customer_service(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    """
    将用户消息转发到客服群
    - 如果用户没有话题，创建新话题
    - 如果有话题，转发到该话题
    """
    user_id = update.effective_user.id
    username = update.effective_user.username or str(user_id)
    
    # 获取用户信息
    user = get_user(user_id)
    
    # 检查是否已有话题
    topic_id = get_topic_id(user_id)
    
    if not topic_id:
        # 创建新话题
        topic_id = await create_topic_for_user(
            context,
            user_id,
            username,
            user
        )
        if topic_id:
            save_topic_id(user_id, topic_id)
    
    if not topic_id:
        print(f"❌ 无法为用户 {user_id} 创建话题")
        return
    
    # 转发消息到话题
    try:
        # 构建转发消息
        user_info = f"👤 @{escape_html(username)} (<code>{user_id}</code>)"
        if user:
            user_info += f"\n💎 {escape_html(user['user_type'])} | ⭐ {escape_html(user['credits'])}积分"
        
        message_text = update.message.text or update.message.caption or "[媒体消息]"
        
        await _send_user_message_to_topic(update, context, topic_id, user_info, message_text)
    except Exception as e:
        if _is_missing_topic_error(e):
            print(f"客服话题已失效，重建话题: user_id={user_id}, old_topic_id={topic_id}")
            new_topic_id = await create_topic_for_user(
                context,
                user_id,
                username,
                user
            )
            if new_topic_id:
                save_topic_id(user_id, new_topic_id)
                try:
                    await _send_user_message_to_topic(update, context, new_topic_id, user_info, message_text)
                    return
                except Exception as retry_error:
                    print(f"重建话题后转发客服失败: {retry_error}")
                    return

        print(f"转发客服失败: {e}")

async def create_topic_for_user(
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int,
    username: str,
    user: dict = None
) -> int:
    """
    为用户创建新话题
    返回话题ID
    """
    try:
        # 话题名称
        topic_name = f"👤 {username}"
        if user:
            topic_name += f" ({user['user_type']})"
        
        # 创建话题
        topic = await context.bot.create_forum_topic(
            chat_id=CUSTOMER_SERVICE_CHAT_ID,
            name=topic_name[:128]  # 话题名称最多128字符
        )
        
        return topic.message_thread_id
    except Exception as e:
        print(f"创建话题失败: {e}")
        return None

# ==================== 客服回复处理 ====================

async def handle_service_reply(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    """
    处理客服群的回复，转发给对应用户
    ✅ 不再发送"已发送给用户"反馈
    """
    # 检查是否在客服群
    if update.effective_chat.id != CUSTOMER_SERVICE_CHAT_ID:
        return
    
    # 检查是否在话题中
    if not update.message.message_thread_id:
        return
    
    topic_id = update.message.message_thread_id
    
    # 跳过公告话题
    if topic_id == ANNOUNCEMENT_TOPIC_ID:
        return
    
    # 从数据库查找对应的用户
    user_id = get_user_id_by_topic(topic_id)
    
    if not user_id:
        await update.message.reply_text(
            "⚠️ 无法找到对应用户\n"
            "💡 请用户先发送消息，建立话题映射"
        )
        return
    
    # 转发消息给用户
    try:
        message_text = update.message.text or update.message.caption or ""
        
        # 发送文本
        if message_text:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"📞 <b>客服回复:</b>\n\n{escape_html(message_text)}",
                parse_mode='HTML'
            )
        
        # 转发媒体
        if update.message.photo:
            await context.bot.send_photo(
                chat_id=user_id,
                photo=update.message.photo[-1].file_id,
                caption=f"📞 <b>客服回复</b>",
                parse_mode='HTML'
            )
        elif update.message.video:
            await context.bot.send_video(
                chat_id=user_id,
                video=update.message.video.file_id,
                caption=f"📞 <b>客服回复</b>",
                parse_mode='HTML'
            )
        elif update.message.document:
            await context.bot.send_document(
                chat_id=user_id,
                document=update.message.document.file_id,
                caption=f"📞 <b>客服回复</b>",
                parse_mode='HTML'
            )
        
        # ✅ 不再发送"已发送给用户"反馈
        
    except Exception as e:
        print(f"发送给用户失败: {e}")
        await update.message.reply_text(f"❌ 发送失败: {e}")

# ==================== 公告推送 ====================

async def handle_announcement(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    """
    处理公告话题的消息，推送给所有用户
    ✅ 保留推送反馈
    """
    # 检查是否在公告话题
    if update.effective_chat.id != CUSTOMER_SERVICE_CHAT_ID:
        return
    
    if not update.message.message_thread_id:
        return
    
    if update.message.message_thread_id != ANNOUNCEMENT_TOPIC_ID:
        return
    
    # 获取所有用户
    user_ids = get_all_user_ids()
    
    if not user_ids:
        await update.message.reply_text("⚠️ 没有用户可推送")
        return
    
    message_text = update.message.text or update.message.caption or ""
    
    # 确认推送
    await update.message.reply_text(
        f"📢 准备推送公告给 {len(user_ids)} 个用户\n"
        f"内容: {escape_html(message_text[:100])}...\n\n"
        f"推送中...",
        parse_mode='HTML'
    )
    
    # 推送给所有用户
    success_count = 0
    failed_count = 0
    
    for user_id in user_ids:
        try:
            # 发送文本
            if message_text:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"📢 <b>系统公告</b>\n\n{escape_html(message_text)}",
                    parse_mode='HTML'
                )
            
            # 转发媒体
            if update.message.photo:
                await context.bot.send_photo(
                    chat_id=user_id,
                    photo=update.message.photo[-1].file_id,
                    caption=f"📢 <b>系统公告</b>",
                    parse_mode='HTML'
                )
            elif update.message.video:
                await context.bot.send_video(
                    chat_id=user_id,
                    video=update.message.video.file_id,
                    caption=f"📢 <b>系统公告</b>",
                    parse_mode='HTML'
                )
            
            success_count += 1
            
            # 每10个用户休息一下，避免被限流
            if success_count % 10 == 0:
                import asyncio
                await asyncio.sleep(1)
            
        except Exception as e:
            failed_count += 1
            print(f"推送失败 {user_id}: {e}")
    
    # 推送完成报告
    await update.message.reply_text(
        f"✅ 公告推送完成\n\n"
        f"成功: {success_count}\n"
        f"失败: {failed_count}",
        parse_mode='HTML'
    )

# ==================== 客服群消息分发 ====================

async def handle_customer_service_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    """
    客服群消息总分发器
    """
    # 只处理客服群消息
    if update.effective_chat.id != CUSTOMER_SERVICE_CHAT_ID:
        return
    
    # 检查是否有话题ID
    if not update.message.message_thread_id:
        return
    
    topic_id = update.message.message_thread_id
    
    # 公告话题 - 推送给所有用户
    if topic_id == ANNOUNCEMENT_TOPIC_ID:
        await handle_announcement(update, context)
        return
    
    # 其他话题 - 回复给对应用户
    await handle_service_reply(update, context)
