output "vpc_id" {
  description = "Prod VPC ID."
  value       = module.network.vpc_id
}

output "private_subnet_ids" {
  description = "Prod private subnet IDs."
  value       = module.network.private_subnet_ids
}

output "public_subnet_ids" {
  description = "Prod public subnet IDs."
  value       = module.network.public_subnet_ids
}

output "ecr_repository_urls" {
  description = "Prod ECR repository URLs."
  value       = module.registry.repository_urls
}

output "secret_names" {
  description = "Prod Secrets Manager placeholder names."
  value       = module.secrets.secret_names
}

output "github_actions_role_arn" {
  description = "Optional prod GitHub Actions role ARN."
  value       = module.iam.github_actions_role_arn
}
