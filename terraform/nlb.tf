# Network Load Balancer with Elastic IP
# Provides static IP for CloudFlare while maintaining ECS Fargate
# Cost: ~$16/month (same as ALB but with static IP)

# Elastic IP for NLB
resource "aws_eip" "nlb" {
  count = var.enable_nlb ? length(local.azs) : 0

  domain = "vpc"

  tags = merge(local.network_tags, {
    Name         = "${local.name_prefix}-nlb-eip-${count.index + 1}"
    ResourceType = "elastic-ip"
    Purpose      = "nlb-static-ip"
    Billable     = "true"
  })
}

# Network Load Balancer
resource "aws_lb" "nlb" {
  count = var.enable_nlb ? 1 : 0

  name               = "${local.name_prefix}-nlb"
  internal           = false
  load_balancer_type = "network"

  # Assign Elastic IPs to each subnet
  dynamic "subnet_mapping" {
    for_each = range(length(local.azs))
    content {
      subnet_id     = aws_subnet.public[subnet_mapping.value].id
      allocation_id = aws_eip.nlb[subnet_mapping.value].id
    }
  }

  enable_deletion_protection = false

  tags = merge(local.network_tags, {
    Name         = "${local.name_prefix}-nlb"
    ResourceType = "network-load-balancer"
    Purpose      = "ecs-fargate-static-ip"
    Billable     = "true"
  })
}

# NLB Target Group
resource "aws_lb_target_group" "nlb_ecs" {
  count = var.enable_nlb ? 1 : 0

  name        = "${local.name_prefix}-nlb-ecs-tg"
  port        = 5000
  protocol    = "TCP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 2
    timeout             = 10
    interval            = 30
    protocol            = "TCP"
    port                = "traffic-port"
  }

  tags = merge(local.network_tags, {
    Name         = "${local.name_prefix}-nlb-ecs-target-group"
    ResourceType = "lb-target-group"
    Purpose      = "nlb-ecs-targets"
  })
}

# NLB Listener
resource "aws_lb_listener" "nlb" {
  count = var.enable_nlb ? 1 : 0

  load_balancer_arn = aws_lb.nlb[0].arn
  port              = "80"
  protocol          = "TCP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.nlb_ecs[0].arn
  }

  tags = merge(local.network_tags, {
    Name         = "${local.name_prefix}-nlb-listener"
    ResourceType = "lb-listener"
    Purpose      = "tcp-traffic-forwarding"
  })
}