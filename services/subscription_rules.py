"""
订阅规则配置。
"""
from config.settings import NORMAL_MAX_SUBSCRIPTIONS, VIP_MAX_SUBSCRIPTIONS


def get_subscription_limit(user: dict) -> int:
    """根据用户类型返回可创建的最大订阅数。"""
    if user and user.get("user_type") == "vip":
        return VIP_MAX_SUBSCRIPTIONS
    return NORMAL_MAX_SUBSCRIPTIONS
