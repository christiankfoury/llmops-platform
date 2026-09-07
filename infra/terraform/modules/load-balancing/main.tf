locals {
  enabled = var.configuration != null
  targets = local.enabled ? {
    api = { port = 8000, path = "/health/ready", matcher = "200", priority = 10, host = var.configuration.api_hostname }
    web = { port = 3000, path = "/", matcher = "200-399", priority = 20, host = var.configuration.web_hostname }
  } : {}
}

resource "aws_security_group" "alb" {
  count       = local.enabled ? 1 : 0
  name_prefix = "${var.name_prefix}-alb-"
  description = "Terraform-owned ALB: approved TLS clients and application ports only"
  vpc_id      = var.vpc_id
  tags        = var.tags
}

resource "aws_vpc_security_group_ingress_rule" "tls" {
  for_each          = local.enabled ? var.configuration.allowed_cidrs : toset([])
  security_group_id = aws_security_group.alb[0].id
  description       = "Approved TLS client range"
  cidr_ipv4         = each.value
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
  tags              = var.tags
}

resource "aws_vpc_security_group_egress_rule" "pods" {
  for_each                     = local.targets
  security_group_id            = aws_security_group.alb[0].id
  referenced_security_group_id = var.pod_security_group_id
  description                  = "Terraform-owned ${each.key} target and health traffic"
  ip_protocol                  = "tcp"
  from_port                    = each.value.port
  to_port                      = each.value.port
  tags                         = var.tags
}

resource "aws_vpc_security_group_ingress_rule" "pods" {
  for_each                     = local.targets
  security_group_id            = var.pod_security_group_id
  referenced_security_group_id = aws_security_group.alb[0].id
  # Never use the LBC shared-rule marker; the restricted controller still checks GC.
  description = "Terraform-owned ${each.key} traffic from the platform ALB"
  ip_protocol = "tcp"
  from_port   = each.value.port
  to_port     = each.value.port
  tags        = var.tags
}

resource "aws_lb" "this" {
  count                      = local.enabled ? 1 : 0
  name_prefix                = "aip-"
  internal                   = var.configuration.internal
  load_balancer_type         = "application"
  security_groups            = [aws_security_group.alb[0].id]
  subnets                    = var.configuration.internal ? var.private_subnet_ids : var.public_subnet_ids
  enable_deletion_protection = true
  drop_invalid_header_fields = true
  desync_mitigation_mode     = "strictest"
  access_logs {
    enabled = true
    bucket  = var.configuration.access_logs_bucket
    prefix  = var.name_prefix
  }
  tags = var.tags
}

resource "aws_lb_target_group" "this" {
  for_each             = local.targets
  name_prefix          = "${each.key}-"
  vpc_id               = var.vpc_id
  target_type          = "ip"
  ip_address_type      = "ipv4"
  protocol             = "HTTP"
  port                 = each.value.port
  deregistration_delay = 30
  health_check {
    enabled             = true
    protocol            = "HTTP"
    port                = "traffic-port"
    path                = each.value.path
    matcher             = each.value.matcher
    interval            = 15
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 2
  }
  tags = var.tags
  # No aws_lb_target_group_attachment: the restricted controller owns pod membership.
}

resource "aws_lb_listener" "https" {
  count             = local.enabled ? 1 : 0
  load_balancer_arn = aws_lb.this[0].arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = var.configuration.certificate_arn
  default_action {
    type = "fixed-response"
    fixed_response {
      content_type = "text/plain"
      message_body = "Not found"
      status_code  = "404"
    }
  }
  tags = var.tags
}

resource "aws_lb_listener_rule" "host" {
  for_each     = local.targets
  listener_arn = aws_lb_listener.https[0].arn
  priority     = each.value.priority
  condition {
    host_header { values = [each.value.host] }
  }
  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.this[each.key].arn
  }
  tags = var.tags
}

resource "aws_iam_role_policy" "registration" {
  count = local.enabled ? 1 : 0
  name  = "approved-target-registration"
  role  = var.controller_role_name
  # Describe APIs lack AWS resource-level authorization. v3.5.0 needs SG discovery
  # even when TGB networking is omitted; the compatibility test uses this same policy.
  policy = templatefile("${path.module}/registration-policy.json.tftpl", {
    targetgroup_arns = jsonencode([for target in aws_lb_target_group.this : target.arn])
  })
}
