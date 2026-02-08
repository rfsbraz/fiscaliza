# Application Load Balancer for ECS Fargate
# Provides stable DNS endpoint for CloudFlare
# Cost: ~$16-18/month

# ALB Security Group
resource "aws_security_group" "alb" {
  count = var.enable_alb ? 1 : 0

  name_prefix = "${local.name_prefix}-alb-"
  vpc_id      = aws_vpc.main.id
  description = "Security group for Application Load Balancer"

  # Allow HTTP from anywhere (for HTTP to HTTPS redirect)
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow HTTP from anywhere for HTTPS redirect"
  }

  # Allow HTTPS from anywhere (CloudFlare proxy disabled)
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow HTTPS from anywhere"
  }

  # Allow all outbound traffic
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound traffic"
  }

  tags = merge(local.network_tags, {
    Name         = "${local.name_prefix}-alb-sg"
    ResourceType = "security-group"
    Purpose      = "alb-traffic-control"
  })

  lifecycle {
    create_before_destroy = true
  }
}

# Application Load Balancer
resource "aws_lb" "main" {
  count = var.enable_alb ? 1 : 0

  name               = "${local.name_prefix}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb[0].id]
  subnets            = aws_subnet.public[*].id

  enable_deletion_protection = false # Set to true for production

  tags = merge(local.network_tags, {
    Name         = "${local.name_prefix}-alb"
    ResourceType = "application-load-balancer"
    Purpose      = "ecs-fargate-load-balancing"
    Billable     = "true"
  })
}

# Target Group for ECS Service
resource "aws_lb_target_group" "ecs" {
  count = var.enable_alb ? 1 : 0

  name        = "${local.name_prefix}-ecs-tg"
  port        = 5000
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2  # 2 consecutive successes = healthy  
    unhealthy_threshold = 3  # 3 consecutive failures = unhealthy (more tolerance)
    timeout             = 5  # 5 second timeout per check
    interval            = 15 # Check every 15 seconds (faster than 30s)
    path                = "/api/ping"
    matcher             = "200"
    protocol            = "HTTP"
    port                = "traffic-port"
  }

  # Fast deregistration for zero-downtime deployments
  deregistration_delay = 30 # 30 seconds instead of default 300

  tags = merge(local.network_tags, {
    Name         = "${local.name_prefix}-ecs-target-group"
    ResourceType = "lb-target-group"
    Purpose      = "ecs-fargate-targets"
  })
}

# ALB Listener (HTTP)
resource "aws_lb_listener" "http" {
  count = var.enable_alb ? 1 : 0

  load_balancer_arn = aws_lb.main[0].arn
  port              = "80"
  protocol          = "HTTP"

  # Redirect HTTP to HTTPS
  default_action {
    type = "redirect"

    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }

  tags = merge(local.network_tags, {
    Name         = "${local.name_prefix}-alb-http-listener"
    ResourceType = "lb-listener"
    Purpose      = "http-to-https-redirect"
  })
}

# SSL Certificate for the domain
resource "aws_acm_certificate" "main" {
  count = var.enable_alb ? 1 : 0

  domain_name               = local.api_domain_name
  subject_alternative_names = []
  validation_method         = "DNS"

  lifecycle {
    create_before_destroy = true
  }

  tags = merge(local.security_tags, {
    Name         = "${local.name_prefix}-ssl-certificate"
    ResourceType = "acm-certificate"
    Purpose      = "alb-ssl-termination"
    Domain       = var.domain_name
  })
}

# SSL Certificate validation records in CloudFlare
resource "cloudflare_record" "cert_validation" {
  count = var.enable_alb && var.cloudflare_zone_id != "" ? 1 : 0

  zone_id = var.cloudflare_zone_id
  name    = tolist(aws_acm_certificate.main[0].domain_validation_options)[count.index].resource_record_name
  content = trimsuffix(tolist(aws_acm_certificate.main[0].domain_validation_options)[count.index].resource_record_value, ".")
  type    = tolist(aws_acm_certificate.main[0].domain_validation_options)[count.index].resource_record_type
  ttl     = 60
  proxied = false

  comment = "SSL certificate validation for ALB"
}

# Certificate validation
resource "aws_acm_certificate_validation" "main" {
  count = var.enable_alb && var.cloudflare_zone_id != "" ? 1 : 0

  certificate_arn         = aws_acm_certificate.main[0].arn
  validation_record_fqdns = cloudflare_record.cert_validation[*].hostname

  timeouts {
    create = "5m"
  }
}

# HTTPS Listener
resource "aws_lb_listener" "https" {
  count = var.enable_alb ? 1 : 0

  load_balancer_arn = aws_lb.main[0].arn
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS-1-2-2017-01"
  certificate_arn   = var.cloudflare_zone_id != "" ? aws_acm_certificate_validation.main[0].certificate_arn : aws_acm_certificate.main[0].arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.ecs[0].arn
  }

  tags = merge(local.network_tags, {
    Name         = "${local.name_prefix}-alb-https-listener"
    ResourceType = "lb-listener"
    Purpose      = "https-traffic-routing"
  })
}

# Update ECS Security Group to allow ALB traffic
resource "aws_security_group_rule" "ecs_from_alb" {
  count = var.enable_alb ? 1 : 0

  type                     = "ingress"
  from_port                = 5000
  to_port                  = 5000
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.alb[0].id
  security_group_id        = aws_security_group.ecs_service.id
  description              = "Allow traffic from ALB"
}

# Remove direct CloudFlare access to ECS (force traffic through ALB)
# Comment out or remove the CloudFlare IP ingress rule in ecs.tf