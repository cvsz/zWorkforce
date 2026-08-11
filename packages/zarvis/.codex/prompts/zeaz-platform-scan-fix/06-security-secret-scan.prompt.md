# ZEAZ Security and Secret Hygiene Scan

## Language and Coding Standards
- **Communication**: Always talk in Thai when interacting with users.
- **Code & Technical Assets**: All code, comments, documentation, and technical definitions must be in English.

Goal:
Detect accidental sensitive files or risky tracked changes before commit/push.

Do not print secret values.
Do not open secret files unless only checking filename/path metadata.
Do not commit secrets.

Scan:
- .env
- .env.*
- secrets/
- secret/
- credentials/
- token/
- tokens/
- *.pem
- *.key
- *.p12
- *.pfx
- *.tfvars
- *.tfstate
- creds.json
- credentials.json
- .wrangler/
- .cloudflared/
- .kube/
- .ssh/
- .gnupg/

Use:
- git status --short
- git ls-files
- git diff --name-only
- git diff --cached --name-only

If risky files are untracked:
- leave them untracked
- add safe ignore rules if appropriate

If risky files are tracked:
- report path only
- recommend rotation if real secret was committed
- do not display secret contents

Output:
- Safe/unsafe file list by path only
- Recommended gitignore patch
- No secret values
