import shutil
import sys
import types
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path


if "telegram" not in sys.modules:
    telegram_module = types.ModuleType("telegram")
    sys.modules["telegram"] = telegram_module
else:
    telegram_module = sys.modules["telegram"]
telegram_module.Bot = object

if "telegram.error" not in sys.modules:
    telegram_error_module = types.ModuleType("telegram.error")
    sys.modules["telegram.error"] = telegram_error_module
else:
    telegram_error_module = sys.modules["telegram.error"]
telegram_error_module.TelegramError = Exception

if "aiohttp" not in sys.modules:
    aiohttp_module = types.ModuleType("aiohttp")
    aiohttp_module.ClientSession = object
    sys.modules["aiohttp"] = aiohttp_module


from config import settings
from database.models import init_database
from database.operations import (
    create_payment,
    create_user,
    expire_user_pending_payments,
    get_pending_payments,
)
from services.payment_checker import PaymentChecker


class FakeBot:
    def __init__(self):
        self.sent_messages = []

    async def send_message(self, **kwargs):
        self.sent_messages.append(kwargs)


class PaymentCheckerTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmpdir = Path(__file__).resolve().parents[1] / ".test_tmp" / self.__class__.__name__ / self._testMethodName
        if self.tmpdir.exists():
            shutil.rmtree(self.tmpdir)
        self.tmpdir.mkdir(parents=True)
        self.original_db_path = settings.USER_DATABASE_PATH
        self.db_path = str(self.tmpdir / "users.db")
        settings.USER_DATABASE_PATH = self.db_path
        init_database(self.db_path)

    def tearDown(self):
        settings.USER_DATABASE_PATH = self.original_db_path
        if self.tmpdir.exists():
            shutil.rmtree(self.tmpdir)

    async def test_duplicate_timeout_monitors_send_only_one_notification(self):
        create_user(601, "buyer")
        payment_id = create_payment(601, 88.0, 88.12, "wallet")
        payment_data = get_pending_payments(601)[0]
        payment_data["expired_at"] = "2000-01-01 00:00:00"

        bot = FakeBot()
        first_checker = PaymentChecker(bot)
        second_checker = PaymentChecker(bot)

        with redirect_stdout(StringIO()):
            await first_checker.monitor_payment(dict(payment_data))
            await second_checker.monitor_payment(dict(payment_data))

        self.assertEqual(len(bot.sent_messages), 1)
        self.assertEqual(bot.sent_messages[0]["chat_id"], 601)

    async def test_multiple_pending_orders_for_same_user_send_one_timeout_notification(self):
        create_user(602, "buyer")
        create_payment(602, 88.0, 88.31, "wallet")
        create_payment(602, 88.0, 88.32, "wallet")
        payment_data_list = get_pending_payments(602)
        for payment_data in payment_data_list:
            payment_data["expired_at"] = "2000-01-01 00:00:00"

        bot = FakeBot()
        checker = PaymentChecker(bot)

        with redirect_stdout(StringIO()):
            for payment_data in payment_data_list:
                await checker.monitor_payment(dict(payment_data))

        self.assertEqual(len(bot.sent_messages), 1)
        self.assertEqual(get_pending_payments(602), [])


class PendingPaymentStateTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(__file__).resolve().parents[1] / ".test_tmp" / self.__class__.__name__ / self._testMethodName
        if self.tmpdir.exists():
            shutil.rmtree(self.tmpdir)
        self.tmpdir.mkdir(parents=True)
        self.original_db_path = settings.USER_DATABASE_PATH
        self.db_path = str(self.tmpdir / "users.db")
        settings.USER_DATABASE_PATH = self.db_path
        init_database(self.db_path)

    def tearDown(self):
        settings.USER_DATABASE_PATH = self.original_db_path
        if self.tmpdir.exists():
            shutil.rmtree(self.tmpdir)

    def test_can_expire_existing_pending_payments_for_user_before_new_order(self):
        create_user(701, "buyer")
        create_payment(701, 88.0, 88.21, "wallet")
        create_payment(701, 88.0, 88.22, "wallet")

        self.assertEqual(len(get_pending_payments(701)), 2)

        self.assertEqual(expire_user_pending_payments(701), 2)
        self.assertEqual(get_pending_payments(701), [])


if __name__ == "__main__":
    unittest.main()
