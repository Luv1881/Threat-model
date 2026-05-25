# ──────────────────────────────────────────────────────────────────────────────
# Application Load Balancer — maps to the Nginx reverse proxy
#   * Terminates TLS (mirrors nginx ssl_certificate)
#   * Forwards to API target group over HTTP (mirrors intentional misconfiguration)
#   * HTTP → HTTPS redirect on port 80
# ──────────────────────────────────────────────────────────────────────────────

resource "aws_lb" "vaultnote" {
  name               = "vaultnote-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = aws_subnet.public[*].id

  enable_deletion_protection = false

  tags = {
    Name              = "vaultnote-alb"
    TrustBoundary     = "dmz"
    IriusRiskComponent = "reverse-proxy"
  }
}

# ── HTTPS listener (TLS termination) ─────────────────────────────────────────

resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.vaultnote.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = var.certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }
}

# ── HTTP → HTTPS redirect ─────────────────────────────────────────────────────

resource "aws_lb_listener" "http_redirect" {
  load_balancer_arn = aws_lb.vaultnote.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type = "redirect"
    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}

# ── Target group (API tasks — plain HTTP, mirroring docker-compose) ───────────

resource "aws_lb_target_group" "api" {
  name        = "vaultnote-api-tg"
  port        = 3000
  protocol    = "HTTP"
  vpc_id      = aws_vpc.vaultnote.id
  target_type = "ip"

  health_check {
    path                = "/health"
    protocol            = "HTTP"
    matcher             = "200"
    interval            = 30
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }

  tags = {
    Name          = "vaultnote-api-tg"
    TrustBoundary = "application-network"
  }
}
