"""
搜索处理器 - python-telegram-bot 21.7+ 版本
✅ 编号搜索：直接转发主频道消息（自动合并媒体组）
✅ 条件搜索：强制使用映射表匹配
✅ 使用 copy_messages 实现媒体组合并
"""
import sys
import os
import re
from telegram import Update
from telegram.ext import ContextTypes
from telegram.error import TelegramError

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.mapper import (
    match_city_with_variants,
    match_tag_with_variants,
)
from services.query_parser import parse_search_keywords_strict as parse_search_keywords_strict_service
from services.post_fetcher import get_post_by_number, search_posts
from handlers.customer_service import forward_to_customer_service
from database.operations import get_user, update_user_credits
from utils.message_formatter import (
    format_search_results_message,
    format_error_message,
)
from utils.html_utils import escape_html
from utils.pagination import (
    split_results_to_pages,
    generate_pagination_buttons,
)
from config.settings import (
    MAIN_CHANNEL_ID,
    VIDEO_VERIFY_CHANNEL_ID,
    CREDITS_PER_VIDEO,
    SEARCH_MAX_RESULTS,
    SEARCH_RESULTS_PER_PAGE,
)

# ==================== 辅助函数 ====================

def parse_message_link(link: str) -> tuple:
    """
    解析 Telegram 消息链接
    返回: (chat_id, message_id) 或 None
    
    支持格式:
    - 私有频道: https://t.me/c/1003506200357/123
    - 公开频道: https://t.me/username/123
    """
    if not link:
        return None
    
    # 私有频道: https://t.me/c/1003506200357/123
    private_match = re.match(r'https://t\.me/c/(\d+)/(\d+)', link)
    if private_match:
        chat_id = int(f"-100{private_match.group(1)}")
        message_id = int(private_match.group(2))
        return (chat_id, message_id)
    
    # 公开频道: https://t.me/username/123
    public_match = re.match(r'https://t\.me/([^/]+)/(\d+)', link)
    if public_match:
        username = public_match.group(1)
        message_id = int(public_match.group(2))
        return (f"@{username}", message_id)
    
    return None

# ==================== 文本消息处理 ====================

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    处理所有文本消息（编号搜索或条件搜索）
    """
    text = update.message.text.strip()
    
    # 1. 编号搜索（9位或12位纯数字）
    if text.isdigit() and (len(text) == 9 or len(text) == 12):
        await handle_number_search(update, context, text)
        return
    
    # 2. 条件搜索
    await handle_condition_search(update, context, text)

# ==================== 编号搜索 ====================

async def handle_number_search(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    post_number: str
):
    """
    编号搜索（9位或12位）
    
    流程：
    1. 查询数据库获取链接
    2. 转发主频道消息（自动合并媒体组）
    3. 处理验证视频（VIP免费，非VIP扣积分）
    """
    user_id = update.effective_user.id
    user = get_user(user_id)
    
    if not user:
        await update.message.reply_text("⚠️ 请先发送 /start 注册")
        return
    
    # 检查黑名单
    if user['user_type'] == 'blacklist':
        await update.message.reply_text(
            format_error_message('blacklisted')
        )
        return
    
    # 查询帖子
    post = get_post_by_number(post_number)
    
    if not post:
        await update.message.reply_text(
            format_error_message('not_found'),
            parse_mode='HTML'
        )
        return
    
    # 检查状态
    if post['status'] != 'normal':
        await update.message.reply_text(
            format_error_message('offline'),
            parse_mode='HTML'
        )
        return
    
    # ✅ 步骤1：转发主频道消息（支持单张/多张图）
    main_link = post.get('main_channel_link')
    
    if main_link:
        await forward_main_channel_messages(update, context, main_link)
    else:
        await update.message.reply_text(
            "⚠️ 该帖子缺少主频道链接",
            parse_mode='HTML'
        )
    
    # ✅ 步骤2：处理验证视频
    video_link = post.get('video_channel_link')
    if video_link:
        await handle_verification_video(update, context, video_link, user)

async def forward_main_channel_messages(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    main_link: str
):
    """
    转发主频道消息（自动合并媒体组）
    
    支持格式:
    - 单张图: "https://t.me/c/3419735160/123"
    - 多张图: "https://t.me/c/3419735160/123,https://t.me/c/3419735160/124,https://t.me/c/3419735160/125"
    
    使用 copy_messages（21.7+）自动合并媒体组
    """
    
    # 1️⃣ 分割链接（可能是1个或多个）
    if ',' in main_link:
        links = [link.strip() for link in main_link.split(',') if link.strip()]
    else:
        links = [main_link.strip()]
    
    # 2️⃣ 解析所有链接，提取 message_id
    message_ids = []
    chat_id = None
    
    for link in links:
        parsed = parse_message_link(link)
        if not parsed:
            print(f"❌ 无法解析链接: {link}")
            continue
        
        if chat_id is None:
            chat_id = parsed[0]  # 取第一个链接的 chat_id
        
        message_ids.append(parsed[1])
    
    # 检查解析结果
    if not message_ids or not chat_id:
        print(f"❌ 无法解析主频道链接: {main_link}")
        await update.message.reply_text(
            "❌ 无法解析主频道链接",
            parse_mode='HTML'
        )
        return
    
    # 3️⃣ 复制消息
    try:
        if len(message_ids) == 1:
            # 单张图：copy_message（单数）
            await context.bot.copy_message(
                chat_id=update.effective_chat.id,
                from_chat_id=chat_id,
                message_id=message_ids[0]
            )
            print(f"✅ 已复制单张图片: {message_ids[0]}")
        
        else:
            # 多张图：copy_messages（复数，自动合并成媒体组）
            result = await context.bot.copy_messages(
                chat_id=update.effective_chat.id,
                from_chat_id=chat_id,
                message_ids=message_ids
            )
            print(f"✅ 已复制媒体组: {len(message_ids)} 张图片 → {len(result)} 条消息")
    
    except TelegramError as e:
        print(f"❌ 复制主频道消息失败: {e}")
        await update.message.reply_text(
            "❌ 无法获取主频道内容\n"
            "可能是bot没有访问权限，请联系客服",
            parse_mode='HTML'
        )

async def handle_verification_video(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    video_link: str,
    user: dict
):
    """
    处理验证视频
    - VIP: 直接复制
    - 非VIP: 检查积分，扣除后复制
    """
    # 解析视频链接
    parsed = parse_message_link(video_link)
    
    if not parsed:
        print(f"❌ 无法解析验证视频链接: {video_link}")
        return
    
    chat_id, message_id = parsed
    user_id = user['user_id']
    
    try:
        # VIP直接复制
        if user['user_type'] == 'vip':
            await context.bot.copy_message(
                chat_id=update.effective_chat.id,
                from_chat_id=chat_id,
                message_id=message_id
            )
            print(f"✅ VIP用户查看验证视频")
            return
        
        # 非VIP检查积分
        if user['credits'] < CREDITS_PER_VIDEO:
            # 积分不足
            await update.message.reply_text(
                format_error_message(
                    'insufficient_credits',
                    required=CREDITS_PER_VIDEO,
                    current=user['credits']
                ),
                parse_mode='HTML'
            )
            return
        
        # 扣除积分
        success = update_user_credits(user_id, -CREDITS_PER_VIDEO)
        
        if not success:
            await update.message.reply_text(
                "❌ 积分扣除失败，请联系客服",
                parse_mode='HTML'
            )
            return
        
        # 复制视频
        await context.bot.copy_message(
            chat_id=update.effective_chat.id,
            from_chat_id=chat_id,
            message_id=message_id
        )
        
        # 重新查询用户获取最新积分
        updated_user = get_user(user_id)
        remaining_credits = updated_user['credits'] if updated_user else 0
        
        await update.message.reply_text(
            f"✅ 已扣除 {CREDITS_PER_VIDEO} 积分\n"
            f"剩余积分: {remaining_credits}",
            parse_mode='HTML'
        )
        
        print(f"✅ 非VIP用户查看验证视频，扣除{CREDITS_PER_VIDEO}积分")
        
    except TelegramError as e:
        print(f"❌ 复制验证视频失败: {e}")
        
        # 退还积分
        if user['user_type'] != 'vip':
            update_user_credits(user_id, CREDITS_PER_VIDEO)
            await update.message.reply_text(
                "❌ 视频获取失败，已退还积分\n"
                "可能是bot没有访问权限，请联系客服",
                parse_mode='HTML'
            )
    
    except Exception as e:
        print(f"❌ 处理验证视频异常: {e}")
        
        # 退还积分
        if user['user_type'] != 'vip':
            update_user_credits(user_id, CREDITS_PER_VIDEO)
            await update.message.reply_text(
                "❌ 发生错误，已退还积分\n"
                "请联系客服",
                parse_mode='HTML'
            )

# ==================== 条件搜索 ====================

async def handle_condition_search(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    search_text: str
):
    """
    条件搜索 - 强制使用映射表匹配
    """
    user_id = update.effective_user.id
    user = get_user(user_id)
    
    if not user:
        await update.message.reply_text("⚠️ 请先发送 /start 注册")
        return
    
    # 检查黑名单
    if user['user_type'] == 'blacklist':
        await update.message.reply_text(
            format_error_message('blacklisted')
        )
        return
    
    # 分词（空格分隔）
    keywords = search_text.split()
    
    if not keywords:
        await update.message.reply_text(
            "❌ 请输入搜索条件\n\n"
            "格式: 城市 标签 身高 体重 年龄 杯罩\n"
            "示例: <code>上海 学生 165 50 20 B</code>\n\n"
            "已转发客服处理...",
            parse_mode='HTML'
        )
        await forward_to_customer_service(update, context)
        return
    
    # 解析关键词（强制映射表）
    filters, unknown_keywords = parse_search_keywords_strict(keywords)
    
    # 如果有无法识别的关键词，转发客服
    if unknown_keywords:
        await update.message.reply_text(
            f"⚠️ 无法识别以下关键词:\n<code>{escape_html(', '.join(unknown_keywords))}</code>\n\n"
            f"<b>支持的搜索条件:</b>\n"
            f"• 城市: 北京、上海、成都、广州...\n"
            f"• 省份: 广东、浙江、四川...\n"
            f"• 标签: 学生、人妻、良家、可跨省...\n"
            f"• 年龄: 18、20、22...（15-35岁）\n"
            f"• 身高: 160、165、170...（141-195cm）\n"
            f"• 体重: 50、60、70...（60-140斤）\n"
            f"• 杯罩: A、B、C、D...\n\n"
            f"<b>正确示例:</b>\n"
            f"• <code>上海 学生 165 50 20 B</code>\n"
            f"• <code>成都 良家 可跨省</code>\n"
            f"• <code>广东 人妻 170 C</code>\n\n"
            f"已转发客服处理...",
            parse_mode='HTML'
        )
        await forward_to_customer_service(update, context)
        return
    
    # 检查是否有有效条件
    if not any([
        filters.get('city'),
        filters.get('province'),
        filters.get('tags'),
        filters.get('age'),
        filters.get('height'),
        filters.get('weight'),
        filters.get('cup_size')
    ]):
        await update.message.reply_text(
            "❌ 请至少输入一个有效搜索条件\n\n"
            "格式: 城市 标签 身高 体重 年龄 杯罩\n"
            "示例: <code>上海 学生 165 50 20 B</code>\n\n"
            "已转发客服处理...",
            parse_mode='HTML'
        )
        await forward_to_customer_service(update, context)
        return
    
    # 执行搜索
    results = search_posts(filters, limit=SEARCH_MAX_RESULTS)
    
    if not results:
        await update.message.reply_text(
            "❌ 没有找到匹配的结果\n\n"
            "💡 尝试放宽搜索条件或更换关键词",
            parse_mode='HTML'
        )
        return
    
    # 保存搜索结果到context
    context.user_data['search_results'] = results
    context.user_data['search_keyword'] = search_text
    
    # 发送第一页
    await send_search_page(update, context, 0)

def parse_search_keywords_strict(keywords: list) -> tuple:
    """
    严格解析搜索关键词（强制使用映射表）
    
    返回: (filters, unknown_keywords)
    """
    return parse_search_keywords_strict_service(keywords)

async def send_search_page(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    page: int
):
    """
    发送搜索结果页面
    """
    results = context.user_data.get('search_results', [])
    keyword = context.user_data.get('search_keyword', '')
    
    if not results:
        await update.message.reply_text("❌ 没有搜索结果")
        return
    
    # 分页
    pages = split_results_to_pages(results, page_size=SEARCH_RESULTS_PER_PAGE)
    total_pages = len(pages)
    
    if page < 0 or page >= total_pages:
        return
    
    current_page_data = pages[page]
    
    # 格式化消息
    message = format_search_results_message(
        current_page_data,
        page,
        total_pages,
        keyword,
        page_size=SEARCH_RESULTS_PER_PAGE,
    )
    
    # 生成翻页按钮
    keyboard = generate_pagination_buttons(
        page,
        total_pages,
        'search_page'
    )
    
    if keyboard:
        await update.message.reply_text(
            message,
            parse_mode='HTML',
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
    else:
        await update.message.reply_text(
            message,
            parse_mode='HTML',
            disable_web_page_preview=True
        )

# ==================== 翻页回调 ====================

async def handle_search_page_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    """
    处理搜索结果翻页
    """
    query = update.callback_query
    await query.answer()
    
    # 解析页码
    try:
        page = int(query.data.split('_')[2])
    except:
        return
    
    results = context.user_data.get('search_results', [])
    keyword = context.user_data.get('search_keyword', '')
    
    if not results:
        await query.message.reply_text("❌ 搜索结果已过期，请重新搜索")
        return
    
    # 分页
    pages = split_results_to_pages(results, page_size=SEARCH_RESULTS_PER_PAGE)
    total_pages = len(pages)
    
    if page < 0 or page >= total_pages:
        return
    
    current_page_data = pages[page]
    
    # 格式化消息
    message = format_search_results_message(
        current_page_data,
        page,
        total_pages,
        keyword,
        page_size=SEARCH_RESULTS_PER_PAGE,
    )
    
    # 生成翻页按钮
    keyboard = generate_pagination_buttons(
        page,
        total_pages,
        'search_page'
    )
    
    try:
        if keyboard:
            await query.edit_message_text(
                message,
                parse_mode='HTML',
                reply_markup=keyboard,
                disable_web_page_preview=True
            )
        else:
            await query.edit_message_text(
                message,
                parse_mode='HTML',
                disable_web_page_preview=True
            )
    except:
        pass
