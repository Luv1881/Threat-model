# ──────────────────────────────────────────────────────────────────────────────
# ECS Fargate — maps to the API container in docker-compose.yml
#   Node.js/Express bridging frontend-net and backend-net
# ──────────────────────────────────────────────────────────────────────────────

resource "aws_ecs_cluster" "vaultnote" {
  name = "vaultnote"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = {
    Name              = "vaultnote-cluster"
    IriusRiskComponent = "container-runtime"
  }
}

resource "aws_ecs_cluster_capacity_providers" "vaultnote" {
  cluster_name       = aws_ecs_cluster.vaultnote.name
  capacity_providers = ["FARGATE", "FARGATE_SPOT"]

  default_capacity_provider_strategy {
    capacity_provider = "FARGATE"
    weight            = 1
  }
}

# ── CloudWatch log group ──────────────────────────────────────────────────────

resource "aws_cloudwatch_log_group" "api" {
  name              = "/ecs/vaultnote-api"
  retention_in_days = 14

  tags = { Name = "vaultnote-api-logs" }
}

# ── IAM execution role ────────────────────────────────────────────────────────

resource "aws_iam_role" "ecs_execution" {
  name = "vaultnote-ecs-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  tags = { Name = "vaultnote-ecs-execution-role" }
}

resource "aws_iam_role_policy_attachment" "ecs_execution" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# ── IAM task role (grants S3 access for file attachments) ────────────────────

resource "aws_iam_role" "ecs_task" {
  name = "vaultnote-ecs-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  tags = { Name = "vaultnote-ecs-task-role" }
}

resource "aws_iam_role_policy" "api_s3" {
  name = "vaultnote-api-s3-policy"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "FileAttachmentsReadWrite"
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.attachments.arn,
          "${aws_s3_bucket.attachments.arn}/*"
        ]
      },
      {
        Sid    = "SecretsManagerRead"
        Effect = "Allow"
        Action = ["secretsmanager:GetSecretValue"]
        Resource = [
          aws_secretsmanager_secret.db_password.arn,
          aws_secretsmanager_secret.jwt_secret.arn,
          aws_secretsmanager_secret.redis_token.arn,
        ]
      }
    ]
  })
}

# ── Task definition ───────────────────────────────────────────────────────────

resource "aws_ecs_task_definition" "api" {
  family                   = "vaultnote-api"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.api_cpu
  memory                   = var.api_memory
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name      = "api"
      image     = var.api_image
      essential = true

      portMappings = [
        {
          containerPort = 3000
          protocol      = "tcp"
        }
      ]

      environment = [
        { name = "NODE_ENV",       value = var.environment },
        { name = "MINIO_ENDPOINT", value = aws_s3_bucket.attachments.bucket_regional_domain_name },
        { name = "MINIO_PORT",     value = "443" }
      ]

      secrets = [
        { name = "DATABASE_URL", valueFrom = aws_secretsmanager_secret.db_url.arn },
        { name = "REDIS_URL",    valueFrom = aws_secretsmanager_secret.redis_url.arn },
        { name = "JWT_SECRET",   valueFrom = aws_secretsmanager_secret.jwt_secret.arn }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.api.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "api"
        }
      }

      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:3000/health || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60
      }
    }
  ])

  tags = {
    Name              = "vaultnote-api-task"
    TrustBoundary     = "application-network"
    IriusRiskComponent = "web-service"
  }
}

# ── ECS Service ───────────────────────────────────────────────────────────────

resource "aws_ecs_service" "api" {
  name            = "vaultnote-api"
  cluster         = aws_ecs_cluster.vaultnote.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = var.api_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.api.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.api.arn
    container_name   = "api"
    container_port   = 3000
  }

  depends_on = [
    aws_lb_listener.https,
    aws_iam_role_policy_attachment.ecs_execution
  ]

  tags = {
    Name          = "vaultnote-api-service"
    TrustBoundary = "application-network"
  }
}
