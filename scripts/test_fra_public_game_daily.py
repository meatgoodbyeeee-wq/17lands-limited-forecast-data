import datetime as dt
import gzip
import io
import unittest
import urllib.error
from fra_public_game_daily import URL, check

CSV=b'game_time,event_type,won,opening_hand_A,drawn_A\n2026-09-29,PremierDraft,True,2,1\n2026-09-30,PremierDraft,False,0,1\n'
NOW=dt.datetime(2026,9,30,tzinfo=dt.timezone.utc)
class Response(io.BytesIO):
    def __init__(self,body=b'',etag='v1'):
        super().__init__(body);self.headers={'ETag':etag}

class DailyCheckTests(unittest.TestCase):
    def run_check(self,previous=None,body=CSV):
        calls=[]
        def opener(req,**kwargs):
            self.assertEqual(req.full_url,URL)
            calls.append(req.get_method())
            return Response(gzip.compress(body) if req.get_method()=='GET' else b'')
        result=check(previous or {},NOW,opener)
        return result,calls
    def test_valid_game_only(self):
        result,calls=self.run_check()
        self.assertEqual(calls,['HEAD','GET'])
        self.assertEqual(result['status'],'available')
        self.assertEqual(result['observations']['cards'][0]['gih'],75)
        self.assertNotIn('alsa',result['observations']['cards'][0])
    def test_release_date_does_not_switch(self):
        def unavailable(req,**kwargs):raise urllib.error.HTTPError(URL,404,'missing',{},None)
        result=check({},dt.datetime(2026,9,29,tzinfo=dt.timezone.utc),unavailable)
        self.assertEqual(result['status'],'unavailable')
        self.assertIsNone(result.get('observations'))
    def test_before_release_no_request(self):
        result=check({},dt.datetime(2026,9,28,tzinfo=dt.timezone.utc),lambda *a,**k:self.fail('request before release'))
        self.assertEqual(result['status'],'awaiting_release')
    def test_daily_guard(self):
        old,_=self.run_check()
        result,calls=self.run_check(old)
        self.assertEqual(calls,[]);self.assertEqual(result,old)
    def test_unchanged_file(self):
        old,_=self.run_check();old['checked_at']='2026-09-29T00:00:00Z'
        result,calls=self.run_check(old)
        self.assertEqual(calls,['HEAD']);self.assertEqual(result['observations'],old['observations'])
    def test_invalid_or_empty_data_not_available(self):
        for body in [b'invalid\n',CSV.replace(b'PremierDraft',b'QuickDraft'),CSV.replace(b'2026-09',b'2025-09')]:
            result,_=self.run_check(body=body)
            self.assertEqual(result['status'],'error');self.assertIsNone(result.get('observations'))
    def test_failure_retains_previous(self):
        old,_=self.run_check();old['checked_at']='2026-09-29T00:00:00Z'
        for status in (403,404,500):
            def fail(req,**kwargs):raise urllib.error.HTTPError(URL,status,'unavailable',{},None)
            result=check(old,NOW,fail)
            self.assertEqual(result['observations'],old['observations'])

if __name__=='__main__':unittest.main()
