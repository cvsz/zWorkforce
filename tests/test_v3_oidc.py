import json
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

from zworkforce.identity import OidcAuthenticator, OidcConfig


class OidcTests(unittest.TestCase):
    def setUp(self):
        self.private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(self.private.public_key()))
        jwk["kid"] = "test-key"
        self.jwks = {"keys": [jwk]}
        parent = self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*_): pass
            def do_GET(self):
                if self.path == "/.well-known/openid-configuration":
                    body={"issuer":parent.issuer,"jwks_uri":parent.issuer+"/jwks","id_token_signing_alg_values_supported":["RS256"]}
                elif self.path == "/jwks": body=parent.jwks
                else: self.send_response(404);self.end_headers();return
                raw=json.dumps(body).encode();self.send_response(200);self.send_header("Content-Type","application/json");self.send_header("Content-Length",str(len(raw)));self.end_headers();self.wfile.write(raw)
        self.server=ThreadingHTTPServer(("127.0.0.1",0),Handler)
        self.issuer=f"http://127.0.0.1:{self.server.server_address[1]}"
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
    def tearDown(self): self.server.shutdown();self.server.server_close()
    def test_valid_oidc_and_group_role_mapping(self):
        now=int(time.time())
        token=jwt.encode({"iss":self.issuer,"aud":"zworkforce","iat":now,"exp":now+300,"sub":"u1","tenant":"acme","role":"viewer","groups":["admins"],"scope":"workforce:read task:write","preferred_username":"alice"},self.private,algorithm="RS256",headers={"kid":"test-key"})
        auth=OidcAuthenticator(OidcConfig(self.issuer,"zworkforce",group_role_map={"admins":"admin"}))
        p=auth.authenticate(token)
        self.assertIsNotNone(p);self.assertEqual(p.tenant_id,"acme");self.assertEqual(p.role,"admin");self.assertIn("task:write",p.scopes)
    def test_wrong_audience_rejected(self):
        now=int(time.time())
        token=jwt.encode({"iss":self.issuer,"aud":"other","iat":now,"exp":now+300,"sub":"u1"},self.private,algorithm="RS256",headers={"kid":"test-key"})
        self.assertIsNone(OidcAuthenticator(OidcConfig(self.issuer,"zworkforce")).authenticate(token))

if __name__=="__main__": unittest.main()
