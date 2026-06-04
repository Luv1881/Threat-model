# ──────────────────────────────────────────────────────────────────────────────
# AWS Secrets Manager — replaces hardcoded credentials in docker-compose.yml
#   DB password, Redis auth token, JWT secret, and connection URL strings
# ──────────────────────────────────────────────────────────────────────────────

resource "aws_secretsmanager_secret" "db_password" {
  name                    = "vaultnote/${var.environment}/db-password"
  recovery_window_in_days = 0

  tags = { Name = "vaultnote-db-password" }
}

resource "aws_secretsmanager_secret_version" "db_password" {
  secret_id     = aws_secretsmanager_secret.db_password.id
  secret_string = var.db_password
}

resource "aws_secretsmanager_secret" "jwt_secret" {
  name                    = "vaultnote/${var.environment}/jwt-secret"
  recovery_window_in_days = 0

  tags = { Name = "vaultnote-jwt-secret" }
}

resource "aws_secretsmanager_secret_version" "jwt_secret" {
  secret_id     = aws_secretsmanager_secret.jwt_secret.id
  secret_string = var.jwt_secret
}

resource "aws_secretsmanager_secret" "redis_token" {
  name                    = "vaultnote/${var.environment}/redis-auth-token"
  recovery_window_in_days = 0

  tags = { Name = "vaultnote-redis-auth-token" }
}

resource "aws_secretsmanager_secret_version" "redis_token" {
  secret_id     = aws_secretsmanager_secret.redis_token.id
  secret_string = var.redis_auth_token
}

# ── Connection URL secrets (injected as env vars into ECS task) ───────────────

resource "aws_secretsmanager_secret" "db_url" {
  name                    = "vaultnote/${var.environment}/db-url"
  recovery_window_in_days = 0

  tags = { Name = "vaultnote-db-url" }
}

resource "aws_secretsmanager_secret_version" "db_url" {
  secret_id = aws_secretsmanager_secret.db_url.id
  secret_string = "postgresql://${var.db_username}:${var.db_password}@${aws_db_instance.postgresql.endpoint}/vaultnote"
}

resource "aws_secretsmanager_secret" "redis_url" {
  name                    = "vaultnote/${var.environment}/redis-url"
  recovery_window_in_days = 0

  tags = { Name = "vaultnote-redis-url" }
}

resource "aws_secretsmanager_secret_version" "redis_url" {
  secret_id = aws_secretsmanager_secret.redis_url.id
  secret_string = "redis://:${var.redis_auth_token}@${aws_elasticache_replication_group.redis.primary_endpoint_address}:6379"
}
