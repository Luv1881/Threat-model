## Fix these first — top 10 of 46 still-at-risk findings

| # | Score | Severity | Finding | Asset | Source |
|--:|--:|---|---|---|---|
| 1 | 69 | high | Exposed Default Credentials: MinIO Object Storage is tagged as intentional-misconfiguration and stores confidential data | MinIO Object Storage | feature_datastores.yaml:146 |
| 2 | 66 | elevated | Lateral Movement via Shared Runtime on Docker Host: assets from 3 trust zones co-located | Nginx Reverse Proxy | feature_frontend.yaml:81 |
| 3 | 66 | elevated | Missing Authentication covering communication link Route to ECS API from AWS API Gateway to API Server | API Server | feature_api.yaml:55 |
| 4 | 66 | elevated | Missing Authentication covering communication link HTTP to API Server from Nginx Reverse Proxy to API Server | API Server | feature_api.yaml:55 |
| 5 | 66 | elevated | Missing Content-Security-Policy: Nginx Reverse Proxy serves browser clients handling auth tokens without a verified CSP header | Nginx Reverse Proxy | feature_frontend.yaml:81 |
| 6 | 66 | elevated | Missing Hardening risk at PostgreSQL Database | PostgreSQL Database | feature_datastores.yaml:59 |
| 7 | 66 | elevated | Path-Traversal risk at API Server against filesystem MinIO Object Storage via MinIO File Storage | API Server | feature_api.yaml:55 |
| 8 | 66 | elevated | Unencrypted Communication named MinIO File Storage between API Server and MinIO Object Storage transferring authentication data (like credentials, token, session-id, etc.) | API Server | feature_api.yaml:55 |
| 9 | 66 | elevated | Unencrypted Communication named PostgreSQL Connection between API Server and PostgreSQL Database transferring authentication data (like credentials, token, session-id, etc.) | API Server | feature_api.yaml:55 |
| 10 | 66 | elevated | Unencrypted Communication named Redis Session Store between API Server and Redis Cache transferring authentication data (like credentials, token, session-id, etc.) | API Server | feature_api.yaml:55 |

1. **Exposed Default Credentials: MinIO Object Storage is tagged as intentional-misconfiguration and stores confidential data** — Rotate all default credentials before deployment; store secrets in a secrets manager (CWE-1392, cheatsheet: https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
2. **Lateral Movement via Shared Runtime on Docker Host: assets from 3 trust zones co-located** — Runtime Isolation (cheatsheet: https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html)
3. **Missing Authentication covering communication link Route to ECS API from AWS API Gateway to API Server** — Authentication of Incoming Requests (CWE-306, cheatsheet: https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
4. **Missing Authentication covering communication link HTTP to API Server from Nginx Reverse Proxy to API Server** — Authentication of Incoming Requests (CWE-306, cheatsheet: https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
5. **Missing Content-Security-Policy: Nginx Reverse Proxy serves browser clients handling auth tokens without a verified CSP header** — Configure a Content-Security-Policy response header on the web entry point (CWE-693, cheatsheet: https://cheatsheetseries.owasp.org/cheatsheets/Content_Security_Policy_Cheat_Sheet.html)
6. **Missing Hardening risk at PostgreSQL Database** — System Hardening (CWE-16, cheatsheet: https://cheatsheetseries.owasp.org/cheatsheets/Attack_Surface_Analysis_Cheat_Sheet.html)
7. **Path-Traversal risk at API Server against filesystem MinIO Object Storage via MinIO File Storage** — Path-Traversal Prevention (CWE-22, cheatsheet: https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html)
8. **Unencrypted Communication named MinIO File Storage between API Server and MinIO Object Storage transferring authentication data (like credentials, token, session-id, etc.)** — Encryption of Communication Links (CWE-319, cheatsheet: https://cheatsheetseries.owasp.org/cheatsheets/Transport_Layer_Protection_Cheat_Sheet.html)
9. **Unencrypted Communication named PostgreSQL Connection between API Server and PostgreSQL Database transferring authentication data (like credentials, token, session-id, etc.)** — Encryption of Communication Links (CWE-319, cheatsheet: https://cheatsheetseries.owasp.org/cheatsheets/Transport_Layer_Protection_Cheat_Sheet.html)
10. **Unencrypted Communication named Redis Session Store between API Server and Redis Cache transferring authentication data (like credentials, token, session-id, etc.)** — Encryption of Communication Links (CWE-319, cheatsheet: https://cheatsheetseries.owasp.org/cheatsheets/Transport_Layer_Protection_Cheat_Sheet.html)
