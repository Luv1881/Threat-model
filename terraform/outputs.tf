output "alb_dns_name" {
  description = "DNS name of the Application Load Balancer (entry point)"
  value       = aws_lb.vaultnote.dns_name
}

output "alb_zone_id" {
  description = "Route 53 hosted zone ID of the ALB (for alias records)"
  value       = aws_lb.vaultnote.zone_id
}

output "vpc_id" {
  description = "ID of the VaultNote VPC"
  value       = aws_vpc.vaultnote.id
}

output "public_subnet_ids" {
  description = "IDs of public (DMZ) subnets"
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "IDs of private (data-tier) subnets"
  value       = aws_subnet.private[*].id
}

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = aws_ecs_cluster.vaultnote.name
}

output "rds_endpoint" {
  description = "PostgreSQL RDS endpoint (host:port)"
  value       = aws_db_instance.postgresql.endpoint
  sensitive   = true
}

output "redis_primary_endpoint" {
  description = "ElastiCache Redis primary endpoint"
  value       = aws_elasticache_replication_group.redis.primary_endpoint_address
  sensitive   = true
}

output "s3_attachments_bucket" {
  description = "S3 bucket name for file attachments"
  value       = aws_s3_bucket.attachments.bucket
}

output "db_url_secret_arn" {
  description = "Secrets Manager ARN for the DATABASE_URL"
  value       = aws_secretsmanager_secret.db_url.arn
}
