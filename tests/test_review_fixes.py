import shutil
import unittest
from pathlib import Path

from config import settings
from database.models import init_database
from database.operations import (
    complete_payment_with_tx,
    create_payment,
    create_user,
    expire_payment,
    get_completed_payment_count,
    get_pending_payments,
    get_user,
    set_vip_expires,
    check_and_expire_vip,
)
from services.query_parser import parse_search_keywords_strict, parse_subscription_keywords
from utils.message_formatter import format_search_result_item, format_stats


class IsolatedDatabaseTestCase(unittest.TestCase):
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


class PaymentStateTests(IsolatedDatabaseTestCase):
    def test_completed_transaction_can_only_be_used_once(self):
        create_user(1001, "first")
        create_user(1002, "second")
        first_payment = create_payment(1001, 100.0, 100.12, "wallet")
        second_payment = create_payment(1002, 100.0, 100.12, "wallet")

        self.assertTrue(complete_payment_with_tx(first_payment, "tx-abc", "payer-a"))
        self.assertFalse(complete_payment_with_tx(second_payment, "tx-abc", "payer-a"))

        pending_ids = {payment["id"] for payment in get_pending_payments()}
        self.assertNotIn(first_payment, pending_ids)
        self.assertIn(second_payment, pending_ids)

    def test_expired_payment_is_removed_from_pending_list(self):
        create_user(2001, "buyer")
        payment_id = create_payment(2001, 100.0, 100.34, "wallet")

        self.assertIn(payment_id, {payment["id"] for payment in get_pending_payments()})

        self.assertTrue(expire_payment(payment_id))
        self.assertNotIn(payment_id, {payment["id"] for payment in get_pending_payments()})

    def test_completed_payment_count_tracks_successful_orders(self):
        create_user(2101, "buyer")
        first_payment = create_payment(2101, 100.0, 100.44, "wallet")
        second_payment = create_payment(2101, 100.0, 100.55, "wallet")

        self.assertEqual(get_completed_payment_count(2101), 0)
        complete_payment_with_tx(first_payment, "tx-first", "payer")
        self.assertEqual(get_completed_payment_count(2101), 1)
        complete_payment_with_tx(second_payment, "tx-second", "payer")
        self.assertEqual(get_completed_payment_count(2101), 2)


class VipExpiryTests(IsolatedDatabaseTestCase):
    def test_expired_vip_is_downgraded_to_normal(self):
        create_user(3001, "vip_user")
        set_vip_expires(3001, -1)

        self.assertEqual(check_and_expire_vip(), 1)
        self.assertEqual(get_user(3001)["user_type"], "normal")


class QueryParserTests(unittest.TestCase):
    def test_search_parser_accepts_documented_weight_examples(self):
        filters, unknown = parse_search_keywords_strict(["成都", "处女", "50", "20", "165cm", "B"])

        self.assertEqual(unknown, [])
        self.assertEqual(filters["city"], "成都")
        self.assertIn("处女", filters["tags"])
        self.assertEqual(filters["weight"], 100)
        self.assertEqual(filters["age"], 20)
        self.assertEqual(filters["height"], 165)
        self.assertEqual(filters["cup_size"], "B")

    def test_subscription_parser_accepts_units_and_converts_weight_to_jin(self):
        sub_data, unknown = parse_subscription_keywords(["上海", "学生", "50kg", "18岁", "1.65m"])

        self.assertEqual(unknown, [])
        self.assertEqual(sub_data["city"], "上海")
        self.assertEqual(sub_data["tags"], ["学生"])
        self.assertEqual((sub_data["weight_min"], sub_data["weight_max"]), (96, 104))
        self.assertEqual((sub_data["age_min"], sub_data["age_max"]), (16, 20))
        self.assertEqual((sub_data["height_min"], sub_data["height_max"]), (161, 169))


class FormatterSafetyTests(unittest.TestCase):
    def test_search_result_fields_are_html_escaped(self):
        rendered = format_search_result_item(
            {
                "post_number": "251221123045",
                "province": "四川<script>",
                "city": "成都&周边",
                "age": 20,
                "height": 165,
                "weight": 100,
                "cup_size": "B",
                "pocket_money": "<面议&可谈>",
                "tags": ["学生<", "良家&"],
                "created_at": "2026-06-07 12:00:00",
                "main_channel_link": "https://t.me/c/123/456",
            },
            1,
        )

        self.assertIn("四川&lt;script&gt; 成都&amp;周边", rendered)
        self.assertIn("&lt;面议&amp;可谈&gt;", rendered)
        self.assertIn("学生&lt; 良家&amp;", rendered)
        self.assertNotIn("<script>", rendered)

    def test_format_stats_handles_empty_database_stats(self):
        rendered = format_stats(
            {
                "total_users": 0,
                "vip_users": 0,
                "blacklist_users": 0,
                "today_new": 0,
            }
        )

        self.assertIn("VIP占比: 0.0%", rendered)


if __name__ == "__main__":
    unittest.main()
