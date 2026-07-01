locals {
  project_name = "production-ai-platform"
  environment  = "staging"
  name_prefix  = "${local.project_name}-${local.environment}"

  common_tags = {
    Project     = local.project_name
    Environment = local.environment
    ManagedBy   = "terraform"
    Repository  = "christiankfoury/production-ai-platform"
  }
}

module "network" {
  source = "../../modules/network"

  name_prefix        = local.name_prefix
  vpc_cidr           = var.vpc_cidr
  az_count           = var.az_count
  enable_nat_gateway = var.enable_nat_gateway
  tags               = local.common_tags
}

module "cluster" {
  source = "../../modules/cluster"

  name_prefix               = local.name_prefix
  environment               = local.environment
  private_subnet_ids        = module.network.private_subnet_ids
  kubernetes_version        = var.kubernetes_version
  endpoint_private_access   = var.eks_endpoint_private_access
  endpoint_public_access    = var.eks_endpoint_public_access
  public_access_cidrs       = var.eks_public_access_cidrs
  enabled_cluster_log_types = var.eks_enabled_cluster_log_types
  node_groups               = var.eks_node_groups
  access_entries = var.create_github_actions_role ? {
    github_actions_staging_deployer = {
      principal_arn = module.iam.github_actions_role_arn
      policy_associations = {
        staging_namespace_edit = {
          policy_arn = "arn:aws:eks::aws:cluster-access-policy/AmazonEKSEditPolicy"
          access_scope = {
            type       = "namespace"
            namespaces = ["ai-platform-staging"]
          }
        }
      }
    }
  } : {}
  tags = local.common_tags
}

module "database" {
  source = "../../modules/database"

  name_prefix                = local.name_prefix
  vpc_id                     = module.network.vpc_id
  private_subnet_ids         = module.network.private_subnet_ids
  allowed_security_group_ids = [module.cluster.cluster_security_group_id]
  database_name              = var.database_name
  master_username            = var.database_master_username
  engine_version             = var.database_engine_version
  instance_class             = var.database_instance_class
  allocated_storage_gb       = var.database_allocated_storage_gb
  max_allocated_storage_gb   = var.database_max_allocated_storage_gb
  backup_retention_days      = var.database_backup_retention_days
  multi_az                   = var.database_multi_az
  deletion_protection        = var.database_deletion_protection
  skip_final_snapshot        = var.database_skip_final_snapshot
  tags                       = local.common_tags
}

module "redis" {
  source = "../../modules/redis"

  name_prefix                = local.name_prefix
  vpc_id                     = module.network.vpc_id
  private_subnet_ids         = module.network.private_subnet_ids
  allowed_security_group_ids = [module.cluster.cluster_security_group_id]
  engine_version             = var.redis_engine_version
  node_type                  = var.redis_node_type
  num_cache_clusters         = var.redis_num_cache_clusters
  automatic_failover_enabled = var.redis_automatic_failover_enabled
  multi_az_enabled           = var.redis_multi_az_enabled
  snapshot_retention_days    = var.redis_snapshot_retention_days
  apply_immediately          = var.redis_apply_immediately
  tags                       = local.common_tags
}

module "registry" {
  source = "../../modules/registry"

  name_prefix       = local.name_prefix
  repository_names  = var.ecr_repository_names
  max_tagged_images = var.max_tagged_images
  force_delete      = var.ecr_force_delete
  tags              = local.common_tags
}

module "secrets" {
  source = "../../modules/secrets"

  name_prefix             = local.name_prefix
  secret_names            = var.secret_names
  recovery_window_in_days = var.secret_recovery_window_in_days
  tags                    = local.common_tags
}

module "iam" {
  source = "../../modules/iam"

  name_prefix                = local.name_prefix
  environment                = local.environment
  create_github_actions_role = var.create_github_actions_role
  github_repository          = var.github_repository
  ecr_repository_arns        = values(module.registry.repository_arns)
  eks_cluster_name           = "${local.name_prefix}-eks"
  tags                       = local.common_tags
}
