output "github_actions_role_arn" {
  description = "ARN of the optional GitHub Actions role."
  value       = try(aws_iam_role.github_actions[0].arn, null)
}

output "github_oidc_provider_arn" {
  description = "ARN of the optional GitHub OIDC provider."
  value       = try(aws_iam_openid_connect_provider.github[0].arn, null)
}
