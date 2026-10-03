import os
import unittest
from unittest.mock import patch

from saasskill.integration_status import integration_status


class IntegrationStatusTests(unittest.TestCase):
    def test_ahrefs_remote_mcp_is_host_managed(self):
        with patch.dict(os.environ, {}, clear=True):
            out = integration_status("ahrefs")
        self.assertEqual(out["endpoint"], "https://api.ahrefs.com/mcp/mcp")
        self.assertFalse(out["direct_mode_configured"])
        self.assertIn("host-managed", out["note"])

    def test_yandex_token_group(self):
        with patch.dict(os.environ, {"YANDEX_DIRECT_TOKEN": "x"}, clear=True):
            out = integration_status("yandex_direct")
        self.assertTrue(out["direct_mode_configured"])


if __name__ == "__main__":
    unittest.main()
