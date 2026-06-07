"""
USDT支付自动检测
为每个订单启动独立的检测任务
15秒检测一次，10分钟后超时
"""
import asyncio
import aiohttp
from datetime import datetime, timedelta
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from telegram import Bot
from telegram.error import TelegramError
from config.settings import (
    USDT_WALLET_ADDRESS,
    VIP_DURATION_DAYS,
    PAYMENT_CHECK_INTERVAL_SECONDS,
    PAYMENT_TIMEOUT_MINUTES,
    REFERRAL_BONUS_BALANCE,
    VIP_MAX_SUBSCRIPTIONS
)
from database.operations import (
    complete_payment_with_tx,
    expire_user_pending_payments,
    get_completed_payment_count,
    get_pending_payments,
    get_user_by_id,
    set_vip_expires,
    update_user_balance
)

# TronGrid API配置
TRONGRID_API = "https://api.trongrid.io"
USDT_CONTRACT = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"  # TRC20 USDT合约地址

class PaymentChecker:
    """支付检测器"""
    
    def __init__(self, bot: Bot):
        self.bot = bot
        self.active_tasks = {}  # {payment_id: task}
    
    async def get_recent_transactions(self) -> list:
        """
        从TronGrid获取最近的USDT转账记录
        """
        try:
            async with aiohttp.ClientSession() as session:
                # 获取TRC20转账记录
                url = f"{TRONGRID_API}/v1/accounts/{USDT_WALLET_ADDRESS}/transactions/trc20"
                params = {
                    'limit': 50,
                    'contract_address': USDT_CONTRACT
                }
                
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get('data', [])
                    else:
                        print(f"❌ TronGrid API错误: {response.status}")
                        return []
                        
        except Exception as e:
            print(f"❌ 获取交易记录失败: {e}")
            return []
    
    async def check_single_payment(self, payment_data: dict, transactions: list):
        """
        检查单个订单是否已支付
        
        payment_data: {
            'id': 订单ID,
            'user_id': 用户ID,
            'verification_amount': 验证金额（99.xx）
            'created_at': 创建时间
        }
        """
        try:
            user_id = payment_data['user_id']
            expected_amount = float(payment_data['verification_amount'])
            
            # 遍历交易记录
            for tx in transactions:
                # 检查是否是转入交易
                if tx.get('to') != USDT_WALLET_ADDRESS:
                    continue
                
                # 检查金额是否匹配（USDT有6位小数）
                amount = float(tx.get('value', 0)) / 1000000
                
                # 金额必须完全匹配（误差<0.01）
                if abs(amount - expected_amount) < 0.01:
                    # 检查交易时间是否在订单创建之后
                    tx_timestamp = tx.get('block_timestamp', 0) / 1000
                    tx_time = datetime.fromtimestamp(tx_timestamp)
                    order_time = datetime.fromisoformat(payment_data['created_at'])
                    
                    if tx_time >= order_time:
                        tx_id = tx.get('transaction_id') or tx.get('txID') or tx.get('hash')
                        if not tx_id:
                            continue
                        print(f"✅ 找到匹配交易: {amount} USDT from {tx.get('from')}")
                        return {
                            "tx_id": tx_id,
                            "payer_address": tx.get('from'),
                            "amount": amount,
                        }
            
            return None
            
        except Exception as e:
            print(f"❌ 检查支付失败: {e}")
            return None
    
    async def process_completed_payment(self, payment_data: dict, tx_data: dict):
        """
        处理已完成的支付
        1. 升级为VIP
        2. 增加余额
        3. 给推荐人奖励（如果有）
        4. 发送通知
        """
        try:
            user_id = payment_data['user_id']
            amount = float(payment_data.get('amount_usdt', 0))
            
            # 完成订单；同一笔链上交易只能核销一次
            completed = complete_payment_with_tx(
                payment_data['id'],
                tx_data.get("tx_id"),
                tx_data.get("payer_address"),
            )
            if not completed:
                print(f"⚠️ 订单 {payment_data['id']} 已处理、已过期或交易已被使用")
                return
            
            # ✅ 修正：set_vip_expires 第二个参数是 days(int)
            set_vip_expires(user_id, VIP_DURATION_DAYS)
            
            # 增加余额
            update_user_balance(user_id, amount)
            
            # 计算过期时间（用于通知）
            expiry_date = datetime.now() + timedelta(days=VIP_DURATION_DAYS)
            
            # 检查推荐人
            user = get_user_by_id(user_id)
            if user and user.get('referrer_id') and get_completed_payment_count(user_id) == 1:
                # 给推荐人增加余额
                update_user_balance(user['referrer_id'], REFERRAL_BONUS_BALANCE)
                
                # 通知推荐人
                try:
                    await self.bot.send_message(
                        chat_id=user['referrer_id'],
                        text=f"🎉 您推荐的用户开通了VIP，您获得了 {REFERRAL_BONUS_BALANCE} USDT余额奖励！"
                    )
                except:
                    pass
            
            # 通知用户
            message = f"""
🎉 <b>支付成功！</b>

您的VIP会员已开通：
💎 会员时长：{VIP_DURATION_DAYS}天
💰 账户余额：+{amount} USDT
📅 到期时间：{expiry_date.strftime('%Y-%m-%d %H:%M')}

现在您可以：
✅ 无限制查看验证视频
✅ 设置订阅推送（最多{VIP_MAX_SUBSCRIPTIONS}个规则）
✅ 享受专属服务

感谢您的支持！
"""
            
            await self.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode='HTML'
            )
            
            print(f"✅ 用户 {user_id} 支付处理完成")
            
        except Exception as e:
            print(f"❌ 处理支付完成失败 (订单 {payment_data['id']}): {e}")
    
    async def monitor_payment(self, payment_data: dict):
        """
        监控单个订单的支付状态
        15秒检测一次，10分钟后超时
        """
        payment_id = payment_data['id']
        user_id = payment_data['user_id']
        verification_amount = payment_data['verification_amount']
        
        print(f"💳 开始监控订单 #{payment_id} (用户 {user_id}, 金额 {verification_amount})")
        
        # 计算超时时间。恢复历史订单时优先使用数据库里的 expired_at。
        try:
            timeout_at = datetime.fromisoformat(str(payment_data.get('expired_at')))
        except Exception:
            timeout_at = datetime.now() + timedelta(minutes=PAYMENT_TIMEOUT_MINUTES)
        
        try:
            while True:
                # 检查是否超时
                if datetime.now() > timeout_at:
                    print(f"⏰ 订单 #{payment_id} 已超时（{PAYMENT_TIMEOUT_MINUTES}分钟）")
                    expired_count = expire_user_pending_payments(user_id)
                    if expired_count <= 0:
                        print(f"ℹ️ 用户 {user_id} 的订单已被其他任务处理，跳过超时通知")
                        break

                    # 通知用户订单已过期
                    try:
                        await self.bot.send_message(
                            chat_id=user_id,
                            text=f"⚠️ 支付订单已过期\n\n请重新发起支付：/pay"
                        )
                    except:
                        pass
                    
                    break
                
                # 获取最新交易记录
                transactions = await self.get_recent_transactions()
                
                if transactions:
                    # 检查是否已支付
                    is_paid = await self.check_single_payment(payment_data, transactions)
                    
                    if is_paid:
                        # 处理支付成功
                        await self.process_completed_payment(payment_data, is_paid)
                        break
                
                # 等待15秒后再次检测
                await asyncio.sleep(PAYMENT_CHECK_INTERVAL_SECONDS)
                
        except asyncio.CancelledError:
            print(f"🛑 订单 #{payment_id} 监控已取消")
        except Exception as e:
            print(f"❌ 监控订单 #{payment_id} 出错: {e}")
        finally:
            # 从活跃任务列表中移除
            if payment_id in self.active_tasks:
                del self.active_tasks[payment_id]
    
    def start_monitoring(self, payment_data: dict):
        """
        为订单启动监控任务
        """
        payment_id = payment_data['id']
        
        # 检查是否已有监控任务
        if payment_id in self.active_tasks:
            print(f"⚠️ 订单 #{payment_id} 已在监控中")
            return
        
        # 创建并启动监控任务
        task = asyncio.create_task(self.monitor_payment(payment_data))
        self.active_tasks[payment_id] = task

    def resume_pending_payments(self):
        """
        Bot 重启后恢复仍未过期的 pending 订单监控。
        """
        for payment in get_pending_payments():
            payment_data = dict(payment)
            payment_data['created_at'] = str(payment_data['created_at'])
            self.start_monitoring(payment_data)
    
    def cancel_monitoring(self, payment_id: int):
        """
        取消订单监控
        """
        if payment_id in self.active_tasks:
            self.active_tasks[payment_id].cancel()
            del self.active_tasks[payment_id]
            print(f"🛑 已取消订单 #{payment_id} 的监控")

# 创建全局检测器实例
_checker_instance = None

def get_payment_checker(bot: Bot) -> PaymentChecker:
    """获取支付检测器单例"""
    global _checker_instance
    if _checker_instance is None:
        _checker_instance = PaymentChecker(bot)
    return _checker_instance
