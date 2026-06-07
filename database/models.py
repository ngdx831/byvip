"""
会员Bot数据库模型
定义所有表结构（用户、支付、订阅、来路统计、话题映射）
"""
import sqlite3
from datetime import datetime
import os


def _ensure_column(cursor, table_name: str, column_name: str, column_definition: str):
    """Add a column for existing SQLite databases when it is missing."""
    cursor.execute(f"PRAGMA table_info({table_name})")
    existing_columns = {row[1] for row in cursor.fetchall()}
    if column_name not in existing_columns:
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}")

def init_database(db_path):
    """
    初始化数据库，创建所有表
    """
    # 确保目录存在
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # ========== 表1: users - 用户表 ==========
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            username TEXT,
            user_type TEXT DEFAULT 'normal',
            balance REAL DEFAULT 0.0,
            credits INTEGER DEFAULT 5,
            referrer_id INTEGER,
            referral_count INTEGER DEFAULT 0,
            referral_source TEXT,
            vip_expires_at TIMESTAMP,
            last_subscription_push TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (referrer_id) REFERENCES users(user_id)
        )
    ''')
    
    # ========== 表2: payments - 支付订单表 ==========
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount_usdt REAL NOT NULL,
            verification_amount REAL NOT NULL,
            status TEXT DEFAULT 'pending',
            wallet_address TEXT,
            tx_id TEXT,
            payer_address TEXT,
            expired_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    ''')

    _ensure_column(cursor, 'payments', 'tx_id', 'TEXT')
    _ensure_column(cursor, 'payments', 'payer_address', 'TEXT')
    _ensure_column(cursor, 'payments', 'expired_at', 'TIMESTAMP')
    
    # ========== 表3: subscriptions - 订阅表 ==========
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            city TEXT,
            age_min INTEGER,
            age_max INTEGER,
            height_min INTEGER,
            height_max INTEGER,
            weight_min INTEGER,
            weight_max INTEGER,
            tags TEXT,
            time_slot TEXT DEFAULT 'hourly',
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    ''')
    
    # ========== 表4: referral_stats - 来路统计表 ==========
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS referral_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            link_code TEXT UNIQUE NOT NULL,
            click_count INTEGER DEFAULT 0,
            register_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # ========== 表5: user_topics - 用户话题映射表 ==========
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_topics (
            user_id INTEGER PRIMARY KEY,
            topic_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    ''')
    
    # ========== 创建索引 ==========
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id)
    ''')
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_users_type ON users(user_type)
    ''')
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_payments_user_id ON payments(user_id)
    ''')
    cursor.execute('''
        CREATE UNIQUE INDEX IF NOT EXISTS idx_payments_tx_id ON payments(tx_id)
        WHERE tx_id IS NOT NULL
    ''')
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_payments_status_expired ON payments(status, expired_at)
    ''')
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_subscriptions_user_id ON subscriptions(user_id)
    ''')
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_user_topics_topic_id ON user_topics(topic_id)
    ''')
    
    conn.commit()
    conn.close()
    
    print(f"Database initialized: {db_path}")

if __name__ == '__main__':
    # 测试
    test_db = "./users.db"
    init_database(test_db)
    print("Database created successfully.")
