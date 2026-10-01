import os, sys, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ['ENABLE_LLM']='0'
import app, common

import io, json
class AdapterTests(unittest.TestCase):
    def test_disabled_never_calls_network(self):
        with patch('urllib.request.urlopen') as request:
            self.assertIsNone(common.llm_json('system','input'));request.assert_not_called()
    def test_openai_compatible_response(self):
        body={'choices':[{'message':{'content':'{"ok":true}'}}]}
        response=io.BytesIO(json.dumps(body).encode())
        with patch.dict(os.environ,{'ENABLE_LLM':'1','LLM_MODEL':'local-test'}),patch('urllib.request.urlopen',return_value=response) as request:
            self.assertEqual(common.llm_json('system','input'),{'ok':True})
            self.assertTrue(request.call_args.args[0].full_url.endswith('/v1/chat/completions'))
    def test_malformed_response_fails_explicitly(self):
        response=io.BytesIO(b'{"choices":[{"message":{"content":"not-json"}}]}')
        with patch.dict(os.environ,{'ENABLE_LLM':'1','LLM_MODEL':'local-test'}),patch('urllib.request.urlopen',return_value=response),self.assertRaises(ValueError):common.llm_json('system','input')
if __name__=='__main__':unittest.main()
