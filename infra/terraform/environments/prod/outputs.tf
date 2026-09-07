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

output "eks_cluster_name" {
  description = "Prod EKS cluster name."
  value       = module.cluster.cluster_name
}

output "eks_cluster_endpoint" {
  description = "Prod EKS cluster endpoint."
  value       = module.cluster.cluster_endpoint
}

output "eks_oidc_provider_arn" {
  description = "Prod EKS OIDC provider ARN for workload identity."
  value       = module.cluster.oidc_provider_arn
}

output "eks_node_role_arn" {
  description = "Prod EKS node IAM role ARN."
  value       = module.cluster.node_role_arn
}

output "database_endpoint" {
  description = "Prod RDS PostgreSQL endpoint."
  value       = module.database.instance_endpoint
}

output "database_master_user_secret_arn" {
  description = "Prod AWS-managed RDS master user secret ARN."
  value       = module.database.master_user_secret_arn
  sensitive   = true
}

output "redis_primary_endpoint" {
  description = "Prod Redis primary endpoint address."
  value       = module.redis.primary_endpoint_address
}

output "secret_names" {
  description = "Prod Secrets Manager placeholder names."
  value       = module.secrets.secret_names
}

output "external_secrets_role_arn" {
  description = "Prod External Secrets Operator IAM role ARN."
  value       = module.secrets.external_secrets_role_arn
}

output "github_actions_role_arn" {
  description = "Optional prod GitHub Actions role ARN."
  value       = module.iam.github_actions_role_arn
}

output "budget_name" {
  description = "Optional prod AWS Budget name."
  value       = module.budget.budget_name
}

output "github_migration_role_arn" {
  description = "Separate namespace-scoped migration runner role."
  value       = module.iam.github_migration_role_arn
}

output "external_secrets_role_arns" {
  description = "Distinct bootstrap reader identities; migration owner is excluded from the runtime role."
  value       = module.secrets.external_secrets_role_arns
}

output "load_balancer_role_arn" {
  value       = module.cluster.load_balancer_role_arn
  description = "Bootstrap-owned load balancer controller identity."
}
