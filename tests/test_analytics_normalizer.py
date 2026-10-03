import unittest
from saasskill.analytics import normalize_analytics_result

class AnalyticsNormalizerTests(unittest.TestCase):
    def test_ga4_rows(self):
        payload={"metricHeaders":[{"name":"sessions"},{"name":"ecommercePurchases"},{"name":"totalRevenue"}],"rows":[{"metricValues":[{"value":"100"},{"value":"3"},{"value":"120.50"}]},{"metricValues":[{"value":"50"},{"value":"2"},{"value":"80"}]}]}
        result=normalize_analytics_result(provider="ga4",request_id="r1",payload=payload,context={"workflow":"existing_project_audit"})
        self.assertEqual(result["data"]["totals"]["visits"],150)
        self.assertEqual(result["data"]["totals"]["payments"],5)
        self.assertEqual(result["data"]["totals"]["revenue"],200.5)

    def test_posthog_column_result(self):
        result=normalize_analytics_result(provider="posthog",request_id="r2",payload={"columns":["users","leads"],"results":[[100,10],[50,4]]})
        self.assertEqual(result["data"]["totals"]["reach"],150)
        self.assertEqual(result["data"]["totals"]["leads"],14)

if __name__=="__main__":
    unittest.main()
