# ──────────────────────────────────────────────────────────────────────────────
# VPC — mirrors the Docker Compose network isolation
#   public  subnets  → "DMZ"            (nginx-proxy / ALB)
#   private subnets  → "Data Tier"      (RDS, ElastiCache, S3 VPC endpoint)
#   app     subnets  → "App Network"    (ECS API tasks)
# ──────────────────────────────────────────────────────────────────────────────

resource "aws_vpc" "vaultnote" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = {
    Name           = "vaultnote-vpc"
    TrustBoundary  = "vpc-root"
    IriusRiskComponent = "vpc"
  }
}

# ── Public subnets (DMZ — ALB lives here) ────────────────────────────────────

resource "aws_subnet" "public" {
  count             = length(var.availability_zones)
  vpc_id            = aws_vpc.vaultnote.id
  cidr_block        = var.public_subnet_cidrs[count.index]
  availability_zone = var.availability_zones[count.index]

  map_public_ip_on_launch = true

  tags = {
    Name          = "vaultnote-public-${var.availability_zones[count.index]}"
    TrustBoundary = "dmz"
    Tier          = "public"
  }
}

# ── Private subnets (Data Tier — RDS, ElastiCache) ───────────────────────────

resource "aws_subnet" "private" {
  count             = length(var.availability_zones)
  vpc_id            = aws_vpc.vaultnote.id
  cidr_block        = var.private_subnet_cidrs[count.index]
  availability_zone = var.availability_zones[count.index]

  map_public_ip_on_launch = false

  tags = {
    Name          = "vaultnote-private-${var.availability_zones[count.index]}"
    TrustBoundary = "data-tier"
    Tier          = "private"
  }
}

# ── Internet Gateway ──────────────────────────────────────────────────────────

resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.vaultnote.id

  tags = { Name = "vaultnote-igw" }
}

# ── NAT Gateway (one per public subnet for HA) ───────────────────────────────

resource "aws_eip" "nat" {
  count  = length(var.availability_zones)
  domain = "vpc"

  tags = { Name = "vaultnote-nat-eip-${count.index}" }
}

resource "aws_nat_gateway" "nat" {
  count         = length(var.availability_zones)
  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id

  tags = { Name = "vaultnote-nat-${count.index}" }

  depends_on = [aws_internet_gateway.igw]
}

# ── Route tables ──────────────────────────────────────────────────────────────

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.vaultnote.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id
  }

  tags = { Name = "vaultnote-rt-public" }
}

resource "aws_route_table_association" "public" {
  count          = length(var.availability_zones)
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table" "private" {
  count  = length(var.availability_zones)
  vpc_id = aws_vpc.vaultnote.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.nat[count.index].id
  }

  tags = { Name = "vaultnote-rt-private-${count.index}" }
}

resource "aws_route_table_association" "private" {
  count          = length(var.availability_zones)
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private[count.index].id
}

# ── Security Groups ───────────────────────────────────────────────────────────

# ALB (public-facing — maps to Nginx DMZ role)
resource "aws_security_group" "alb" {
  name        = "vaultnote-alb-sg"
  description = "Allow HTTPS/HTTP inbound from the internet to the ALB"
  vpc_id      = aws_vpc.vaultnote.id

  ingress {
    description = "HTTPS from internet"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTP redirect only"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name              = "vaultnote-alb-sg"
    TrustBoundary     = "dmz"
    IriusRiskComponent = "load-balancer"
  }
}

# ECS API tasks (application tier)
resource "aws_security_group" "api" {
  name        = "vaultnote-api-sg"
  description = "Allow inbound from ALB only; egress to data tier"
  vpc_id      = aws_vpc.vaultnote.id

  ingress {
    description     = "HTTP from ALB (intentional plain HTTP — mirrors docker-compose misconfiguration)"
    from_port       = 3000
    to_port         = 3000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name              = "vaultnote-api-sg"
    TrustBoundary     = "application-network"
    IriusRiskComponent = "web-service"
  }
}

# RDS PostgreSQL (data tier)
resource "aws_security_group" "rds" {
  name        = "vaultnote-rds-sg"
  description = "Allow PostgreSQL from API tier only"
  vpc_id      = aws_vpc.vaultnote.id

  ingress {
    description     = "PostgreSQL from API"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.api.id]
  }

  tags = {
    Name              = "vaultnote-rds-sg"
    TrustBoundary     = "data-tier"
    IriusRiskComponent = "database"
  }
}

# ElastiCache Redis (data tier)
resource "aws_security_group" "redis" {
  name        = "vaultnote-redis-sg"
  description = "Allow Redis from API tier only"
  vpc_id      = aws_vpc.vaultnote.id

  ingress {
    description     = "Redis from API"
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.api.id]
  }

  tags = {
    Name              = "vaultnote-redis-sg"
    TrustBoundary     = "data-tier"
    IriusRiskComponent = "cache"
  }
}
