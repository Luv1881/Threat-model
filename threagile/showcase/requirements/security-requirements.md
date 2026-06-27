# Security requirements (20)

- [ ] **Asset Using Known Default or Hardcoded Credentials** — Rotate all default credentials before deployment; store secrets in a secrets manager _(HIGH, CWE-1392)_
      Affects: MinIO Object Storage
      Verify: Are all service credentials rotated from vendor defaults? Are secrets stored in a dedicated secrets manager rather than plain environment variables?
- [ ] **Lateral Movement via Shared Runtime** — Runtime Isolation _(ELEVATED)_
      Affects: Nginx Reverse Proxy
      Verify: Are high-trust and low-trust assets co-located on the same shared runtime?
- [ ] **Missing Authentication** — Authentication of Incoming Requests _(ELEVATED, CWE-306, 2 findings)_
      Affects: API Server
      Verify: Are recommendations from the linked cheat sheet and referenced ASVS chapter applied?
- [ ] **Missing Cloud Hardening** — Cloud Hardening _(ELEVATED, CWE-1008, 3 findings)_
      Verify: Are recommendations from the linked cheat sheet and referenced ASVS chapter applied?
- [ ] **Missing Content-Security-Policy Header on Web Entry Point** — Configure a Content-Security-Policy response header on the web entry point _(ELEVATED, CWE-693)_
      Affects: Nginx Reverse Proxy
      Verify: Is a Content-Security-Policy response header present and non-trivial on all pages served to browsers? Use browser DevTools or securityheaders.com to verify.
- [ ] **Missing Hardening** — System Hardening _(ELEVATED, CWE-16, 3 findings)_
      Affects: AWS RDS PostgreSQL, ECS Container Platform, PostgreSQL Database
      Verify: Are recommendations from the linked cheat sheet and referenced ASVS chapter applied?
- [ ] **Path-Traversal** — Path-Traversal Prevention _(ELEVATED, CWE-22, 3 findings)_
      Affects: API Server, ECS Container Platform, GitHub Actions Build Pipeline
      Verify: Are recommendations from the linked cheat sheet and referenced ASVS chapter applied?
- [ ] **Unencrypted Communication** — Encryption of Communication Links _(ELEVATED, CWE-319, 4 findings)_
      Affects: API Server, Nginx Reverse Proxy
      Verify: Are recommendations from the linked cheat sheet and referenced ASVS chapter applied?
- [ ] **Unguarded Access From Internet** — Encapsulation of Technical Asset _(ELEVATED, CWE-501)_
      Affects: API Server
      Verify: Are recommendations from the linked cheat sheet and referenced ASVS chapter applied?
- [ ] **Accidental Secret Leak** — Build Pipeline Hardening _(MEDIUM, CWE-200)_
      Affects: VaultNote Source Repository
      Verify: Are recommendations from the linked cheat sheet and referenced ASVS chapter applied?
- [ ] **Code Backdooring** — Build Pipeline Hardening _(MEDIUM, CWE-912, 3 findings)_
      Affects: AWS ECR Container Registry, GitHub Actions Build Pipeline, VaultNote Source Repository
      Verify: Are recommendations from the linked cheat sheet and referenced ASVS chapter applied?
- [ ] **Container Base Image Backdooring** — Container Infrastructure Hardening _(MEDIUM, CWE-912, 7 findings)_
      Affects: API Server, MinIO Object Storage, Nginx Reverse Proxy, Note RAG Pipeline, PostgreSQL Database, Redis Cache, VaultNote Vector Store
      Verify: Are recommendations from the linked cheat sheet and referenced ASVS/CSVS applied?
- [ ] **Container Platform Escape** — Container Infrastructure Hardening _(MEDIUM, CWE-1008)_
      Affects: ECS Container Platform
      Verify: Are recommendations from the linked cheat sheet and referenced ASVS or CSVS chapter applied?
- [ ] **Missing Two-Factor Authentication (2FA)** — Authentication with Second Factor (2FA) _(MEDIUM, CWE-308)_
      Affects: API Server
      Verify: Are recommendations from the linked cheat sheet and referenced ASVS chapter applied?
- [ ] **Missing Vault (Secret Storage)** — Vault (Secret Storage) _(MEDIUM, CWE-522)_
      Affects: API Server
      Verify: Is there a Vault (Secret Storage) in place?
- [ ] **Missing Web Application Firewall (WAF)** — Web Application Firewall (WAF) _(MEDIUM, CWE-1008)_
      Affects: API Server
      Verify: Is there a Web Application Firewall (WAF) in place?
- [ ] **Mixed Targets on Shared Runtime** — Runtime Separation _(MEDIUM, CWE-1008)_
      Verify: Are recommendations from the linked cheat sheet and referenced ASVS chapter applied?
- [ ] **Unchecked Deployment** — Build Pipeline Hardening _(MEDIUM, CWE-1127, 3 findings)_
      Affects: AWS ECR Container Registry, GitHub Actions Build Pipeline, VaultNote Source Repository
      Verify: Are recommendations from the linked cheat sheet and referenced ASVS chapter applied?
- [ ] **Unencrypted Technical Assets** — Encryption of Technical Asset _(MEDIUM, CWE-311, 5 findings)_
      Affects: AWS RDS PostgreSQL, AWS S3 Notes Bucket, MinIO Object Storage, PostgreSQL Database, Redis Cache
      Verify: Are recommendations from the linked cheat sheet and referenced ASVS chapter applied?
- [ ] **DoS-risky Access Across Trust-Boundary** — Anti-DoS Measures _(LOW, CWE-400, 3 findings)_
      Affects: API Server, Nginx Reverse Proxy, PostgreSQL Database
      Verify: Are recommendations from the linked cheat sheet and referenced ASVS chapter applied?
