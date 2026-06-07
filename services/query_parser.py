"""
Search and subscription keyword parsing.

This module intentionally has no Telegram dependency so parsing rules can be
tested as plain business logic.
"""
from config.settings import HEIGHT_TOLERANCE, WEIGHT_TOLERANCE, AGE_TOLERANCE
from services.mapper import (
    match_city_with_variants,
    match_tag_with_variants,
    parse_number_with_unit,
)


PROVINCES = {
    "北京", "上海", "天津", "重庆",
    "广东", "浙江", "江苏", "山东", "河南", "四川", "湖北",
    "湖南", "河北", "福建", "安徽", "辽宁", "陕西", "江西",
    "山西", "黑龙江", "吉林", "云南", "贵州", "广西", "海南",
    "甘肃", "青海", "宁夏", "新疆", "内蒙古", "西藏",
}


def _number_to_typed_value(keyword: str):
    parsed_with_unit = parse_number_with_unit(keyword)
    if parsed_with_unit:
        return parsed_with_unit

    try:
        num = int(keyword)
    except ValueError:
        return None

    if 15 <= num <= 35:
        return ("age", num)

    # Most documented examples use 50/60/70 as kg-like body weight.
    # The collector database stores weight in jin, so convert these inputs.
    if 36 <= num <= 70:
        return ("weight", num * 2)

    if 71 <= num <= 140:
        return ("weight", num)

    if 141 <= num <= 195:
        return ("height", num)

    return ("unknown_number", num)


def _range_to_typed_value(keyword: str):
    if "-" not in keyword or keyword.startswith("-"):
        return None

    parts = keyword.split("-")
    if len(parts) != 2:
        return None

    try:
        start = int(parts[0])
        end = int(parts[1])
    except ValueError:
        return None

    if start > end:
        start, end = end, start

    if 15 <= start <= 35 and 15 <= end <= 35:
        return ("age", start, end)

    if 36 <= start <= 70 and 36 <= end <= 70:
        return ("weight", start * 2, end * 2)

    if 60 <= start <= 140 and 60 <= end <= 140:
        return ("weight", start, end)

    if 141 <= start <= 195 and 141 <= end <= 195:
        return ("height", start, end)

    return ("unknown_number", start, end)


def parse_search_keywords_strict(keywords: list) -> tuple:
    """
    Parse search keywords into collector DB filters.

    Returns: (filters, unknown_keywords)
    """
    filters = {
        "city": None,
        "province": None,
        "tags": [],
        "age": None,
        "height": None,
        "weight": None,
        "cup_size": None,
    }
    unknown_keywords = []

    for keyword in keywords:
        matched_range = _range_to_typed_value(keyword)
        if matched_range:
            kind = matched_range[0]
            if kind == "age":
                filters["age"] = (matched_range[1] + matched_range[2]) // 2
                continue
            if kind == "weight":
                filters["weight"] = (matched_range[1] + matched_range[2]) // 2
                continue
            if kind == "height":
                filters["height"] = (matched_range[1] + matched_range[2]) // 2
                continue
            unknown_keywords.append(f"{keyword}(超出范围)")
            continue

        typed_value = _number_to_typed_value(keyword)
        if typed_value:
            kind = typed_value[0]
            if kind in {"age", "weight", "height"}:
                filters[kind] = typed_value[1]
                continue
            unknown_keywords.append(f"{keyword}(超出范围)")
            continue

        if len(keyword) == 1 and keyword.upper() in "ABCDEFGH":
            filters["cup_size"] = keyword.upper()
            continue

        city = match_city_with_variants(keyword)
        if city:
            if city in PROVINCES:
                filters["province"] = city
            else:
                filters["city"] = city
            continue

        tag = match_tag_with_variants(keyword)
        if tag:
            if tag not in filters["tags"]:
                filters["tags"].append(tag)
            continue

        unknown_keywords.append(keyword)

    return filters, unknown_keywords


def parse_subscription_keywords(keywords: list) -> tuple:
    """
    Parse subscription keywords into subscription rule fields.

    Returns: (sub_data, unknown_keywords)
    """
    sub_data = {
        "city": None,
        "age_min": None,
        "age_max": None,
        "height_min": None,
        "height_max": None,
        "weight_min": None,
        "weight_max": None,
        "tags": [],
        "time_slot": "hourly",
    }
    unknown_keywords = []

    for keyword in keywords:
        matched_range = _range_to_typed_value(keyword)
        if matched_range:
            kind = matched_range[0]
            if kind == "age":
                sub_data["age_min"], sub_data["age_max"] = matched_range[1], matched_range[2]
                continue
            if kind == "weight":
                sub_data["weight_min"], sub_data["weight_max"] = matched_range[1], matched_range[2]
                continue
            if kind == "height":
                sub_data["height_min"], sub_data["height_max"] = matched_range[1], matched_range[2]
                continue
            unknown_keywords.append(f"{keyword}(超出范围)")
            continue

        typed_value = _number_to_typed_value(keyword)
        if typed_value:
            kind, value = typed_value
            if kind == "age":
                sub_data["age_min"] = max(15, value - AGE_TOLERANCE)
                sub_data["age_max"] = min(35, value + AGE_TOLERANCE)
                continue
            if kind == "weight":
                sub_data["weight_min"] = max(60, value - WEIGHT_TOLERANCE)
                sub_data["weight_max"] = min(140, value + WEIGHT_TOLERANCE)
                continue
            if kind == "height":
                sub_data["height_min"] = max(141, value - HEIGHT_TOLERANCE)
                sub_data["height_max"] = min(195, value + HEIGHT_TOLERANCE)
                continue
            unknown_keywords.append(f"{keyword}(超出范围)")
            continue

        city = match_city_with_variants(keyword)
        if city:
            sub_data["city"] = city
            continue

        tag = match_tag_with_variants(keyword)
        if tag:
            if tag not in sub_data["tags"]:
                sub_data["tags"].append(tag)
            continue

        unknown_keywords.append(keyword)

    return sub_data, unknown_keywords
