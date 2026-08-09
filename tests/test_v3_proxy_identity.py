import hashlib,hmac,time,unittest
from common import stack
from zworkforce.security import AuthManager

class ProxyIdentityTests(unittest.TestCase):
    def setUp(self): self.temp,self.settings,self.db,self.provider,self.engine,_=stack();self.auth=AuthManager(self.db,trust_proxy_identity=True,proxy_identity_secret="x"*32)
    def tearDown(self): self.engine.shutdown();self.temp.cleanup()
    def test_scopes_are_covered_by_signature(self):
        ts=str(int(time.time()));name="alice";role="operator";tenant="default";scopes="workforce:read"
        material=f"{name}\n{role}\n{tenant}\n{scopes}\n{ts}".encode();sig=hmac.new(("x"*32).encode(),material,hashlib.sha256).hexdigest()
        headers={"X-Forwarded-User":name,"X-Forwarded-Role":role,"X-Forwarded-Tenant":tenant,"X-Forwarded-Scopes":scopes,"X-ZWorkforce-Proxy-Signature":sig,"X-ZWorkforce-Proxy-Timestamp":ts}
        self.assertIsNotNone(self.auth.authenticate(None,None,headers))
        headers["X-Forwarded-Scopes"]="*"
        self.assertIsNone(self.auth.authenticate(None,None,headers))
if __name__=="__main__":unittest.main()
