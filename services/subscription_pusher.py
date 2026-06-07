"""
订阅推送定时任务。
每小时扫描最近入库的新帖子，匹配用户订阅后直接推送。
"""
import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from telegram import Bot
from telegram.error import TelegramError
from config.settings import (
    SUBSCRIPTION_PUSH_ENABLED,
    SUBSCRIPTION_PUSH_INTERVAL_MINUTES,
    SUBSCRIPTION_SEARCH_HOURS
)
from database.operations import (
    get_users_need_push_this_hour,
    mark_user_pushed,
    get_user_subscriptions
)
from services.post_fetcher import get_recent_posts_for_subscription
from utils.message_formatter import format_search_result_item

class SubscriptionPusher:
    """订阅推送器"""
    
    def __init__(self, bot: Bot):
        self.bot = bot
        self.is_running = False
        self.is_pushing = False  # 是否正在推送中
    
    async def push_to_user(self, user_id: int):
        """
        推送订阅内容给单个用户
        """
        try:
            # 获取用户的所有订阅
            subscriptions = get_user_subscriptions(user_id)
            
            if not subscriptions:
                print(f"用户 {user_id} 没有活跃订阅")
                return
            
            all_posts = []
            
            # 遍历每个订阅条件，获取匹配的帖子
            for sub in subscriptions:
                posts = get_recent_posts_for_subscription(
                    sub, 
                    hours=SUBSCRIPTION_SEARCH_HOURS
                )
                
                # 去重（基于post_number）
                for post in posts:
                    if not any(p['post_number'] == post['post_number'] for p in all_posts):
                        all_posts.append(post)
            
            if not all_posts:
                # 没有新内容，不推送
                print(f"用户 {user_id} 没有匹配的新内容")
                return
            
            # 构建推送消息
            message = "📬 <b>订阅推送</b>\n\n"
            message += f"为您找到 <b>{len(all_posts)}</b> 条符合订阅条件的最新信息：\n\n"
            
            for i, post in enumerate(all_posts[:10], 1):  # 最多推送10条
                message += f"{i}. {format_search_result_item(post, i)}\n"
            
            if len(all_posts) > 10:
                message += f"\n还有 {len(all_posts) - 10} 条结果，请使用搜索功能查看更多。"
            
            message += "\n\n💡 使用 <code>/delsub</code> 可删除所有订阅规则"
            
            # 发送推送
            await self.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode='HTML',
                disable_web_page_preview=True
            )
            
            # 标记已推送
            mark_user_pushed(user_id)
            print(f"✅ 已推送给用户 {user_id}，共 {len(all_posts)} 条结果")
            
        except TelegramError as e:
            print(f"❌ 推送失败 (用户 {user_id}): {e}")
        except Exception as e:
            print(f"❌ 推送出错 (用户 {user_id}): {e}")
    
    async def run_hourly_push(self):
        """
        执行每小时推送任务（分批次）
        """
        if self.is_pushing:
            print("推送任务正在进行中，跳过本次检查")
            return
        
        try:
            self.is_pushing = True
            
            # 获取本小时需要推送的用户列表
            user_ids = get_users_need_push_this_hour()
            
            if not user_ids:
                print("本小时没有需要推送的用户")
                return

            print(f"📬 开始每小时订阅推送，共 {len(user_ids)} 个用户待检查")
            
            # 分批次推送，避免拥堵
            for i, user_id in enumerate(user_ids, 1):
                try:
                    await self.push_to_user(user_id)
                    print(f"进度: {i}/{len(user_ids)}")
                    
                    # 间隔推送（避免频率限制）
                    if i < len(user_ids):
                        await asyncio.sleep(SUBSCRIPTION_PUSH_INTERVAL_MINUTES * 60)
                        
                except Exception as e:
                    print(f"推送用户 {user_id} 时出错: {e}")
                    continue
            
            print(f"✅ 本小时订阅推送检查完成，共检查 {len(user_ids)} 个用户")
            
        finally:
            self.is_pushing = False

    async def run_daily_push(self, _legacy_slot: str = None):
        """
        兼容旧调用：现在订阅推送按小时执行。
        """
        await self.run_hourly_push()
    
    async def schedule_loop(self):
        """
        推送调度循环
        每小时扫描一次最近入库的新帖子
        """
        self.is_running = True
        print("📬 订阅推送服务已启动")
        print(f"   每轮扫描最近 {SUBSCRIPTION_SEARCH_HOURS} 小时的新入库帖子")
        print(f"   推送间隔: {SUBSCRIPTION_PUSH_INTERVAL_MINUTES}分钟/用户")
        
        while self.is_running:
            try:
                if SUBSCRIPTION_PUSH_ENABLED:
                    await self.run_hourly_push()
                
                # 等待1小时后再次检查
                await asyncio.sleep(3600)
                
            except Exception as e:
                print(f"❌ 推送调度出错: {e}")
                await asyncio.sleep(300)  # 出错后等5分钟再试
    
    async def manual_push(self, user_id: int = None):
        """
        手动触发推送（测试用）
        user_id: 指定用户ID，None表示推送所有用户
        """
        try:
            if user_id:
                # 推送指定用户
                print(f"🧪 测试推送用户 {user_id}")
                await self.push_to_user(user_id)
            else:
                # 推送所有本小时未推送用户
                print("🧪 测试推送所有本小时未推送用户")
                await self.run_hourly_push()
            
            return True
        except Exception as e:
            print(f"❌ 手动推送失败: {e}")
            return False
    
    def stop(self):
        """停止推送服务"""
        self.is_running = False
        print("📬 订阅推送服务已停止")

# 创建全局推送器实例
_pusher_instance = None

def get_pusher(bot: Bot) -> SubscriptionPusher:
    """获取推送器单例"""
    global _pusher_instance
    if _pusher_instance is None:
        _pusher_instance = SubscriptionPusher(bot)
    return _pusher_instance
