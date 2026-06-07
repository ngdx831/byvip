import shutil
import sys
import types
import unittest
from pathlib import Path
from types import SimpleNamespace


class BadRequest(Exception):
    pass


if "telegram" not in sys.modules:
    telegram_module = types.ModuleType("telegram")
    telegram_module.Update = object
    telegram_module.ForumTopic = object
    sys.modules["telegram"] = telegram_module

    telegram_ext_module = types.ModuleType("telegram.ext")
    telegram_ext_module.ContextTypes = SimpleNamespace(DEFAULT_TYPE=object)
    sys.modules["telegram.ext"] = telegram_ext_module

    telegram_error_module = types.ModuleType("telegram.error")
    telegram_error_module.BadRequest = BadRequest
    sys.modules["telegram.error"] = telegram_error_module


from config import settings
from database.models import init_database
from database.operations import create_user
from handlers import customer_service


class FakeBot:
    def __init__(self):
        self.sent_messages = []
        self.created_topics = []
        self.fail_first_send = True

    async def send_message(self, **kwargs):
        self.sent_messages.append(kwargs)
        if self.fail_first_send:
            self.fail_first_send = False
            raise BadRequest("Message thread not found")

    async def create_forum_topic(self, **kwargs):
        self.created_topics.append(kwargs)
        return SimpleNamespace(message_thread_id=222)


class CustomerServiceTopicTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmpdir = Path(__file__).resolve().parents[1] / ".test_tmp" / self.__class__.__name__ / self._testMethodName
        if self.tmpdir.exists():
            shutil.rmtree(self.tmpdir)
        self.tmpdir.mkdir(parents=True)
        self.original_db_path = settings.USER_DATABASE_PATH
        self.original_handler_db_path = customer_service.USER_DATABASE_PATH
        self.db_path = str(self.tmpdir / "users.db")
        settings.USER_DATABASE_PATH = self.db_path
        customer_service.USER_DATABASE_PATH = self.db_path
        init_database(self.db_path)

    def tearDown(self):
        settings.USER_DATABASE_PATH = self.original_db_path
        customer_service.USER_DATABASE_PATH = self.original_handler_db_path
        if self.tmpdir.exists():
            shutil.rmtree(self.tmpdir)

    async def test_recreates_deleted_customer_service_topic_for_existing_user(self):
        create_user(501, "old_user")
        customer_service.save_topic_id(501, 111)
        bot = FakeBot()
        update = SimpleNamespace(
            effective_user=SimpleNamespace(id=501, username="old_user"),
            message=SimpleNamespace(
                text="hello",
                caption=None,
                photo=[],
                video=None,
                document=None,
            ),
        )
        context = SimpleNamespace(bot=bot)

        await customer_service.forward_to_customer_service(update, context)

        self.assertEqual(customer_service.get_topic_id(501), 222)
        self.assertEqual(len(bot.created_topics), 1)
        self.assertEqual([message["message_thread_id"] for message in bot.sent_messages], [111, 222])


if __name__ == "__main__":
    unittest.main()
