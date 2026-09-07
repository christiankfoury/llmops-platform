# Only mock providers and plan commands; never AWS or a real cluster.
mock_provider "aws" {}

run "load_balancing_authorization_and_routing" {
  command = plan
  module { source = "../../modules/load-balancing" }
  variables {
    name_prefix           = "synthetic-platform"
    vpc_id                = "vpc-00000000000000000"
    private_subnet_ids    = ["subnet-00000000000000001", "subnet-00000000000000002"]
    public_subnet_ids     = ["subnet-00000000000000003", "subnet-00000000000000004"]
    pod_security_group_id = "sg-00000000000000000"
    controller_role_name  = "synthetic-controller"
    tags                  = { Environment = "test", ManagedBy = "terraform" }
    configuration = {
      certificate_arn    = "arn:aws:acm:us-east-1:000000000000:certificate/00000000-0000-0000-0000-000000000000"
      access_logs_bucket = "synthetic-approved-alb-logs"
      allowed_cidrs      = ["10.0.0.0/8"]
      api_hostname       = "api.platform.example.com"
      web_hostname       = "platform.example.com"
    }
  }
  override_resource {
    target          = aws_lb_target_group.this["api"]
    override_during = plan
    values          = { arn = "arn:aws:elasticloadbalancing:us-east-1:000000000000:targetgroup/api/0123456789abcdef" }
  }
  override_resource {
    target          = aws_lb_target_group.this["web"]
    override_during = plan
    values          = { arn = "arn:aws:elasticloadbalancing:us-east-1:000000000000:targetgroup/web/0123456789abcdef" }
  }
  assert {
    condition     = aws_lb.this[0].internal && aws_lb.this[0].enable_deletion_protection && aws_lb.this[0].drop_invalid_header_fields && one(aws_lb.this[0].access_logs).enabled
    error_message = "ALB must default internal, protected and access-logged."
  }
  assert {
    condition     = aws_lb_listener.https[0].port == 443 && aws_lb_listener.https[0].protocol == "HTTPS" && one(aws_lb_listener.https[0].default_action).type == "fixed-response"
    error_message = "Only TLS with default rejection may be exposed."
  }
  assert {
    condition     = alltrue([for target in aws_lb_target_group.this : target.target_type == "ip" && tonumber(target.deregistration_delay) == 30]) && one(aws_lb_target_group.this["api"].health_check).path == "/health/ready"
    error_message = "Targets must use pod IPs, bounded draining and readiness health checks."
  }
  assert {
    condition     = toset([for rule in aws_vpc_security_group_ingress_rule.pods : rule.to_port]) == toset([8000, 3000]) && alltrue([for rule in aws_vpc_security_group_ingress_rule.tls : rule.from_port == 443 && rule.to_port == 443])
    error_message = "Security groups must expose only TLS and the two application ports."
  }
  assert {
    condition     = toset(jsondecode(aws_iam_role_policy.registration[0].policy).Statement[0].Resource) == toset([aws_lb_target_group.this["api"].arn, aws_lb_target_group.this["web"].arn]) && length(jsondecode(aws_iam_role_policy.registration[0].policy).Statement) == 2
    error_message = "IAM membership scope must use only the Terraform-produced target groups."
  }
}
