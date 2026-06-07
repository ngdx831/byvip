import shutil
import unittest
from pathlib import Path

from config import settings
from database.models import init_database
from database.operations import (
    create_subscription,
    create_user,
    get_users_need_push_this_hour,
    mark_user_pushed,
    update_user_type,
)
from services.subscription_rules import get_subscription_limit


class SubscriptionRuleTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(__file__).resolve().parents[1] / ".test_tmp" / self._testMethodName
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

    def test_subscription_limit_depends_on_user_type(self):
        self.assertEqual(get_subscription_limit({"user_type": "normal"}), 1)
        self.assertEqual(get_subscription_limit({"user_type": "vip"}), 5)

    def test_hourly_push_candidates_include_normal_and_vip_users(self):
        create_user(1001, "normal_user")
        create_user(1002, "vip_user")
        create_user(1003, "blocked_user")
        update_user_type(1002, "vip")
        update_user_type(1003, "blacklist")

        for user_id in (1001, 1002, 1003):
            create_subscription(
                user_id,
                {
                    "city": "上海",
                    "tags": ["学生"],
                },
            )

        self.assertEqual(set(get_users_need_push_this_hour()), {1001, 1002})

    def test_hourly_push_candidates_skip_users_already_pushed_this_hour(self):
        create_user(2001, "recently_pushed")
        create_subscription(2001, {"city": "成都", "tags": ["良家"]})

        self.assertEqual(get_users_need_push_this_hour(), [2001])

        mark_user_pushed(2001)

        self.assertEqual(get_users_need_push_this_hour(), [])


if __name__ == "__main__":
    unittest.main()
