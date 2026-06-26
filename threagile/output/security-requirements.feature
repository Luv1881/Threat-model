Feature: VaultNote Threat Model security requirements

  Scenario: Asset Using Known Default or Hardcoded Credentials
    # HIGH, CWE-1392
    Given the affected assets MinIO Object Storage are deployed
    Then Rotate all default credentials before deployment; store secrets in a secrets manager
    And it can be verified that Are all service credentials rotated from vendor defaults? Are secrets stored in a dedicated secrets manager rather than plain environment variables?

  Scenario: Lateral Movement via Shared Runtime
    # ELEVATED
    Given the affected assets Nginx Reverse Proxy are deployed
    Then Runtime Isolation
    And it can be verified that Are high-trust and low-trust assets co-located on the same shared runtime?

  Scenario: Missing Authentication
    # ELEVATED, CWE-306
    Given the affected assets API Server are deployed
    Then Authentication of Incoming Requests
    And it can be verified that Are recommendations from the linked cheat sheet and referenced ASVS chapter applied?

  Scenario: Missing Cloud Hardening
    # ELEVATED, CWE-1008
    Given the system is deployed
    Then Cloud Hardening
    And it can be verified that Are recommendations from the linked cheat sheet and referenced ASVS chapter applied?

  Scenario: Missing Content-Security-Policy Header on Web Entry Point
    # ELEVATED, CWE-693
    Given the affected assets Nginx Reverse Proxy are deployed
    Then Configure a Content-Security-Policy response header on the web entry point
    And it can be verified that Is a Content-Security-Policy response header present and non-trivial on all pages served to browsers? Use browser DevTools or securityheaders.com to verify.

  Scenario: Missing Hardening
    # ELEVATED, CWE-16
    Given the affected assets AWS RDS PostgreSQL, ECS Container Platform, PostgreSQL Database are deployed
    Then System Hardening
    And it can be verified that Are recommendations from the linked cheat sheet and referenced ASVS chapter applied?

  Scenario: Path-Traversal
    # ELEVATED, CWE-22
    Given the affected assets API Server, ECS Container Platform, GitHub Actions Build Pipeline are deployed
    Then Path-Traversal Prevention
    And it can be verified that Are recommendations from the linked cheat sheet and referenced ASVS chapter applied?

  Scenario: Unencrypted Communication
    # ELEVATED, CWE-319
    Given the affected assets API Server, Nginx Reverse Proxy are deployed
    Then Encryption of Communication Links
    And it can be verified that Are recommendations from the linked cheat sheet and referenced ASVS chapter applied?

  Scenario: Unguarded Access From Internet
    # ELEVATED, CWE-501
    Given the affected assets API Server are deployed
    Then Encapsulation of Technical Asset
    And it can be verified that Are recommendations from the linked cheat sheet and referenced ASVS chapter applied?

  Scenario: Accidental Secret Leak
    # MEDIUM, CWE-200
    Given the affected assets VaultNote Source Repository are deployed
    Then Build Pipeline Hardening
    And it can be verified that Are recommendations from the linked cheat sheet and referenced ASVS chapter applied?

  Scenario: Code Backdooring
    # MEDIUM, CWE-912
    Given the affected assets AWS ECR Container Registry, GitHub Actions Build Pipeline, VaultNote Source Repository are deployed
    Then Build Pipeline Hardening
    And it can be verified that Are recommendations from the linked cheat sheet and referenced ASVS chapter applied?

  Scenario: Container Base Image Backdooring
    # MEDIUM, CWE-912
    Given the affected assets API Server, MinIO Object Storage, Nginx Reverse Proxy, Note RAG Pipeline, PostgreSQL Database, Redis Cache, VaultNote Vector Store are deployed
    Then Container Infrastructure Hardening
    And it can be verified that Are recommendations from the linked cheat sheet and referenced ASVS/CSVS applied?

  Scenario: Container Platform Escape
    # MEDIUM, CWE-1008
    Given the affected assets ECS Container Platform are deployed
    Then Container Infrastructure Hardening
    And it can be verified that Are recommendations from the linked cheat sheet and referenced ASVS or CSVS chapter applied?

  Scenario: Missing Two-Factor Authentication (2FA)
    # MEDIUM, CWE-308
    Given the affected assets API Server are deployed
    Then Authentication with Second Factor (2FA)
    And it can be verified that Are recommendations from the linked cheat sheet and referenced ASVS chapter applied?

  Scenario: Missing Vault (Secret Storage)
    # MEDIUM, CWE-522
    Given the affected assets API Server are deployed
    Then Vault (Secret Storage)
    And it can be verified that Is there a Vault (Secret Storage) in place?

  Scenario: Missing Web Application Firewall (WAF)
    # MEDIUM, CWE-1008
    Given the affected assets API Server are deployed
    Then Web Application Firewall (WAF)
    And it can be verified that Is there a Web Application Firewall (WAF) in place?

  Scenario: Mixed Targets on Shared Runtime
    # MEDIUM, CWE-1008
    Given the system is deployed
    Then Runtime Separation
    And it can be verified that Are recommendations from the linked cheat sheet and referenced ASVS chapter applied?

  Scenario: Unchecked Deployment
    # MEDIUM, CWE-1127
    Given the affected assets AWS ECR Container Registry, GitHub Actions Build Pipeline, VaultNote Source Repository are deployed
    Then Build Pipeline Hardening
    And it can be verified that Are recommendations from the linked cheat sheet and referenced ASVS chapter applied?

  Scenario: Unencrypted Technical Assets
    # MEDIUM, CWE-311
    Given the affected assets AWS RDS PostgreSQL, AWS S3 Notes Bucket, MinIO Object Storage, PostgreSQL Database, Redis Cache are deployed
    Then Encryption of Technical Asset
    And it can be verified that Are recommendations from the linked cheat sheet and referenced ASVS chapter applied?

  Scenario: DoS-risky Access Across Trust-Boundary
    # LOW, CWE-400
    Given the affected assets API Server, Nginx Reverse Proxy, PostgreSQL Database are deployed
    Then Anti-DoS Measures
    And it can be verified that Are recommendations from the linked cheat sheet and referenced ASVS chapter applied?

