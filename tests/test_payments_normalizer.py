import unittest
from saasskill.payments import normalize_payments_result

class PaymentNormalizerTests(unittest.TestCase):
    def test_stripe_verified_payments(self):
        payload={"data":[{"id":"pi_1","object":"payment_intent","status":"succeeded","amount_received":1000,"currency":"usd"},{"id":"pi_2","object":"payment_intent","status":"requires_payment_method","amount_received":0,"currency":"usd"},{"id":"ch_1","object":"charge","paid":True,"refunded":False,"amount":2500,"currency":"usd"}]}
        result=normalize_payments_result(provider="stripe",request_id="r1",payload=payload,context={"workflow":"existing_project_audit"})
        self.assertEqual(result["data"]["count"],2)
        self.assertEqual(result["data"]["revenue"],35.0)
        self.assertEqual(result["state_merge_patch"]["audit_snapshot"]["verified_payments"]["count"],2)

if __name__=="__main__":
    unittest.main()
