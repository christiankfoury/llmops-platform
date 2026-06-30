output "vpc_id" {
  description = "Dev VPC ID."
  value       = module.network.vpc_id
}

output "private_subnet_ids" {
  description = "Dev private subnet IDs."
  value       = module.network.private_subnet_ids
}

output "public_subnet_ids" {
  description = "Dev public subnet IDs."
  value       = module.network.public_subnet_ids
}

output "ecr_repository_urls" {
  description = "Dev ECR repository URLs."
  value       = module.registry.repository_urls
}

output "secret_names" {
  description = "Dev Secrets Manager placeholder names."
  value       = module.secrets.secret_names
}

output "github_actions_role_arn" {
  description = "Optional dev GitHub Actions role ARN."
  value       = module.iam.github_actions_role_arn
}
