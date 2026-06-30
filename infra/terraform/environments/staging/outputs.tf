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

output "eks_cluster_name" {
  description = "Staging EKS cluster name."
  value       = module.cluster.cluster_name
}

output "eks_cluster_endpoint" {
  description = "Staging EKS cluster endpoint."
  value       = module.cluster.cluster_endpoint
}

output "eks_oidc_provider_arn" {
  description = "Staging EKS OIDC provider ARN for workload identity."
  value       = module.cluster.oidc_provider_arn
}

output "eks_node_role_arn" {
  description = "Staging EKS node IAM role ARN."
  value       = module.cluster.node_role_arn
}

output "secret_names" {
  description = "Staging Secrets Manager placeholder names."
  value       = module.secrets.secret_names
}

output "github_actions_role_arn" {
  description = "Optional staging GitHub Actions role ARN."
  value       = module.iam.github_actions_role_arn
}
