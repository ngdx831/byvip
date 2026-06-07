"""
城市和标签映射服务 - 修复版
支持容错匹配、不区分大小写、单位处理
"""
import json
import os
import re

# 加载映射表
MAPPING_FILE = os.path.join(os.path.dirname(__file__), '..', 'config', 'city_tag_mapping.json')

with open(MAPPING_FILE, 'r', encoding='utf-8') as f:
    MAPPING_DATA = json.load(f)

CITIES = MAPPING_DATA['cities']
TAGS = MAPPING_DATA['tags']
TAG_VARIANTS = MAPPING_DATA['tag_variants']

# 反向映射（拼音 -> 中文）
PINYIN_TO_CITY = {v: k for k, v in CITIES.items()}
PINYIN_TO_TAG = {v: k for k, v in TAGS.items()}

# 创建小写映射以支持不区分大小写
TAGS_LOWER = {k.lower(): k for k in TAGS.keys()}
TAG_VARIANTS_LOWER = {}
for main_tag, variants in TAG_VARIANTS.items():
    for variant in variants:
        TAG_VARIANTS_LOWER[variant.lower()] = main_tag

def city_to_pinyin(city: str) -> str:
    """
    城市转拼音
    """
    return CITIES.get(city)

def tag_to_pinyin(tag: str) -> str:
    """
    标签转拼音
    """
    return TAGS.get(tag)

def pinyin_to_city(pinyin: str) -> str:
    """
    拼音转城市
    """
    return PINYIN_TO_CITY.get(pinyin)

def pinyin_to_tag(pinyin: str) -> str:
    """
    拼音转标签
    """
    return PINYIN_TO_TAG.get(pinyin)

def match_city_with_variants(text: str) -> str:
    """
    匹配城市（含省份，直接匹配）
    """
    # 直接匹配
    if text in CITIES:
        return text
    
    # 尝试匹配省份（如"广东"）
    provinces = ["广东", "浙江", "江苏", "山东", "河南", "四川", "湖北", 
                "湖南", "河北", "福建", "安徽", "辽宁", "陕西", "江西",
                "山西", "黑龙江", "吉林", "云南", "贵州", "广西", "海南",
                "甘肃", "青海", "宁夏", "新疆", "内蒙古", "西藏",
                "北京", "上海", "天津", "重庆"]
    
    if text in provinces:
        return text
    
    return None

def match_tag_with_variants(text: str) -> str:
    """
    匹配标签（支持容错，不区分大小写）
    """
    # 转换为小写进行匹配
    text_lower = text.lower()
    
    # 先直接匹配（小写）
    if text_lower in TAGS_LOWER:
        return TAGS_LOWER[text_lower]
    
    # 容错匹配（小写）
    if text_lower in TAG_VARIANTS_LOWER:
        return TAG_VARIANTS_LOWER[text_lower]
    
    return None

def parse_number_with_unit(text: str) -> tuple:
    """
    解析带单位的数字
    返回: (类型, 数值) 或 None
    
    类型包括:
    - 'age': 年龄（岁）
    - 'height': 身高（cm或m）
    - 'weight': 体重（kg、公斤、斤）
    
    示例:
    - "18岁" -> ('age', 18)
    - "165cm" -> ('height', 165)
    - "1.65m" -> ('height', 165)
    - "50kg" -> ('weight', 100)  # 转换为斤
    - "50公斤" -> ('weight', 100)
    - "100斤" -> ('weight', 100)
    """
    text = text.strip()
    
    # 年龄: 18岁、20岁
    age_match = re.match(r'^(\d+)岁$', text)
    if age_match:
        age = int(age_match.group(1))
        if 15 <= age <= 35:
            return ('age', age)
    
    # 身高(cm): 165cm、170cm
    height_cm_match = re.match(r'^(\d+)cm$', text, re.IGNORECASE)
    if height_cm_match:
        height = int(height_cm_match.group(1))
        if 145 <= height <= 195:
            return ('height', height)
    
    # 身高(m): 1.65m、1.70m
    height_m_match = re.match(r'^(\d+\.?\d*)m$', text, re.IGNORECASE)
    if height_m_match:
        height_m = float(height_m_match.group(1))
        height = int(height_m * 100)
        if 145 <= height <= 195:
            return ('height', height)
    
    # 体重(kg/公斤): 50kg、50公斤
    weight_kg_match = re.match(r'^(\d+)(kg|公斤)$', text, re.IGNORECASE)
    if weight_kg_match:
        weight_kg = int(weight_kg_match.group(1))
        weight_jin = weight_kg * 2  # 转换为斤
        if 36 <= weight_jin <= 140:
            return ('weight', weight_jin)
    
    # 体重(斤): 100斤
    weight_jin_match = re.match(r'^(\d+)斤$', text)
    if weight_jin_match:
        weight = int(weight_jin_match.group(1))
        if 36 <= weight <= 140:
            return ('weight', weight)
    
    return None

def generate_search_link(city: str = None, tags: list = None) -> str:
    """
    生成搜索链接
    http://t.me/sugervip_bot?start=search{city}_{tag1}_{tag2}
    """
    from config.settings import BOT_USERNAME
    
    link_parts = ["search"]
    
    if city:
        pinyin = city_to_pinyin(city)
        if not pinyin and city:  # 省份没有拼音映射，直接用中文
            pinyin = city
        if pinyin:
            link_parts.append(pinyin)
    
    if tags:
        for tag in tags:
            pinyin = tag_to_pinyin(tag)
            if pinyin:
                link_parts.append(pinyin)
    
    search_param = "_".join(link_parts)
    return f"http://t.me/{BOT_USERNAME}?start={search_param}"

def parse_search_link(start_param: str) -> dict:
    """
    解析搜索链接参数
    支持两种格式:
    1. search{city}_{tag1}_{tag2} - 搜索条件
    2. 纯数字（9位或12位） - 编号搜索
    
    返回: 
    - 搜索条件: {'type': 'search', 'city': '成都', 'tags': ['学生', '良家']}
    - 编号: {'type': 'number', 'post_number': '251200011'}
    """
    # 检查是否是纯数字（编号）
    if start_param.isdigit():
        length = len(start_param)
        if length == 9 or length == 12:
            return {'type': 'number', 'post_number': start_param}
    
    # 检查是否是搜索链接
    if not start_param.startswith('search'):
        return None
    
    # 移除 "search" 前缀
    search_str = start_param[6:]  # 'search' 有6个字符
    
    if not search_str:
        return {'type': 'search', 'city': None, 'tags': []}
    
    # 分割参数
    parts = search_str.split('_')
    
    result = {'type': 'search', 'city': None, 'tags': []}
    
    for part in parts:
        # 尝试匹配城市
        city = pinyin_to_city(part)
        if city:
            result['city'] = city
            continue
        
        # 尝试匹配标签
        tag = pinyin_to_tag(part)
        if tag:
            result['tags'].append(tag)
    
    return result

def is_valid_city(text: str) -> bool:
    """检查是否是有效城市"""
    return match_city_with_variants(text) is not None

def is_valid_tag(text: str) -> bool:
    """检查是否是有效标签"""
    return match_tag_with_variants(text) is not None

def get_all_cities() -> list:
    """获取所有城市列表"""
    return list(CITIES.keys())

def get_all_tags() -> list:
    """获取所有标签列表"""
    return list(TAGS.keys())

if __name__ == '__main__':
    # 测试
    print("=== 城市匹配测试 ===")
    print(f"成都 -> {match_city_with_variants('成都')}")
    print(f"广东 -> {match_city_with_variants('广东')}")
    
    print("\n=== 标签匹配测试（不区分大小写）===")
    print(f"学生 -> {match_tag_with_variants('学生')}")
    print(f"学妹 -> {match_tag_with_variants('学妹')}")
    print(f"SM -> {match_tag_with_variants('SM')}")
    print(f"sm -> {match_tag_with_variants('sm')}")
    print(f"外省 -> {match_tag_with_variants('外省')}")
    
    print("\n=== 单位解析测试 ===")
    print(f"18岁 -> {parse_number_with_unit('18岁')}")
    print(f"165cm -> {parse_number_with_unit('165cm')}")
    print(f"1.65m -> {parse_number_with_unit('1.65m')}")
    print(f"50kg -> {parse_number_with_unit('50kg')}")
    print(f"50公斤 -> {parse_number_with_unit('50公斤')}")
    print(f"100斤 -> {parse_number_with_unit('100斤')}")
    
    print("\n=== 生成链接测试 ===")
    link = generate_search_link('成都', ['学生', '良家'])
    print(f"链接: {link}")
    
    print("\n=== 解析链接测试 ===")
    parsed1 = parse_search_link('searchchengdu_xuesheng_liangjia')
    print(f"搜索链接: {parsed1}")
    
    parsed2 = parse_search_link('251200011')
    print(f"编号链接: {parsed2}")