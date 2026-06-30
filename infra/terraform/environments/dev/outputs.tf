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

output "eks_cluster_name" {
  description = "Dev EKS cluster name."
  value       = module.cluster.cluster_name
}

output "eks_cluster_endpoint" {
  description = "Dev EKS cluster endpoint."
  value       = module.cluster.cluster_endpoint
}

output "eks_oidc_provider_arn" {
  description = "Dev EKS OIDC provider ARN for workload identity."
  value       = module.cluster.oidc_provider_arn
}

output "eks_node_role_arn" {
  description = "Dev EKS node IAM role ARN."
  value       = module.cluster.node_role_arn
}

output "secret_names" {
  description = "Dev Secrets Manager placeholder names."
  value       = module.secrets.secret_names
}

output "github_actions_role_arn" {
  description = "Optional dev GitHub Actions role ARN."
  value       = module.iam.github_actions_role_arn
}
