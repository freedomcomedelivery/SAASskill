import unittest

from saasskill.ads_write_transport import execute_ads_write_dispatch


class AdsWriteTransportTests(unittest.TestCase):
    def test_dry_run_never_needs_credentials(self):
        dispatch={"provider":"google_ads","operation":"campaign.status","target":"123","payload":{"customer_id":"1","status":"PAUSED"},"apply":False,"dry_run":True}
        out=execute_ads_write_dispatch(dispatch,dry_run=True)
        self.assertEqual(out["status"],"dry_run")

    def test_live_rejects_unapproved_dispatch(self):
        dispatch={"provider":"meta_ads","operation":"campaign.status","target":"123","payload":{"status":"PAUSED"},"apply":False,"dry_run":False}
        with self.assertRaises(PermissionError):
            execute_ads_write_dispatch(dispatch,dry_run=False)

    def test_unsupported_complex_write_is_explicit(self):
        dispatch={"provider":"apple_ads","operation":"campaign.create","target":"1","payload":{},"apply":True,"dry_run":False,"approval_id":"a1","plan_digest":"sha256:x"}
        with self.assertRaises(NotImplementedError):
            execute_ads_write_dispatch(dispatch,dry_run=False)


if __name__ == "__main__":
    unittest.main()
