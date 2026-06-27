## Threat-model gate — ❌ **FAIL**

_Policy: Strict gate_

Findings still at risk: **46** (1 high, 17 elevated, 24 medium, 4 low)

### 2 policy violation(s)

| Rule | Detail |
|------|--------|
| `max_severity_counts` | 1 high finding(s) still at risk, policy allows at most 0<br>offending: exposed-default-credentials@minio-storage |
| `max_severity_counts` | 17 elevated finding(s) still at risk, policy allows at most 0<br>offending: lateral-movement-shared-runtime@docker-host, missing-authentication@aws-api-gateway>route-to-ecs-api@aws-api-gateway@api-server, missing-authentication@nginx-proxy>http-to-api-server@nginx-proxy@api-server, missing-cloud-hardening@aws-cloud@aws, missing-cloud-hardening@docker-host, missing-csp-header@nginx-proxy, missing-hardening@ecs-platform, missing-hardening@postgresql-db, missing-hardening@rds-postgresql, path-traversal@api-server@minio-storage@api-server>minio-file-storage, path-traversal@build-pipeline@container-registry@build-pipeline>push-image-to-registry, path-traversal@ecs-platform@container-registry@ecs-platform>pull-images-from-ecr, unencrypted-communication@api-server>minio-file-storage@api-server@minio-storage, unencrypted-communication@api-server>postgresql-connection@api-server@postgresql-db, unencrypted-communication@api-server>redis-session-store@api-server@redis-cache (+2 more) |
