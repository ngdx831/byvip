"""
翻页按钮生成器
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from typing import List

def generate_pagination_buttons(
    current_page: int,
    total_pages: int,
    callback_prefix: str
) -> InlineKeyboardMarkup:
    """
    生成翻页按钮
    
    Args:
        current_page: 当前页码（从0开始）
        total_pages: 总页数
        callback_prefix: 回调前缀（如 "search_page"）
    
    Returns:
        InlineKeyboardMarkup
    """
    keyboard = []
    
    # 如果只有一页，不显示翻页按钮
    if total_pages <= 1:
        return None
    
    buttons = []
    
    # 上一页按钮
    if current_page > 0:
        buttons.append(
            InlineKeyboardButton(
                "⬅️ 上一页",
                callback_data=f"{callback_prefix}_{current_page - 1}"
            )
        )
    
    # 页码显示
    buttons.append(
        InlineKeyboardButton(
            f"📄 {current_page + 1}/{total_pages}",
            callback_data="page_info"
        )
    )
    
    # 下一页按钮
    if current_page < total_pages - 1:
        buttons.append(
            InlineKeyboardButton(
                "下一页 ➡️",
                callback_data=f"{callback_prefix}_{current_page + 1}"
            )
        )
    
    keyboard.append(buttons)
    
    return InlineKeyboardMarkup(keyboard)

def generate_search_result_buttons(
    results: List[dict],
    current_page: int,
    total_pages: int,
    search_keyword: str = None
) -> InlineKeyboardMarkup:
    """
    生成搜索结果的翻页按钮
    
    Args:
        results: 当前页的搜索结果
        current_page: 当前页码
        total_pages: 总页数
        search_keyword: 搜索关键词（用于callback）
    """
    keyboard = []
    
    # 翻页按钮
    if total_pages > 1:
        buttons = []
        
        if current_page > 0:
            buttons.append(
                InlineKeyboardButton(
                    "⬅️ 上一页",
                    callback_data=f"search_page_{current_page - 1}"
                )
            )
        
        buttons.append(
            InlineKeyboardButton(
                f"📄 {current_page + 1}/{total_pages}",
                callback_data="page_info"
            )
        )
        
        if current_page < total_pages - 1:
            buttons.append(
                InlineKeyboardButton(
                    "下一页 ➡️",
                    callback_data=f"search_page_{current_page + 1}"
                )
            )
        
        keyboard.append(buttons)
    
    return InlineKeyboardMarkup(keyboard) if keyboard else None

def split_results_to_pages(results: List, page_size: int = 10) -> List[List]:
    """
    将结果分页
    
    Args:
        results: 结果列表
        page_size: 每页大小
    
    Returns:
        分页后的结果
    """
    pages = []
    for i in range(0, len(results), page_size):
        pages.append(results[i:i + page_size])
    return pages

def get_total_pages(total_results: int, page_size: int = 10) -> int:
    """
    计算总页数
    """
    return (total_results + page_size - 1) // page_size

if __name__ == '__main__':
    # 测试
    print("=== 测试分页 ===")
    test_results = list(range(1, 51))  # 50条结果
    pages = split_results_to_pages(test_results, page_size=10)
    print(f"总共 {len(test_results)} 条结果")
    print(f"分为 {len(pages)} 页")
    print(f"第1页: {pages[0]}")
