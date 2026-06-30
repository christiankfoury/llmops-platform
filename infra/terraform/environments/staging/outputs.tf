output "vpc_id" {
  description = "Staging VPC ID."
  value       = module.network.vpc_id
}

output "private_subnet_ids" {
  description = "Staging private subnet IDs."
  value       = module.network.private_subnet_ids
}

output "public_subnet_ids" {
  description = "Staging public subnet IDs."
  value       = module.network.public_subnet_ids
}

output "ecr_repository_urls" {
  description = "Staging ECR repository URLs."
  value       = module.registry.repository_urls
}

output "secret_names" {
  description = "Staging Secrets Manager placeholder names."
  value       = module.secrets.secret_names
}

output "github_actions_role_arn" {
  description = "Optional staging GitHub Actions role ARN."
  value       = module.iam.github_actions_role_arn
}
