variable "aws_region" {
  description = "AWS region for the staging environment."
  type        = string
  default     = "us-east-1"
}

variable "vpc_cidr" {
  description = "VPC CIDR block for the staging environment."
  type        = string
  default     = "10.30.0.0/16"
}

variable "az_count" {
  description = "Number of availability zones for staging."
  type        = number
  default     = 2
}

variable "enable_nat_gateway" {
  description = "Whether staging creates a NAT gateway."
  type        = bool
  default     = true
}

variable "kubernetes_version" {
  description = "Optional EKS Kubernetes version. Null lets AWS choose the default at cluster creation."
  type        = string
  default     = null
}

variable "eks_endpoint_private_access" {
  description = "Whether the EKS API endpoint is reachable inside the VPC."
  type        = bool
  default     = true
}

variable "eks_endpoint_public_access" {
  description = "Whether the EKS API endpoint is reachable publicly."
  type        = bool
  default     = false
}

variable "eks_public_access_cidrs" {
  description = "CIDR ranges allowed to reach the public EKS API endpoint."
  type        = list(string)
  default     = []
}

variable "eks_enabled_cluster_log_types" {
  description = "EKS control plane log types to enable."
  type        = list(string)
  default     = ["api", "audit", "authenticator", "controllerManager", "scheduler"]
}

variable "eks_node_groups" {
  description = "Managed node groups for staging."
  type = map(object({
    ami_type        = optional(string, "AL2_x86_64")
    capacity_type   = optional(string, "ON_DEMAND")
    desired_size    = number
    disk_size       = optional(number, 40)
    instance_types  = list(string)
    labels          = optional(map(string), {})
    max_size        = number
    max_unavailable = optional(number, 1)
    min_size        = number
  }))
  default = {
    system = {
      capacity_type  = "ON_DEMAND"
      desired_size   = 2
      disk_size      = 50
      instance_types = ["t3.medium"]
      labels = {
        workload = "system"
      }
      max_size = 4
      min_size = 2
    }
  }
}

variable "database_name" {
  description = "Initial PostgreSQL database name."
  type        = string
  default     = "ai_platform"
}

variable "database_master_username" {
  description = "RDS master username. Password is managed by AWS."
  type        = string
  default     = "ai_platform"
}

variable "database_engine_version" {
  description = "Optional PostgreSQL engine version. Null lets AWS choose the default."
  type        = string
  default     = null
}

variable "database_instance_class" {
  description = "Staging RDS instance class."
  type        = string
  default     = "db.t4g.small"
}

variable "database_allocated_storage_gb" {
  description = "Initial staging RDS storage in GiB."
  type        = number
  default     = 50
}

variable "database_max_allocated_storage_gb" {
  description = "Maximum staging RDS autoscaled storage in GiB."
  type        = number
  default     = 100
}

variable "database_backup_retention_days" {
  description = "Staging RDS backup retention in days."
  type        = number
  default     = 7
}

variable "database_multi_az" {
  description = "Whether staging RDS uses Multi-AZ."
  type        = bool
  default     = true
}

variable "database_deletion_protection" {
  description = "Whether staging RDS deletion protection is enabled."
  type        = bool
  default     = true
}

variable "database_skip_final_snapshot" {
  description = "Whether staging skips final snapshot on deletion."
  type        = bool
  default     = false
}

variable "redis_engine_version" {
  description = "Optional Redis engine version. Null lets AWS choose the default."
  type        = string
  default     = null
}

variable "redis_node_type" {
  description = "Staging Redis node type."
  type        = string
  default     = "cache.t4g.small"
}

variable "redis_num_cache_clusters" {
  description = "Number of staging Redis cache clusters."
  type        = number
  default     = 2
}

variable "redis_automatic_failover_enabled" {
  description = "Whether staging Redis automatic failover is enabled."
  type        = bool
  default     = true
}

variable "redis_multi_az_enabled" {
  description = "Whether staging Redis Multi-AZ is enabled."
  type        = bool
  default     = true
}

variable "redis_snapshot_retention_days" {
  description = "Staging Redis snapshot retention in days."
  type        = number
  default     = 7
}

variable "redis_apply_immediately" {
  description = "Whether staging Redis changes apply immediately."
  type        = bool
  default     = false
}

variable "ecr_repository_names" {
  description = "Application image repositories."
  type        = list(string)
  default     = ["api", "web"]
}

variable "max_tagged_images" {
  description = "Tagged image retention count per repository."
  type        = number
  default     = 40
}

variable "ecr_force_delete" {
  description = "Whether ECR repositories can be deleted while containing images."
  type        = bool
  default     = false
}

variable "secret_names" {
  description = "Placeholder secrets to create without secret values."
  type        = list(string)
  default = [
    "runtime",
    "database-password",
    "redis-auth-token",
    "openai-api-key",
    "gateway-signing-secret"
  ]
}

variable "secret_recovery_window_in_days" {
  description = "Secrets Manager recovery window for staging."
  type        = number
  default     = 14
}

variable "budget_alert_enabled" {
  description = "Whether to create the optional staging monthly AWS Budget alert."
  type        = bool
  default     = false
}

variable "budget_monthly_limit_usd" {
  description = "Staging monthly AWS Budget limit in USD."
  type        = string
  default     = "250"
}

variable "budget_alert_threshold_percent" {
  description = "Staging monthly budget percentage that triggers an alert."
  type        = number
  default     = 80
}

variable "budget_alert_subscriber_emails" {
  description = "Email addresses for optional staging AWS Budget alerts."
  type        = list(string)
  default     = []
}

variable "create_github_actions_role" {
  description = "Whether to create the optional GitHub Actions OIDC role."
  type        = bool
  default     = false
}

variable "github_repository" {
  description = "GitHub repository in owner/name format allowed to assume the optional CI/CD role."
  type        = string
  default     = "christiankfoury/production-ai-platform"
}
