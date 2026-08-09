# Identity

## API keys
Persistent API keys support viewer/operator/admin/superadmin roles and scopes. Only the digest is stored.

## Native OIDC

```env
ZWORKFORCE_OIDC_ISSUER=https://id.example.com
ZWORKFORCE_OIDC_AUDIENCE=zworkforce
ZWORKFORCE_OIDC_TENANT_CLAIM=tenant
ZWORKFORCE_OIDC_ROLE_CLAIM=role
ZWORKFORCE_OIDC_SCOPES_CLAIM=scope
ZWORKFORCE_OIDC_NAME_CLAIM=preferred_username
ZWORKFORCE_OIDC_GROUP_ROLE_MAP={"workforce-admins":"admin"}
```

The authenticator discovers JWKS, verifies asymmetric signatures, issuer, audience, expiration and issued-at claims, then maps tenant/role/scopes/name.

## SAML

zWorkforce deliberately does not implement a custom SAML XML/signature stack. Terminate SAML at a mature IdP, access proxy or identity broker and use either OIDC downstream or the signed proxy identity boundary.

The signed proxy boundary binds user, role, tenant and timestamp with HMAC and rejects stale signatures.
