# Threat-model summary: VaultNote Threat Model

**Score: 81/100 (grade B)** · completeness 99% · posture 69% · 46 still at risk

## Fix these first — top 5 of 46 still-at-risk findings

| # | Score | Severity | Finding | Asset |
|--:|--:|---|---|---|
| 1 | 69 | high | Exposed Default Credentials: MinIO Object Storage is tagged as intentional-misconfiguration and stores confidential data | MinIO Object Storage |
| 2 | 66 | elevated | Lateral Movement via Shared Runtime on Docker Host: assets from 3 trust zones co-located | Nginx Reverse Proxy |
| 3 | 66 | elevated | Missing Authentication covering communication link Route to ECS API from AWS API Gateway to API Server | API Server |
| 4 | 66 | elevated | Missing Authentication covering communication link HTTP to API Server from Nginx Reverse Proxy to API Server | API Server |
| 5 | 66 | elevated | Missing Content-Security-Policy: Nginx Reverse Proxy serves browser clients handling auth tokens without a verified CSP header | Nginx Reverse Proxy |

1. **Exposed Default Credentials: MinIO Object Storage is tagged as intentional-misconfiguration and stores confidential data** — Rotate all default credentials before deployment; store secrets in a secrets manager (CWE-1392, cheatsheet: https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
2. **Lateral Movement via Shared Runtime on Docker Host: assets from 3 trust zones co-located** — Runtime Isolation (cheatsheet: https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html)
3. **Missing Authentication covering communication link Route to ECS API from AWS API Gateway to API Server** — Authentication of Incoming Requests (CWE-306, cheatsheet: https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
4. **Missing Authentication covering communication link HTTP to API Server from Nginx Reverse Proxy to API Server** — Authentication of Incoming Requests (CWE-306, cheatsheet: https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
5. **Missing Content-Security-Policy: Nginx Reverse Proxy serves browser clients handling auth tokens without a verified CSP header** — Configure a Content-Security-Policy response header on the web entry point (CWE-693, cheatsheet: https://cheatsheetseries.owasp.org/cheatsheets/Content_Security_Policy_Cheat_Sheet.html)
