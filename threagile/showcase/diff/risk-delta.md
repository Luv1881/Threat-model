## Threat-model risk delta

`threagile.yaml` → `threagile.yaml` · methodology: **stride**

**+7 added, −0 resolved, ~0 changed, =60 unchanged**

### ❌ 7 new risk(s)

| Severity | Risk |
|----------|------|
| Medium | `container-baseimage-backdooring@rag-pipeline` |
| Medium | `container-baseimage-backdooring@vector-store` |
| Medium | `server-side-request-forgery@llm-summarizer@rag-pipeline@llm-summarizer>call-rag-pipeline` |
| Medium | `server-side-request-forgery@llm-summarizer@vector-store@llm-summarizer>query-vector-store` |
| Medium | `server-side-request-forgery@rag-pipeline@vector-store@rag-pipeline>retrieve-from-vector-store` |
| Medium | `unguarded-access-from-internet@rag-pipeline@llm-summarizer@llm-summarizer>call-rag-pipeline` |
| Medium | `unguarded-access-from-internet@vector-store@llm-summarizer@llm-summarizer>query-vector-store` |

**How to fix the new findings:**

- **Container Base Image Backdooring** — Container Infrastructure Hardening (CWE-912, cheatsheet: https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html)
- **Server-Side Request Forgery (SSRF)** — SSRF Prevention (CWE-918, cheatsheet: https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html)
- **Unguarded Access From Internet** — Encapsulation of Technical Asset (CWE-501, cheatsheet: https://cheatsheetseries.owasp.org/cheatsheets/Attack_Surface_Analysis_Cheat_Sheet.html)
