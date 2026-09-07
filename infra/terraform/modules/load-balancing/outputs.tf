output "bootstrap_values" {
  description = "Exact approved TGB tuples; set bootstrap targetBindingsEnabled only after controller/CRD/admission readiness."
  value = {
    targetBindings = { for key, group in aws_lb_target_group.this : "ai-platform-${key}" => {
      arn = group.arn, service = "ai-platform-${key}", port = local.targets[key].port, vpcID = var.vpc_id
    } }
  }
}
output "alb_dns_name" {
  value = local.enabled ? aws_lb.this[0].dns_name : null
}
output "registration_policy_json" {
  description = "Reviewable IAM document; no credentials."
  value       = local.enabled ? aws_iam_role_policy.registration[0].policy : null
}
