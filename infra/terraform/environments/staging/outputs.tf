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

output "database_endpoint" {
  description = "Staging RDS PostgreSQL endpoint."
  value       = module.database.instance_endpoint
}

output "database_master_user_secret_arn" {
  description = "Staging AWS-managed RDS master user secret ARN."
  value       = module.database.master_user_secret_arn
  sensitive   = true
}

output "redis_primary_endpoint" {
  description = "Staging Redis primary endpoint address."
  value       = module.redis.primary_endpoint_address
}

output "secret_names" {
  description = "Staging Secrets Manager placeholder names."
  value       = module.secrets.secret_names
}

output "external_secrets_role_arn" {
  description = "Staging External Secrets Operator IAM role ARN."
  value       = module.secrets.external_secrets_role_arn
}

output "github_actions_role_arn" {
  description = "Optional staging GitHub Actions role ARN."
  value       = module.iam.github_actions_role_arn
}

output "budget_name" {
  description = "Optional staging AWS Budget name."
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


output "load_balancing_bootstrap_values" {
  description = "Exact TargetGroupBinding approvals; merge into bootstrap values after approved AWS creation."
  value       = module.load_balancing.bootstrap_values
}
output "alb_dns_name" {
  value = module.load_balancing.alb_dns_name
}
