# ──────────────────────────────────────────────────────────────────────────────
# RDS PostgreSQL — maps to the postgres:16-alpine service in docker-compose.yml
#   * Intentional misconfiguration mirrored: storage_encrypted = false
#   * Sits in the private (data-tier) subnets — mirrors backend-net internal:true
# ──────────────────────────────────────────────────────────────────────────────

resource "aws_db_subnet_group" "vaultnote" {
  name       = "vaultnote-db-subnet-group"
  subnet_ids = aws_subnet.private[*].id

  tags = {
    Name          = "vaultnote-db-subnet-group"
    TrustBoundary = "data-tier"
  }
}

resource "aws_db_instance" "postgresql" {
  identifier        = "vaultnote-postgresql"
  engine            = "postgres"
  engine_version    = "16.3"
  instance_class    = var.db_instance_class
  allocated_storage = 20
  storage_type      = "gp3"

  db_name  = "vaultnote"
  username = var.db_username
  password = var.db_password

  db_subnet_group_name   = aws_db_subnet_group.vaultnote.name
  vpc_security_group_ids = [aws_security_group.rds.id]

  # ── INTENTIONAL MISCONFIGURATION (mirrors threagile.yaml encryption: none) ──
  storage_encrypted = false

  backup_retention_period = 7
  deletion_protection     = false
  skip_final_snapshot     = true
  multi_az                = false
  publicly_accessible     = false

  # No performance insights to keep cost low in demo
  performance_insights_enabled = false

  tags = {
    Name                   = "vaultnote-postgresql"
    TrustBoundary          = "data-tier"
    IriusRiskComponent     = "database"
    IntentionalMisconfiguration = "no-encryption-at-rest"
  }
}
