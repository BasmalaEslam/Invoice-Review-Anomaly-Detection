import os, sys, json, threading, unittest, urllib.request, urllib.error
from pathlib import Path
from unittest.mock import patch
from http.server import ThreadingHTTPServer as RealServer
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ['ENABLE_LLM']='0'
import common

class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.started=threading.Event()
        def server_factory(address,handler):
            cls.server=RealServer(('127.0.0.1',0),handler);cls.port=cls.server.server_address[1]
            cls.started.set();return cls.server
        def dispatch(path,payload):
            if path!='/echo':raise ValueError('Unknown endpoint')
            return payload
        cls.patch=patch.object(common,'ThreadingHTTPServer',server_factory);cls.patch.start()
        cls.thread=threading.Thread(target=common.serve,args=(dispatch,0),daemon=True);cls.thread.start()
        if not cls.started.wait(5):raise RuntimeError('HTTP test server not ready')
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join(5);cls.patch.stop()
    def request(self,path,body=None):
        req=urllib.request.Request('http://127.0.0.1:'+str(self.port)+path,data=body,headers={'Content-Type':'application/json'})
        return urllib.request.urlopen(req,timeout=5)
    def test_health_and_html(self):
        with self.request('/health') as r:self.assertEqual(json.load(r)['status'],'ok')
        with self.request('/') as r:self.assertIn('text/html',r.headers['Content-Type']);self.assertIn(b'Run scenario',r.read())
    def test_json_round_trip(self):
        with self.request('/echo',json.dumps({'message':'اختبار'}).encode()) as r:self.assertEqual(json.load(r),{'message':'اختبار'})
    def test_unknown_post_returns_400(self):
        with self.assertRaises(urllib.error.HTTPError) as c:self.request('/wrong',b'{}')
        self.assertEqual(c.exception.code,400)
    def test_invalid_json_or_array_returns_400(self):
        for raw in [b'not json',b'[]']:
            with self.subTest(raw=raw),self.assertRaises(urllib.error.HTTPError) as c:self.request('/echo',raw)
            self.assertEqual(c.exception.code,400)
    def test_csv_formula_escaping(self):
        output=common.csv_text([{'name':'=1+1','phone':'+201234','note':'safe'}])
        self.assertIn("'=1+1",output);self.assertIn("'+201234",output)
if __name__=='__main__':unittest.main()
