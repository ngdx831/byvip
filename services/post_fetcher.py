"""
采集Bot数据读取服务
从采集bot的post.db读取帖子数据
"""
import sqlite3
from typing import Optional, List, Dict
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import COLLECTOR_DATABASE_PATH, HEIGHT_TOLERANCE, WEIGHT_TOLERANCE, AGE_TOLERANCE

def get_collector_connection():
    """获取采集bot数据库连接（只读）"""
    conn = sqlite3.connect(
        f'file:{COLLECTOR_DATABASE_PATH}?mode=ro',
        uri=True,
        timeout=30.0
    )
    conn.row_factory = sqlite3.Row
    return conn

def get_post_by_number(post_number: str) -> Optional[Dict]:
    """
    根据编号获取帖子
    """
    conn = get_collector_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM posts 
        WHERE post_number = ?
    ''', (post_number,))
    
    result = cursor.fetchone()
    
    if not result:
        conn.close()
        return None
    
    post = dict(result)
    
    # 获取标签
    cursor.execute('''
        SELECT t.name 
        FROM tags t
        JOIN post_tags pt ON t.id = pt.tag_id
        WHERE pt.post_id = ?
    ''', (post['id'],))
    
    post['tags'] = [row['name'] for row in cursor.fetchall()]
    
    conn.close()
    return post

def get_post_media(post_id: int) -> List[Dict]:
    """
    获取帖子的所有媒体文件
    """
    conn = get_collector_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM media 
        WHERE post_id = ?
        ORDER BY id
    ''', (post_id,))
    
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return results

def search_posts(filters: Dict, limit: int = 50) -> List[Dict]:
    """
    条件搜索帖子
    
    filters = {
        'city': '成都',
        'province': '四川',
        'tags': ['学生', '良家'],
        'age': 20,
        'height': 165,
        'weight': 50,
        'cup_size': 'C',
        'pocket_money_range': '一万以下'  # 一万以下/一到三万/三万以上
    }
    """
    conn = get_collector_connection()
    cursor = conn.cursor()
    
    # 构建SQL查询
    where_clauses = ["status = 'normal'"]
    params = []
    
    # 城市（支持多城市逗号分隔，如"成都,绵阳,重庆"）
    if filters.get('city'):
        where_clauses.append("city LIKE ?")
        params.append(f"%{filters['city']}%")
    
    # 省份（支持多省份逗号分隔，如"四川,重庆"）
    if filters.get('province'):
        where_clauses.append("province LIKE ?")
        params.append(f"%{filters['province']}%")
    
    # 年龄（±浮动）
    if filters.get('age'):
        age = filters['age']
        where_clauses.append(f"age BETWEEN ? AND ?")
        params.extend([age - AGE_TOLERANCE, age + AGE_TOLERANCE])
    
    # 身高（±浮动）
    if filters.get('height'):
        height = filters['height']
        where_clauses.append(f"height BETWEEN ? AND ?")
        params.extend([height - HEIGHT_TOLERANCE, height + HEIGHT_TOLERANCE])
    
    # 体重（±浮动）
    if filters.get('weight'):
        weight = filters['weight']
        where_clauses.append(f"weight BETWEEN ? AND ?")
        params.extend([weight - WEIGHT_TOLERANCE, weight + WEIGHT_TOLERANCE])
    
    # 杯罩
    if filters.get('cup_size'):
        where_clauses.append("cup_size = ?")
        params.append(filters['cup_size'])
    
    # 零花钱范围
    if filters.get('pocket_money_range'):
        pm_range = filters['pocket_money_range']
        if pm_range == '一万以下':
            where_clauses.append("CAST(pocket_money AS INTEGER) < 10000")
        elif pm_range == '一到三万':
            where_clauses.append("CAST(pocket_money AS INTEGER) BETWEEN 10000 AND 30000")
        elif pm_range == '三万以上':
            where_clauses.append("CAST(pocket_money AS INTEGER) > 30000")
    
    # 基础查询
    base_query = f'''
        SELECT DISTINCT p.*
        FROM posts p
        WHERE {" AND ".join(where_clauses)}
    '''
    
    # 如果有标签筛选
    if filters.get('tags') and len(filters['tags']) > 0:
        # 使用子查询匹配标签
        tag_conditions = []
        for tag in filters['tags']:
            tag_conditions.append(f"t.name = ?")
            params.append(tag)
        
        query = f'''
            {base_query}
            AND p.id IN (
                SELECT pt.post_id 
                FROM post_tags pt
                JOIN tags t ON pt.tag_id = t.id
                WHERE {" OR ".join(tag_conditions)}
            )
            ORDER BY p.created_at DESC
            LIMIT ?
        '''
    else:
        query = f'''
            {base_query}
            ORDER BY p.created_at DESC
            LIMIT ?
        '''
    
    params.append(limit)
    
    cursor.execute(query, params)
    results = []
    
    for row in cursor.fetchall():
        post = dict(row)
        
        # 获取标签
        cursor.execute('''
            SELECT t.name 
            FROM tags t
            JOIN post_tags pt ON t.id = pt.tag_id
            WHERE pt.post_id = ?
        ''', (post['id'],))
        
        post['tags'] = [tag_row['name'] for tag_row in cursor.fetchall()]
        results.append(post)
    
    conn.close()
    return results

def get_recent_posts_for_subscription(sub_data: Dict, hours: int = 1) -> List[Dict]:
    """
    为订阅推送获取最近的帖子（真正按 city/province/范围/tags 过滤）
    """
    conn = get_collector_connection()
    cursor = conn.cursor()

    provinces = {
        "广东", "浙江", "江苏", "山东", "河南", "四川", "湖北", "湖南", "河北", "福建",
        "安徽", "辽宁", "陕西", "江西", "山西", "黑龙江", "吉林", "云南", "贵州", "广西",
        "海南", "甘肃", "青海", "宁夏", "新疆", "内蒙古", "西藏",
        "北京", "上海", "天津", "重庆",
    }

    # tags: DB里是逗号分隔字符串
    tag_list = []
    if sub_data.get("tags"):
        tag_list = [t.strip() for t in str(sub_data["tags"]).split(",") if t.strip()]

    # city: 允许“成都,重庆”这种（逗号/中文逗号）
    city_raw = (sub_data.get("city") or "").strip()
    city_list = []
    if city_raw:
        city_list = [c.strip() for c in city_raw.replace("，", ",").split(",") if c.strip()]

    where_clauses = [
        "p.status = 'normal'",
        "datetime(p.created_at) >= datetime('now', '-' || ? || ' hours')",
    ]
    params = [hours]

    # 城市/省份（订阅表只有 city 字段，这里兼容：如果填的是省份就匹配 province）
    if city_list:
        sub_city_conditions = []
        for c in city_list:
            if c in provinces:
                sub_city_conditions.append("p.province LIKE ?")
                params.append(f"%{c}%")
            else:
                sub_city_conditions.append("p.city LIKE ?")
                params.append(f"%{c}%")
        where_clauses.append("(" + " OR ".join(sub_city_conditions) + ")")

    # 年龄范围
    if sub_data.get("age_min") is not None and sub_data.get("age_max") is not None:
        where_clauses.append("p.age BETWEEN ? AND ?")
        params.extend([sub_data["age_min"], sub_data["age_max"]])

    # 身高范围
    if sub_data.get("height_min") is not None and sub_data.get("height_max") is not None:
        where_clauses.append("p.height BETWEEN ? AND ?")
        params.extend([sub_data["height_min"], sub_data["height_max"]])

    # 体重范围
    if sub_data.get("weight_min") is not None and sub_data.get("weight_max") is not None:
        where_clauses.append("p.weight BETWEEN ? AND ?")
        params.extend([sub_data["weight_min"], sub_data["weight_max"]])

    base_query = f"""
        SELECT DISTINCT p.*
        FROM posts p
        WHERE {" AND ".join(where_clauses)}
    """

    # ✅ 标签过滤（和 search_posts 一样：命中任一 tag 即可）
    if tag_list:
        placeholders = ",".join(["?"] * len(tag_list))
        query = f"""
            {base_query}
            AND p.id IN (
                SELECT pt.post_id
                FROM post_tags pt
                JOIN tags t ON pt.tag_id = t.id
                WHERE t.name IN ({placeholders})
            )
            ORDER BY p.created_at DESC
            LIMIT 10
        """
        params.extend(tag_list)
    else:
        query = f"""
            {base_query}
            ORDER BY p.created_at DESC
            LIMIT 10
        """

    cursor.execute(query, params)

    results = []
    for row in cursor.fetchall():
        post = dict(row)
        cursor.execute(
            """
            SELECT t.name
            FROM tags t
            JOIN post_tags pt ON t.id = pt.tag_id
            WHERE pt.post_id = ?
            """,
            (post["id"],),
        )
        post["tags"] = [tag_row["name"] for tag_row in cursor.fetchall()]
        results.append(post)

    conn.close()
    return results


if __name__ == '__main__':
    # 测试
    print("=== 测试编号查询 ===")
    # post = get_post_by_number('251221123045')
    # if post:
    #     print(f"找到帖子: {post['post_number']}")
    # else:
    #     print("未找到帖子")
    
    print("\n=== 测试条件搜索 ===")
    results = search_posts({
        'city': '成都',
        'tags': ['学生']
    }, limit=5)
    print(f"找到 {len(results)} 条结果")
