"""
数据库操作函数
提供所有表的增删改查功能
"""
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import sys
import os

# 动态获取配置路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def get_connection(db_path=None):
    """获取数据库连接"""
    if db_path is None:
        from config.settings import USER_DATABASE_PATH
        db_path = USER_DATABASE_PATH
    
    conn = sqlite3.connect(db_path, timeout=30.0)
    conn.row_factory = sqlite3.Row  # 使结果可以按列名访问
    return conn

def _timestamp(dt: datetime = None) -> str:
    return (dt or datetime.now()).isoformat(sep=' ', timespec='seconds')

# ==================== 用户操作 ====================

def create_user(user_id: int, username: str = None, referrer_id: int = None, referral_source: str = None) -> bool:
    """
    创建新用户
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO users (user_id, username, referrer_id, referral_source)
            VALUES (?, ?, ?, ?)
        ''', (user_id, username, referrer_id, referral_source))
        
        # 如果有推荐人，更新推荐人的推广数量
        if referrer_id:
            cursor.execute('''
                UPDATE users SET referral_count = referral_count + 1
                WHERE user_id = ?
            ''', (referrer_id,))
            
            # 双方都增加积分
            cursor.execute('''
                UPDATE users SET credits = credits + ?
                WHERE user_id IN (?, ?)
            ''', (5, user_id, referrer_id))  # 5是推广积分
        
        # 更新来路统计
        if referral_source:
            cursor.execute('''
                INSERT INTO referral_stats (link_code, register_count)
                VALUES (?, 1)
                ON CONFLICT(link_code) DO UPDATE SET
                    register_count = register_count + 1
            ''', (referral_source,))
        
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # 用户已存在
        return False
    finally:
        conn.close()

def get_user(user_id: int) -> Optional[Dict]:
    """
    获取用户信息
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return dict(result)
    return None

def get_user_full_info(user_id: int) -> Optional[Dict]:
    """
    获取用户完整信息（包括订单、订阅、来路）
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. 基本信息
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    
    if not result:
        conn.close()
        return None
    
    user = dict(result)
    
    # 2. 订单历史
    cursor.execute('''
        SELECT * FROM payments 
        WHERE user_id = ? 
        ORDER BY created_at DESC
        LIMIT 10
    ''', (user_id,))
    user['payments'] = [dict(row) for row in cursor.fetchall()]
    
    # 3. 订阅列表
    cursor.execute('''
        SELECT * FROM subscriptions 
        WHERE user_id = ? AND is_active = 1
    ''', (user_id,))
    user['subscriptions'] = [dict(row) for row in cursor.fetchall()]
    
    # 4. 来路信息
    if user.get('referral_source'):
        cursor.execute('''
            SELECT * FROM referral_stats 
            WHERE link_code = ?
        ''', (user['referral_source'],))
        ref_result = cursor.fetchone()
        if ref_result:
            user['referral_info'] = dict(ref_result)
    
    conn.close()
    return user

def update_user_type(user_id: int, user_type: str) -> bool:
    """
    更新用户类型（normal/vip/blacklist）
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE users SET user_type = ?
        WHERE user_id = ?
    ''', (user_type, user_id))
    
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    
    return success

def update_user_balance(user_id: int, amount: float) -> bool:
    """
    更新用户余额（正数增加，负数减少）
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE users SET balance = balance + ?
        WHERE user_id = ?
    ''', (amount, user_id))
    
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    
    return success

def update_user_credits(user_id: int, amount: int) -> bool:
    """
    更新用户积分（正数增加，负数减少）
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE users SET credits = credits + ?
        WHERE user_id = ?
    ''', (amount, user_id))
    
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    
    return success

def set_vip_expires(user_id: int, days: int) -> bool:
    """
    设置VIP过期时间
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    expires_at = _timestamp(datetime.now() + timedelta(days=days))
    
    cursor.execute('''
        UPDATE users SET 
            user_type = 'vip',
            vip_expires_at = ?
        WHERE user_id = ?
    ''', (expires_at, user_id))
    
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    
    return success

def check_and_expire_vip():
    """
    检查并过期VIP用户
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    now = _timestamp()
    
    cursor.execute('''
        UPDATE users SET user_type = 'normal'
        WHERE user_type = 'vip' 
        AND vip_expires_at IS NOT NULL 
        AND vip_expires_at < ?
    ''', (now,))
    
    expired_count = cursor.rowcount
    conn.commit()
    conn.close()
    
    return expired_count

# ==================== 支付订单操作 ====================

def create_payment(user_id: int, amount_usdt: float, verification_amount: float, wallet_address: str) -> int:
    """
    创建支付订单
    返回订单ID
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        from config.settings import PAYMENT_TIMEOUT_MINUTES
        expired_at = _timestamp(datetime.now() + timedelta(minutes=PAYMENT_TIMEOUT_MINUTES))
    except Exception:
        expired_at = None
    
    cursor.execute('''
        INSERT INTO payments (user_id, amount_usdt, verification_amount, wallet_address, expired_at)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, amount_usdt, verification_amount, wallet_address, expired_at))
    
    payment_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return payment_id

def complete_payment(payment_id: int) -> bool:
    """
    完成支付订单
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    now = _timestamp()
    
    cursor.execute('''
        UPDATE payments SET 
            status = 'completed',
            completed_at = ?
        WHERE id = ? AND status = 'pending'
    ''', (now, payment_id))
    
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    
    return success

def complete_payment_with_tx(payment_id: int, tx_id: str, payer_address: str = None) -> bool:
    """
    完成支付订单，并绑定链上交易 ID。
    同一个 tx_id 只能成功核销一次。
    """
    if not tx_id:
        return False

    conn = get_connection()
    cursor = conn.cursor()
    now = _timestamp()

    try:
        cursor.execute('BEGIN IMMEDIATE')
        cursor.execute('''
            UPDATE payments SET
                status = 'completed',
                completed_at = ?,
                tx_id = ?,
                payer_address = ?
            WHERE id = ?
              AND status = 'pending'
              AND (expired_at IS NULL OR datetime(expired_at) > datetime(?))
              AND NOT EXISTS (
                  SELECT 1 FROM payments
                  WHERE tx_id = ? AND id != ?
              )
        ''', (now, tx_id, payer_address, payment_id, now, tx_id, payment_id))

        success = cursor.rowcount > 0
        conn.commit()
        return success
    except sqlite3.IntegrityError:
        conn.rollback()
        return False
    finally:
        conn.close()

def expire_payment(payment_id: int) -> bool:
    """
    将待支付订单标记为已过期。
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE payments SET status = 'expired'
        WHERE id = ? AND status = 'pending'
    ''', (payment_id,))

    success = cursor.rowcount > 0
    conn.commit()
    conn.close()

    return success

def expire_user_pending_payments(user_id: int) -> int:
    """
    将用户现有的待支付订单全部标记为已过期。
    返回实际更新的订单数量。
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE payments SET status = 'expired'
        WHERE user_id = ? AND status = 'pending'
    ''', (user_id,))

    expired_count = cursor.rowcount
    conn.commit()
    conn.close()

    return expired_count

def get_pending_payments(user_id: int = None) -> List[Dict]:
    """
    获取待处理订单
    如果指定user_id，则只获取该用户的订单
    否则获取所有待处理订单
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    now = _timestamp()

    if user_id:
        cursor.execute('''
            SELECT * FROM payments 
            WHERE user_id = ? AND status = 'pending'
            AND (expired_at IS NULL OR datetime(expired_at) > datetime(?))
            ORDER BY created_at DESC
        ''', (user_id, now))
    else:
        # 获取所有待处理订单（用于定时检测）
        cursor.execute('''
            SELECT * FROM payments 
            WHERE status = 'pending'
            AND (expired_at IS NULL OR datetime(expired_at) > datetime(?))
            ORDER BY created_at DESC
        ''', (now,))
    
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return results

def get_completed_payment_count(user_id: int) -> int:
    """
    获取用户已完成订单数量。
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT COUNT(*) as count
        FROM payments
        WHERE user_id = ? AND status = 'completed'
    ''', (user_id,))

    count = cursor.fetchone()['count']
    conn.close()

    return count

# ==================== 订阅操作 ====================

def create_subscription(user_id: int, sub_data: Dict) -> int:
    """
    创建订阅
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO subscriptions (
            user_id, city, age_min, age_max, 
            height_min, height_max, weight_min, weight_max, tags, time_slot
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        user_id,
        sub_data.get('city'),
        sub_data.get('age_min'),
        sub_data.get('age_max'),
        sub_data.get('height_min'),
        sub_data.get('height_max'),
        sub_data.get('weight_min'),
        sub_data.get('weight_max'),
        ','.join(sub_data.get('tags', [])),
        sub_data.get('time_slot', 'hourly')
    ))
    
    sub_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return sub_id

def get_user_subscriptions(user_id: int) -> List[Dict]:
    """
    获取用户订阅列表
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM subscriptions 
        WHERE user_id = ? AND is_active = 1
    ''', (user_id,))
    
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return results

def delete_subscription(sub_id: int) -> bool:
    """
    删除订阅
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE subscriptions SET is_active = 0
        WHERE id = ?
    ''', (sub_id,))
    
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    
    return success

def get_all_active_subscriptions() -> List[Dict]:
    """
    获取所有活跃订阅（用于推送任务）
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT s.*, u.user_id, u.username
        FROM subscriptions s
        JOIN users u ON s.user_id = u.user_id
        WHERE s.is_active = 1 AND u.user_type != 'blacklist'
    ''')
    
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return results

# ==================== 来路统计操作 ====================

def track_referral_click(link_code: str):
    """
    记录来路点击
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO referral_stats (link_code, click_count)
        VALUES (?, 1)
        ON CONFLICT(link_code) DO UPDATE SET
            click_count = click_count + 1
    ''', (link_code,))
    
    conn.commit()
    conn.close()

def get_referral_top(limit: int = 10) -> List[Dict]:
    """
    获取来路TOP
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM referral_stats 
        ORDER BY register_count DESC, click_count DESC
        LIMIT ?
    ''', (limit,))
    
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return results

# ==================== 统计操作 ====================

def get_user_stats() -> Dict:
    """
    获取用户统计
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # 总用户数
    cursor.execute('SELECT COUNT(*) as count FROM users')
    total_users = cursor.fetchone()['count']
    
    # VIP用户数
    cursor.execute('SELECT COUNT(*) as count FROM users WHERE user_type = "vip"')
    vip_users = cursor.fetchone()['count']
    
    # 黑名单用户数
    cursor.execute('SELECT COUNT(*) as count FROM users WHERE user_type = "blacklist"')
    blacklist_users = cursor.fetchone()['count']
    
    # 今日新增
    cursor.execute('''
        SELECT COUNT(*) as count FROM users 
        WHERE DATE(created_at) = DATE('now')
    ''')
    today_new = cursor.fetchone()['count']
    
    conn.close()
    
    return {
        'total_users': total_users,
        'vip_users': vip_users,
        'blacklist_users': blacklist_users,
        'today_new': today_new
    }

def get_all_user_ids(user_type: str = None) -> List[int]:
    """
    获取所有用户ID（用于推送）
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    if user_type:
        cursor.execute('SELECT user_id FROM users WHERE user_type = ?', (user_type,))
    else:
        cursor.execute('SELECT user_id FROM users WHERE user_type != "blacklist"')
    
    results = [row['user_id'] for row in cursor.fetchall()]
    conn.close()
    
    return results

# ==================== 订阅推送相关操作 ====================

def mark_user_pushed(user_id: int):
    """
    标记用户最近一次订阅推送时间
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    pushed_at = datetime.now().isoformat(sep=' ', timespec='seconds')
    cursor.execute('''
        UPDATE users
        SET last_subscription_push = ?
        WHERE user_id = ?
    ''', (pushed_at, user_id))
    
    conn.commit()
    conn.close()

def get_users_need_push_this_hour() -> List[int]:
    """
    获取本小时需要检查订阅推送的用户ID列表。
    返回有活跃订阅、未被拉黑、且本小时还没推送过的用户。
    """
    conn = get_connection()
    cursor = conn.cursor()

    hour_start = datetime.now().replace(minute=0, second=0, microsecond=0)
    hour_start_text = hour_start.isoformat(sep=' ', timespec='seconds')

    cursor.execute('''
        SELECT DISTINCT s.user_id
        FROM subscriptions s
        LEFT JOIN users u ON s.user_id = u.user_id
        WHERE s.is_active = 1
        AND u.user_type != 'blacklist'
        AND (u.last_subscription_push IS NULL OR datetime(u.last_subscription_push) < ?)
        ORDER BY RANDOM()
    ''', (hour_start_text,))
    
    user_ids = [row['user_id'] for row in cursor.fetchall()]
    conn.close()
    
    return user_ids

def get_users_need_push_today(_legacy_slot: str = None) -> List[int]:
    """
    兼容旧调用：现在订阅推送按小时执行，不再按日期或时间段过滤。
    """
    return get_users_need_push_this_hour()

def get_subscription_count(user_id: int) -> int:
    """
    获取用户的订阅数量
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT COUNT(*) as count FROM subscriptions
        WHERE user_id = ? AND is_active = 1
    ''', (user_id,))
    
    count = cursor.fetchone()['count']
    conn.close()
    
    return count

def delete_all_subscriptions(user_id: int) -> int:
    """
    删除用户所有订阅
    返回删除的数量
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE subscriptions SET is_active = 0
        WHERE user_id = ? AND is_active = 1
    ''', (user_id,))
    
    deleted_count = cursor.rowcount
    conn.commit()
    conn.close()
    
    return deleted_count

# ==================== 详细统计功能 ====================

def get_detailed_stats() -> Dict:
    """
    获取详细统计数据
    包括用户、VIP、订单、订阅、采集bot数据等
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    stats = {}
    
    # ========== 用户统计 ==========
    # 总用户数
    cursor.execute('SELECT COUNT(*) as count FROM users')
    stats['total_users'] = cursor.fetchone()['count']
    
    # VIP用户数
    cursor.execute('SELECT COUNT(*) as count FROM users WHERE user_type = "vip"')
    stats['vip_users'] = cursor.fetchone()['count']
    
    # 普通用户数
    cursor.execute('SELECT COUNT(*) as count FROM users WHERE user_type = "normal"')
    stats['normal_users'] = cursor.fetchone()['count']
    
    # 黑名单用户数
    cursor.execute('SELECT COUNT(*) as count FROM users WHERE user_type = "blacklist"')
    stats['blacklist_users'] = cursor.fetchone()['count']
    
    # 今日新增用户
    cursor.execute('''
        SELECT COUNT(*) as count FROM users 
        WHERE DATE(created_at) = DATE('now')
    ''')
    stats['today_new_users'] = cursor.fetchone()['count']
    
    # 本周新增用户
    cursor.execute('''
        SELECT COUNT(*) as count FROM users 
        WHERE DATE(created_at) >= DATE('now', '-7 days')
    ''')
    stats['week_new_users'] = cursor.fetchone()['count']
    
    # 本月新增用户
    cursor.execute('''
        SELECT COUNT(*) as count FROM users 
        WHERE DATE(created_at) >= DATE('now', 'start of month')
    ''')
    stats['month_new_users'] = cursor.fetchone()['count']
    
    # 总余额
    cursor.execute('SELECT SUM(balance) as total FROM users')
    result = cursor.fetchone()
    stats['total_balance'] = result['total'] if result['total'] else 0
    
    # 总积分
    cursor.execute('SELECT SUM(credits) as total FROM users')
    result = cursor.fetchone()
    stats['total_credits'] = result['total'] if result['total'] else 0
    
    # ========== 订单统计 ==========
    # 总订单数
    cursor.execute('SELECT COUNT(*) as count FROM payments')
    stats['total_orders'] = cursor.fetchone()['count']
    
    # 已完成订单
    cursor.execute('SELECT COUNT(*) as count FROM payments WHERE status = "completed"')
    stats['completed_orders'] = cursor.fetchone()['count']
    
    # 待处理订单
    cursor.execute('SELECT COUNT(*) as count FROM payments WHERE status = "pending"')
    stats['pending_orders'] = cursor.fetchone()['count']
    
    # 今日订单
    cursor.execute('''
        SELECT COUNT(*) as count FROM payments 
        WHERE DATE(created_at) = DATE('now')
    ''')
    stats['today_orders'] = cursor.fetchone()['count']
    
    # 今日完成订单
    cursor.execute('''
        SELECT COUNT(*) as count FROM payments 
        WHERE status = "completed" AND DATE(completed_at) = DATE('now')
    ''')
    stats['today_completed_orders'] = cursor.fetchone()['count']
    
    # 今日收入（已完成订单）
    cursor.execute('''
        SELECT SUM(amount_usdt) as total FROM payments 
        WHERE status = "completed" AND DATE(completed_at) = DATE('now')
    ''')
    result = cursor.fetchone()
    stats['today_income'] = result['total'] if result['total'] else 0
    
    # 总收入
    cursor.execute('''
        SELECT SUM(amount_usdt) as total FROM payments 
        WHERE status = "completed"
    ''')
    result = cursor.fetchone()
    stats['total_income'] = result['total'] if result['total'] else 0
    
    # ========== 订阅统计 ==========
    # 总订阅数
    cursor.execute('SELECT COUNT(*) as count FROM subscriptions WHERE is_active = 1')
    stats['total_subscriptions'] = cursor.fetchone()['count']
    
    # 今日推送用户数（已推送的）
    cursor.execute('''
        SELECT COUNT(*) as count FROM users 
        WHERE DATE(last_subscription_push) = DATE('now')
    ''')
    stats['today_pushed_users'] = cursor.fetchone()['count']
    
    # 待推送用户数（有订阅但本小时还没推送）
    hour_start = datetime.now().replace(minute=0, second=0, microsecond=0)
    hour_start_text = hour_start.isoformat(sep=' ', timespec='seconds')
    cursor.execute('''
        SELECT COUNT(DISTINCT s.user_id) as count
        FROM subscriptions s
        LEFT JOIN users u ON s.user_id = u.user_id
        WHERE s.is_active = 1 
        AND u.user_type != 'blacklist'
        AND (u.last_subscription_push IS NULL OR datetime(u.last_subscription_push) < ?)
    ''', (hour_start_text,))
    stats['pending_push_users'] = cursor.fetchone()['count']
    
    # ========== 推广统计 ==========
    # 总推广链接数
    cursor.execute('SELECT COUNT(*) as count FROM referral_stats')
    stats['total_referral_links'] = cursor.fetchone()['count']
    
    # 总点击数
    cursor.execute('SELECT SUM(click_count) as total FROM referral_stats')
    result = cursor.fetchone()
    stats['total_clicks'] = result['total'] if result['total'] else 0
    
    # 总注册转化数
    cursor.execute('SELECT SUM(register_count) as total FROM referral_stats')
    result = cursor.fetchone()
    stats['total_conversions'] = result['total'] if result['total'] else 0
    
    # 通过推荐注册的用户数
    cursor.execute('SELECT COUNT(*) as count FROM users WHERE referrer_id IS NOT NULL')
    stats['referred_users'] = cursor.fetchone()['count']
    
    conn.close()
    
    # ========== 采集bot统计（只读） ==========
    try:
        from services.post_fetcher import get_collector_connection
        
        collector_conn = get_collector_connection()
        collector_cursor = collector_conn.cursor()
        
        # 总帖子数
        collector_cursor.execute('SELECT COUNT(*) as count FROM posts WHERE status = "normal"')
        stats['total_posts'] = collector_cursor.fetchone()['count']
        
        # 今日新增帖子
        collector_cursor.execute('''
            SELECT COUNT(*) as count FROM posts 
            WHERE DATE(created_at) = DATE('now') AND status = "normal"
        ''')
        stats['today_new_posts'] = collector_cursor.fetchone()['count']
        
        # 总标签数
        collector_cursor.execute('SELECT COUNT(*) as count FROM tags')
        stats['total_tags'] = collector_cursor.fetchone()['count']
        
        collector_conn.close()
    except Exception as e:
        print(f"获取采集bot统计失败: {e}")
        stats['total_posts'] = 0
        stats['today_new_posts'] = 0
        stats['total_tags'] = 0
    
    return stats

if __name__ == '__main__':
    # 测试
    print("数据库操作函数加载完成！")
    
# 为兼容性添加别名
def get_user_by_id(user_id: int) -> Optional[Dict]:
    """
    获取用户信息（别名）
    """
    return get_user(user_id)
