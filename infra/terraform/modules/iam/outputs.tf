output "github_actions_role_arn" {
  description = "Namespace application deployment identity; no registry publishing."
  value       = try(aws_iam_role.github_actions[0].arn, null)
}

output "github_publisher_role_arn" {
  description = "Environment-scoped ECR publisher with no Kubernetes access entry."
  value       = try(aws_iam_role.github_publisher[0].arn, null)
}

output "github_oidc_provider_arn" {
  description = "ARN of the optional GitHub OIDC provider."
  value       = try(data.aws_iam_openid_connect_provider.github[0].arn, null)
}

output "github_migration_role_arn" {
  description = "Separate approved migration runner role; no app namespace or cluster bootstrap access."
  value       = try(aws_iam_role.github_migration[0].arn, null)
}
