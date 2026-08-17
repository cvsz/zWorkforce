import unittest
from common import stack
from zworkforce.connectors import (
    CONNECTOR_REGISTRY,
    SignatureVerifier,
    SocialShopConnectorExecutor,
    ConnectorError,
)
from zworkforce.tools import ToolExecutor, TOOL_DEFINITIONS

class ConnectorsTests(unittest.TestCase):
    def setUp(self):
        self.temp, self.settings, self.db, self.provider, self.engine, self.auth = stack()
        self.executor = SocialShopConnectorExecutor(self.settings, self.db)

    def tearDown(self):
        self.temp.cleanup()

    def test_connector_catalog_contains_social_and_shop_platforms(self):
        catalog = self.executor.list_connectors()
        connectors = {c["connector"] for c in catalog}
        self.assertIn("facebook", connectors)
        self.assertIn("instagram", connectors)
        self.assertIn("tiktok_content", connectors)
        self.assertIn("tiktok_shop", connectors)
        self.assertIn("shopee_seller", connectors)
        self.assertIn("facebook_commerce", connectors)
        self.assertIn("youtube", connectors)
        self.assertIn("x_twitter", connectors)
        self.assertIn("linkedin", connectors)

    def test_meta_appsecret_proof_signature(self):
        token = "EAABwzLIX123"
        secret = "appsecret456"
        proof = SignatureVerifier.meta_appsecret_proof(token, secret)
        self.assertEqual(len(proof), 64)
        with self.assertRaises(ConnectorError):
            SignatureVerifier.meta_appsecret_proof("", secret)

    def test_shopee_v2_hmac_signature(self):
        partner_id = 12345
        path = "/api/v2/order/get_order_list"
        timestamp = 1700000000
        partner_key = "partner_secret_key"
        sig = SignatureVerifier.shopee_v2_signature(partner_id, path, timestamp, partner_key)
        self.assertEqual(len(sig), 64)

        # With shop access token
        sig_shop = SignatureVerifier.shopee_v2_signature(partner_id, path, timestamp, partner_key, access_token="tok123", shop_id=6789)
        self.assertEqual(len(sig_shop), 64)
        self.assertNotEqual(sig, sig_shop)

    def test_tiktok_shop_hmac_signature(self):
        app_secret = "tt_shop_secret"
        path = "/api/products/search"
        params = {"app_key": "key1", "timestamp": 1700000000, "shop_cipher": "cipher123"}
        sig = SignatureVerifier.tiktok_shop_signature(app_secret, path, params)
        self.assertEqual(len(sig), 64)

    def test_social_connector_read_and_mutating_execution(self):
        # Read-only insights
        res = self.executor.execute_action(
            "facebook",
            "facebook_get_insights",
            {"period": "day"},
            tenant_id="default",
            actor="user:tester",
            mutating_approved=False,
        )
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["action"], "facebook_get_insights")

        # Mutating publish without approval fails
        with self.assertRaises(ConnectorError):
            self.executor.execute_action(
                "facebook",
                "facebook_publish_post",
                {"caption": "Hello World"},
                tenant_id="default",
                actor="user:tester",
                mutating_approved=False,
            )

        # Mutating publish with approval succeeds
        res_pub = self.executor.execute_action(
            "facebook",
            "facebook_publish_post",
            {"caption": "Hello World"},
            tenant_id="default",
            actor="user:tester",
            mutating_approved=True,
        )
        self.assertEqual(res_pub["status"], "success")
        self.assertTrue(res_pub["payload_summary"]["mutating"])

    def test_shop_connector_shopee_and_tiktok_shop(self):
        # Shopee inventory sync
        res_shopee = self.executor.execute_action(
            "shopee_seller",
            "shopee_update_stock",
            {"item_id": 1001, "stock": 50},
            tenant_id="default",
            actor="user:tester",
            mutating_approved=True,
        )
        self.assertEqual(res_shopee["status"], "success")
        self.assertEqual(res_shopee["connector"], "shopee_seller")

        # TikTok Shop price update
        res_tt = self.executor.execute_action(
            "tiktok_shop",
            "tiktok_shop_update_price",
            {"product_id": "p_123", "price": 299.0},
            tenant_id="default",
            actor="user:tester",
            mutating_approved=True,
        )
        self.assertEqual(res_tt["status"], "success")
        self.assertEqual(res_tt["connector"], "tiktok_shop")

    def test_tool_executor_dispatches_connectors(self):
        tools = ToolExecutor(self.settings, self.db)
        self.assertIn("social_connector", TOOL_DEFINITIONS)
        self.assertIn("shop_connector", TOOL_DEFINITIONS)

        res = tools.execute(
            "social_connector",
            {"platform": "instagram", "action": "instagram_get_insights", "params": {"metric": "impressions"}},
            tenant_id="default",
            agent_id="social-manager",
            actor="user:alice",
        )
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["connector"], "instagram")


if __name__ == "__main__":
    unittest.main()
