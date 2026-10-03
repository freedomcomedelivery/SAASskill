import unittest
from saasskill.crm import normalize_crm_result

class CRMNormalizerTests(unittest.TestCase):
    def test_hubspot_stages(self):
        payload={"results":[{"id":"1","properties":{"lifecyclestage":"lead"}},{"id":"2","properties":{"lifecyclestage":"salesqualifiedlead"}},{"id":"3","properties":{"lifecyclestage":"customer"}}]}
        result=normalize_crm_result(provider="hubspot",request_id="r1",payload=payload)
        self.assertEqual(result["data"]["summary"]["leads"],3)
        self.assertEqual(result["data"]["summary"]["qualified_leads"],2)
        self.assertEqual(result["data"]["summary"]["paid_stage_count"],1)

if __name__=="__main__":
    unittest.main()
