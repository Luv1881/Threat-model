# ──────────────────────────────────────────────────────────────────────────────
# S3 — maps to the MinIO object-storage service in docker-compose.yml
#   * Stores file attachments (binary uploads linked to notes)
#   * Intentional misconfiguration mirrored: server-side encryption disabled
#   * Public access explicitly blocked — mirrors backend-net internal: true
# ──────────────────────────────────────────────────────────────────────────────

resource "aws_s3_bucket" "attachments" {
  bucket = "vaultnote-attachments-${var.environment}"

  tags = {
    Name                        = "vaultnote-attachments"
    TrustBoundary               = "data-tier"
    IriusRiskComponent          = "object-storage"
    IntentionalMisconfiguration = "no-encryption-at-rest"
  }
}

resource "aws_s3_bucket_public_access_block" "attachments" {
  bucket = aws_s3_bucket.attachments.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ── INTENTIONAL MISCONFIGURATION: server-side encryption is NOT enabled ───────
# This mirrors the MinIO default in docker-compose (no SSE-S3).
# In production, replace with an aws_s3_bucket_server_side_encryption_configuration
# resource using AES-256 or KMS.

resource "aws_s3_bucket_versioning" "attachments" {
  bucket = aws_s3_bucket.attachments.id

  versioning_configuration {
    status = "Disabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "attachments" {
  bucket = aws_s3_bucket.attachments.id

  rule {
    id     = "expire-old-uploads"
    status = "Enabled"

    filter {}

    expiration {
      days = 365
    }
  }
}

# ── VPC Endpoint for S3 (private routing — no NAT needed for S3 calls) ───────

resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.vaultnote.id
  service_name      = "com.amazonaws.${var.aws_region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = aws_route_table.private[*].id

  tags = {
    Name          = "vaultnote-s3-endpoint"
    TrustBoundary = "data-tier"
  }
}
