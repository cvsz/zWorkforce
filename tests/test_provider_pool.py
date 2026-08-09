from zworkforce.providers import _clean_error
from dataclasses import replace
import unittest

from common import stack
from zworkforce.config import ProviderConfig
from zworkforce.providers import ProviderError, ProviderPool, ProviderResult, Usage

class BadEndpoint:
    def chat(self,*args,**kwargs): raise ProviderError("boom",retryable=True)
class GoodEndpoint:
    def chat(self,tier,messages,tools): return ProviderResult("ok","backup","backup-model",Usage(2,0,1),[],{"role":"assistant","content":"ok"})

class ProviderPoolTests(unittest.TestCase):
    def test_provider_error_redacts_credentials(self):
        cleaned=_clean_error("Authorization: Bearer sk_supersecret123456 api_key=abcdef123456")
        self.assertNotIn("sk_supersecret", cleaned); self.assertNotIn("abcdef123456", cleaned)
    def setUp(self): self.temp,self.settings,self.db,self.provider,self.engine,self.auth=stack()
    def tearDown(self): self.engine.shutdown(); self.temp.cleanup()
    def test_failover_and_health(self):
        settings=replace(self.settings,providers=(ProviderConfig(name="primary",kind="mock",priority=1,models={"luna":"a","terra":"a","sol":"a"}),ProviderConfig(name="backup",kind="mock",priority=2,models={"luna":"b","terra":"b","sol":"b"}),),provider_circuit_failures=1)
        pool=ProviderPool(settings,self.db); pool.endpoints["primary"]=BadEndpoint(); pool.endpoints["backup"]=GoodEndpoint()
        result=pool.chat("terra",[{"role":"user","content":"x"}],[]); self.assertEqual(result.provider_name,"backup"); self.assertFalse(self.db.provider_available("primary"))
        health={x["name"]:x for x in self.db.list_provider_health()}; self.assertEqual(health["primary"]["failures"],1); self.assertEqual(health["backup"]["successes"],1)

if __name__=="__main__": unittest.main()
