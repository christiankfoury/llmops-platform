locals {
  project_name = "production-ai-platform"
  environment  = "prod"
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
  tags                       = local.common_tags
}
