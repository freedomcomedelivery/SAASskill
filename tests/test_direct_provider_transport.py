import os
import unittest
from unittest.mock import patch

from saasskill.direct_provider_transport import execute_direct_read


class DirectProviderTransportTests(unittest.TestCase):
    def test_semrush_dry_run_needs_no_key(self):
        with patch.dict(os.environ, {}, clear=True):
            out = execute_direct_read("semrush", {"params": {"type": "domain_rank", "domain": "example.com", "database": "us"}}, dry_run=True)
        self.assertEqual(out["status"], "dry_run")
        self.assertFalse(out["integration"]["direct_mode_configured"])

    def test_stripe_live_without_key_fails_before_network(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError):
                execute_direct_read("stripe", {"resource": "payment_intents"}, dry_run=False)

    def test_hubspot_rejects_non_crm_path(self):
        env={"HUBSPOT_ACCESS_TOKEN":"x"}
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaises(PermissionError):
                execute_direct_read("hubspot", {"path": "/marketing/v3/forms"}, dry_run=False)


if __name__ == "__main__":
    unittest.main()
