# ──────────────────────────────────────────────────────────────────────────────
# ElastiCache Redis — maps to the redis:7-alpine service in docker-compose.yml
#   * Password-protected (auth token) — mirrors requirepass
#   * Intentional misconfiguration mirrored: at_rest_encryption_enabled = false
#   * Sits in the private (data-tier) subnets
# ──────────────────────────────────────────────────────────────────────────────

resource "aws_elasticache_subnet_group" "vaultnote" {
  name       = "vaultnote-redis-subnet-group"
  subnet_ids = aws_subnet.private[*].id

  tags = {
    Name          = "vaultnote-redis-subnet-group"
    TrustBoundary = "data-tier"
  }
}

resource "aws_elasticache_replication_group" "redis" {
  replication_group_id = "vaultnote-redis"
  description          = "Session store and JWT revocation list for VaultNote API"

  node_type            = var.redis_node_type
  num_cache_clusters   = 1
  engine               = "redis"
  engine_version       = "7.2"
  port                 = 6379

  subnet_group_name  = aws_elasticache_subnet_group.vaultnote.name
  security_group_ids = [aws_security_group.redis.id]

  auth_token                 = var.redis_auth_token
  transit_encryption_enabled = true

  # ── INTENTIONAL MISCONFIGURATION (mirrors threagile.yaml encryption: none) ──
  at_rest_encryption_enabled = false

  auto_minor_version_upgrade = true
  automatic_failover_enabled = false

  tags = {
    Name                        = "vaultnote-redis"
    TrustBoundary               = "data-tier"
    IriusRiskComponent          = "cache"
    IntentionalMisconfiguration = "no-encryption-at-rest"
  }
}
