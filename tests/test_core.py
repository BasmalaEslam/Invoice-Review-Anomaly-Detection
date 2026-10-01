import os, sys, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ['ENABLE_LLM']='0'
import app, common

class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.patch=patch.object(common,'ROOT',Path(self.tmp.name));self.patch.start()
    def tearDown(self):
        self.patch.stop();self.tmp.cleanup()

    def payload(self,request_id='I1'):
        return {'request_id':request_id,'text':'Invoice: INV1\nVendor: Demo\nCurrency: EGP\nSubtotal: 1000\nTax: 140\nTotal: 1140\nItems: 4'}
    def test_decimal_reconciliation(self):
        p=self.payload();p['text']=p['text'].replace('Subtotal: 1000','Subtotal: 0.10').replace('Tax: 140','Tax: 0.20').replace('Total: 1140','Total: 0.30')
        self.assertNotIn('total_mismatch',app.process(p)['invoice']['flags'])
    def test_total_mismatch_flag(self):
        p=self.payload();p['text']=p['text'].replace('Total: 1140','Total: 1400')
        self.assertIn('total_mismatch',app.process(p)['invoice']['flags'])
    def test_duplicate_identity_across_request_ids(self):
        app.process(self.payload());self.assertTrue(app.process(self.payload('I2'))['duplicate'])
        self.assertEqual(len(app.dispatch('/invoices',{})['invoices']),1)
    def test_same_id_changed_payload_rejected(self):
        p=self.payload();app.process(p)
        with self.assertRaises(ValueError):app.process({**p,'text':p['text']+'\nChanged'})
    def test_human_review_audit_and_finality(self):
        app.process(self.payload());app.review({'invoice_id':'I1','decision':'rejected','reviewer':'Basmala'})
        result=app.dispatch('/invoices',{})
        self.assertEqual(result['invoices'][0]['status'],'rejected');self.assertEqual(len(result['audit']),1)
        with self.assertRaises(ValueError):app.review({'invoice_id':'I1','decision':'approved','reviewer':'Other'})
    def test_missing_fields_and_currency(self):
        result=app.process({'request_id':'I1','text':'Invoice: PARTIAL\nVendor: Demo\nCurrency: USD'})
        self.assertIn('missing:total',result['invoice']['flags']);self.assertIsNone(result['anomaly'])
    def test_money_rejects_invalid_precision(self):
        for v in ['NaN','Infinity','-1','1.001',True]:
            with self.subTest(value=v),self.assertRaises(ValueError):app.money(v)
    def test_llm_malformed_fields(self):
        with patch.object(app,'llm_json',return_value={'fields':{'total':'not-a-number'}}),self.assertRaises(ValueError):app.process(self.payload())
if __name__=='__main__':unittest.main()
