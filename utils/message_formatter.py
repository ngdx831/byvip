"""
消息格式化工具 - 修复版
优化搜索结果显示
"""
from datetime import datetime
from typing import List, Dict
from utils.html_utils import escape_html, safe_html_url


def generate_referral_link(user_id: int) -> str:
    """
    生成推广链接
    """
    from config.settings import BOT_USERNAME
    return f"https://t.me/{BOT_USERNAME}?start=invite{user_id}"


def generate_tracking_link(code: str) -> str:
    """
    生成来路统计链接
    """
    from config.settings import BOT_USERNAME
    return f"https://t.me/{BOT_USERNAME}?start=link_{code}"


def format_post_number(post_number: str) -> str:
    """
    格式化帖子编号（等宽字体，方便复制）
    """
    return f"<code>{post_number}</code>"


def format_user_id(user_id: int) -> str:
    """
    格式化用户ID（添加复制提示）
    """
    return f"<code>{user_id}</code>"


def format_amount(amount: float) -> str:
    """
    格式化金额
    """
    return f"{amount:.2f}"


def format_timestamp(timestamp: str, format: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    格式化时间戳
    """
    try:
        dt = datetime.fromisoformat(timestamp)
        return dt.strftime(format)
    except Exception:
        return timestamp


def format_month_day(timestamp: str) -> str:
    """
    格式化为月/日
    """
    return format_timestamp(timestamp, "%m/%d")


def escape_markdown(text: str) -> str:
    """
    转义Markdown特殊字符（用于MarkdownV2）
    """
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text


def format_search_result_item(post: Dict, index: int) -> str:
    """
    格式化单条搜索结果 - 优化版

    显示内容:
    - 编号（等宽格式）
    - 省份 城市
    - 年龄 身高 体重 杯罩
    - 零花钱 标签（不带#）
    - 时间
    - 主频道链接
    """
    # 标签不带#
    tags = post.get('tags', [])
    tag_text = ' '.join(escape_html(tag) for tag in tags) if tags else "无"

    # 格式化时间
    time_str = format_month_day(post.get('created_at', ''))

    # 省份和城市
    location = ''
    if post.get('province'):
        location += escape_html(post['province'])
    if post.get('city'):
        if location:
            location += ' '
        location += escape_html(post['city'])
    if not location:
        location = '未知地区'

    # 基本信息
    age = escape_html(post.get('age', '?'))
    height = escape_html(post.get('height', '?'))
    weight = escape_html(post.get('weight', '?'))
    cup_size = escape_html(post.get('cup_size', '?'))
    pocket_money = escape_html(post.get('pocket_money', '面议'))

    # 主频道链接（只取第一个）
    main_link = post.get('main_channel_link', '#')

    # 兼容 list/tuple
    if isinstance(main_link, (list, tuple)):
        main_link = main_link[0] if main_link else '#'

    # 兼容字符串里拼了多个链接：逗号/中文逗号/换行/空格
    if isinstance(main_link, str):
        s = main_link.strip()
        if not s or s == '#':
            main_link = '#'
        else:
            s = s.replace('，', ',').replace('\n', ',').strip()
            # 优先逗号分隔
            if ',' in s:
                main_link = s.split(',', 1)[0].strip() or '#'
            else:
                # 没逗号就按空白切第一个（URL 不应含空格）
                parts = s.split()
                main_link = parts[0].strip() if parts else '#'

    main_link = safe_html_url(main_link)

    result = f"""
{index}. <code>{escape_html(post['post_number'])}</code>
📍 {location}
👤 {age}岁 | {height}cm | {weight}斤 | {cup_size}杯
💰 {pocket_money} | {tag_text}
📅 {time_str}"""

    # 添加主频道链接
    if main_link:
        result += f" | <a href=\"{main_link}\">📱查看详情</a>"

    result += "\n"

    return result


def format_search_results_message(
    results: List[Dict],
    page: int,
    total_pages: int,
    keyword: str = None,
    page_size: int = 10,
) -> str:
    """
    格式化搜索结果列表 - 优化版

    改进:
    - 显示省份和城市
    - 标签不带#
    - 编号等宽格式
    - 更清晰的布局
    """
    if not results:
        return "❌ 没有找到匹配的结果"

    header = "🔍 <b>搜索结果</b>"
    if keyword:
        header += f" - {escape_html(keyword)}"
    header += f"\n\n📄 第 {page + 1}/{total_pages} 页 | 共 {len(results)} 条\n"

    result_text = ""
    for i, post in enumerate(results, 1):
        result_text += format_search_result_item(post, (page * page_size) + i)

    footer = "\n💡 复制编号后发送，即可查看完整信息"

    return header + result_text + footer


def format_post_caption(post: Dict) -> str:
    """
    格式化帖子标题（用于发送媒体组）
    """
    tags = post.get('tags', [])
    tag_text = ' '.join([f"#{tag}" for tag in tags]) if tags else ""

    caption = f"""
📋 <b>编号</b>: #{post['post_number']}

📍 <b>地区</b>: {post.get('province', '?')} {post.get('city', '?')}
👤 <b>年龄</b>: {post.get('age', '?')}岁
📏 <b>身高</b>: {post.get('height', '?')}cm
⚖️ <b>体重</b>: {post.get('weight', '?')}斤
👙 <b>杯罩</b>: {post.get('cup_size', '?')}
💰 <b>零花钱</b>: {post.get('pocket_money', '面议')}

🏷 <b>标签</b>: {tag_text}

📅 发布时间: {format_timestamp(post.get('created_at', ''))}
"""

    # VIP提示
    caption += "\n💎 VIP用户可查看验证视频"

    return caption


def format_error_message(error_type: str, **kwargs) -> str:
    """
    格式化错误消息
    """
    messages = {
        'not_found': "❌ 未找到该编号的帖子\n\n💡 请检查编号是否正确",
        'offline': "⚠️ 该帖子已下架",
        'insufficient_credits': f"⚠️ 积分不足\n\n需要: {kwargs.get('required', 0)} 积分\n当前: {kwargs.get('current', 0)} 积分\n\n💡 获取积分方式：\n• 充值VIP（无限使用）\n• 推广好友（每人5积分）",
        'invalid_format': "❌ 搜索格式错误\n\n请使用：\n• 编号搜索：<code>251221123045</code>\n• 条件搜索：<code>城市 标签 身高</code>（空格分隔）\n\n💡 输入 /help 查看详细帮助",
        'unknown_keyword': "⚠️ 无法识别的关键词\n\n已转发客服处理",
        'blacklisted': "🚫 您已被加入黑名单",
        'vip_required': "⚠️ 此功能需要VIP权限\n\n使用 /pay 充值VIP",
    }

    return messages.get(error_type, "❌ 发生错误")


def format_user_info(user: Dict) -> str:
    """
    格式化用户信息（个人中心）
    """
    user_type_emoji = {
        'normal': '👤',
        'vip': '💎',
        'blacklist': '🚫'
    }

    user_type_text = {
        'normal': '普通用户',
        'vip': 'VIP会员',
        'blacklist': '已拉黑'
    }

    emoji = user_type_emoji.get(user['user_type'], '👤')
    type_text = user_type_text.get(user['user_type'], '普通用户')

    msg = f"""
{emoji} <b>个人中心</b>

🆔 用户ID: {format_user_id(user['user_id'])}
👤 用户名: @{user.get('username', '未设置')}
💎 会员类型: {type_text}
💰 余额: {format_amount(user['balance'])} USDT
⭐ 积分: {user['credits']}
📅 注册时间: {format_timestamp(user['created_at'])}
"""

    # VIP过期时间
    if user.get('vip_expires_at'):
        msg += f"⏰ VIP到期: {format_timestamp(user['vip_expires_at'])}\n"

    # 推广信息
    from config.settings import REFERRAL_CREDITS
    referral_link = generate_referral_link(user['user_id'])
    msg += f"\n📊 <b>推广信息</b>\n"
    msg += f"• 已推广人数: {user['referral_count']}\n"
    msg += f"• 我的推广链接:\n"
    msg += f"  <code>{referral_link}</code>\n"
    msg += f"\n💡 分享链接邀请好友，双方各得 {REFERRAL_CREDITS} 积分"

    return msg


def format_admin_user_detail(user: Dict) -> str:
    """
    格式化用户详情（管理员查看）
    """
    msg = f"""
👤 <b>用户详情</b>

🆔 ID: {format_user_id(user['user_id'])}
👤 用户名: @{user.get('username', '未设置')}
💎 类型: {user['user_type']}
💰 余额: {format_amount(user['balance'])} USDT
⭐ 积分: {user['credits']}
📅 注册时间: {format_timestamp(user['created_at'])}

📊 <b>推广数据:</b>
• 推荐人: {user.get('referrer_id', '无')}
• 推广人数: {user['referral_count']}
• 来路: {user.get('referral_source', '直接访问')}
"""

    # VIP信息
    if user.get('vip_expires_at'):
        msg += f"\n⏰ VIP到期: {format_timestamp(user['vip_expires_at'])}"

    # 订单记录
    if user.get('payments'):
        msg += f"\n\n💳 <b>订单记录:</b>"
        for payment in user['payments'][:5]:
            status_emoji = "✅" if payment['status'] == 'completed' else "⏳"
            msg += f"\n{status_emoji} {format_amount(payment['amount_usdt'])}U - {payment['status']}"

    # 订阅信息
    if user.get('subscriptions'):
        msg += f"\n\n📬 订阅数量: {len(user['subscriptions'])}"

    return msg


def format_stats(stats: Dict) -> str:
    """
    格式化统计信息
    """
    total_users = stats['total_users']
    vip_rate = stats['vip_users'] / total_users * 100 if total_users > 0 else 0

    return f"""
📊 <b>用户统计</b>

👥 总用户数: {total_users}
💎 VIP用户: {stats['vip_users']}
🚫 黑名单: {stats['blacklist_users']}
🆕 今日新增: {stats['today_new']}

📈 VIP占比: {vip_rate:.1f}%
"""


def format_detailed_stats(stats: Dict) -> str:
    """
    格式化详细统计信息
    """
    # 计算转化率
    conversion_rate = 0
    if stats['total_clicks'] > 0:
        conversion_rate = stats['total_conversions'] / stats['total_clicks'] * 100

    # VIP占比
    vip_rate = 0
    if stats['total_users'] > 0:
        vip_rate = stats['vip_users'] / stats['total_users'] * 100

    # 订单完成率
    order_completion_rate = 0
    if stats['total_orders'] > 0:
        order_completion_rate = stats['completed_orders'] / stats['total_orders'] * 100

    return f"""
📊 <b>系统全面统计</b>

━━━━━━━━━━━━━━━━━━━━
👥 <b>用户数据</b>
━━━━━━━━━━━━━━━━━━━━

📈 总用户数: <code>{stats['total_users']}</code>
💎 VIP用户: <code>{stats['vip_users']}</code> ({vip_rate:.1f}%)
👤 普通用户: <code>{stats['normal_users']}</code>
🚫 黑名单: <code>{stats['blacklist_users']}</code>

🆕 今日新增: <code>{stats['today_new_users']}</code>
📅 本周新增: <code>{stats['week_new_users']}</code>
📆 本月新增: <code>{stats['month_new_users']}</code>

💰 总余额: <code>{stats['total_balance']:.2f}</code> USDT
⭐ 总积分: <code>{stats['total_credits']}</code>

━━━━━━━━━━━━━━━━━━━━
💳 <b>订单数据</b>
━━━━━━━━━━━━━━━━━━━━

📦 总订单: <code>{stats['total_orders']}</code>
✅ 已完成: <code>{stats['completed_orders']}</code> ({order_completion_rate:.1f}%)
⏳ 待处理: <code>{stats['pending_orders']}</code>

🗓️ 今日订单: <code>{stats['today_orders']}</code>
✅ 今日完成: <code>{stats['today_completed_orders']}</code>

💵 今日收入: <code>{stats['today_income']:.2f}</code> USDT
💰 总收入: <code>{stats['total_income']:.2f}</code> USDT

━━━━━━━━━━━━━━━━━━━━
📬 <b>订阅推送</b>
━━━━━━━━━━━━━━━━━━━━

📋 总订阅: <code>{stats['total_subscriptions']}</code>
✅ 今日已推送: <code>{stats['today_pushed_users']}</code>
⏰ 待推送: <code>{stats['pending_push_users']}</code>

━━━━━━━━━━━━━━━━━━━━
🔗 <b>推广数据</b>
━━━━━━━━━━━━━━━━━━━━

🔗 推广链接: <code>{stats['total_referral_links']}</code>
👆 总点击: <code>{stats['total_clicks']}</code>
✅ 总转化: <code>{stats['total_conversions']}</code>
📊 转化率: <code>{conversion_rate:.1f}%</code>
👥 推荐用户: <code>{stats['referred_users']}</code>

━━━━━━━━━━━━━━━━━━━━
📝 <b>采集数据</b>
━━━━━━━━━━━━━━━━━━━━

📄 总帖子: <code>{stats['total_posts']}</code>
🆕 今日新增: <code>{stats['today_new_posts']}</code>
🏷️ 标签数: <code>{stats['total_tags']}</code>

━━━━━━━━━━━━━━━━━━━━
⏰ 更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""


def format_referral_top(top_list: List[Dict]) -> str:
    """
    格式化来路TOP
    """
    if not top_list:
        return "📊 暂无来路数据"

    msg = "🏆 <b>来路TOP10</b>\n\n"

    for i, item in enumerate(top_list, 1):
        emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        msg += f"{emoji} <code>{item['link_code']}</code>\n"
        msg += f"   点击: {item['click_count']} | 注册: {item['register_count']}\n\n"

    return msg


def format_payment_info(order_id: int, amount: float, wallet_address: str) -> str:
    """
    格式化支付信息
    """
    return f"""
💳 <b>充值VIP</b>

<b>订单信息:</b>
• 订单号: {format_user_id(order_id)}
• 金额: <code>{format_amount(amount)}</code> USDT (TRC20)
• 时长: 30天

<b>收款地址:</b>
<code>{wallet_address}</code>

<b>支付说明:</b>
1️⃣ 请使用TRC20网络转账
2️⃣ 转账金额必须完全匹配: <code>{format_amount(amount)}</code> USDT
3️⃣ 转账后系统自动检测（约5-10分钟）
4️⃣ 到账后自动升级VIP

⚠️ 注意:
• 金额不匹配将无法自动到账
• 24小时内未支付订单将自动取消
• 如有问题请联系客服
"""
