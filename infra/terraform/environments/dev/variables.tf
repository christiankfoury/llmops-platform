variable "aws_region" {
  description = "AWS region for the dev environment."
  type        = string
  default     = "us-east-1"
}

variable "vpc_cidr" {
  description = "VPC CIDR block for the dev environment."
  type        = string
  default     = "10.20.0.0/16"
}

variable "az_count" {
  description = "Number of availability zones for dev."
  type        = number
  default     = 2
}

variable "enable_nat_gateway" {
  description = "Whether private nodes have the required outbound route through a NAT gateway; included in the approved cost estimate."
  type        = bool
  default     = true
}

variable "kubernetes_version" {
  description = "Reviewed EKS minor version; verify region/add-on compatibility before approved creation."
  type        = string
  default     = "1.36"
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
  default     = ["api", "audit", "authenticator"]
}

variable "eks_node_groups" {
  description = "Managed node groups for dev."
  type = map(object({
    ami_type        = optional(string, "AL2023_x86_64_STANDARD")
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
      disk_size      = 40
      instance_types = ["t3.medium"]
      labels = {
        workload = "system"
      }
      max_size = 3
      min_size = 1
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
  description = "Reviewed PostgreSQL release candidate; verify RDS region availability during launch preflight."
  type        = string
  default     = "16.15"
}

variable "database_instance_class" {
  description = "Dev RDS instance class."
  type        = string
  default     = "db.t4g.micro"
}

variable "database_allocated_storage_gb" {
  description = "Initial dev RDS storage in GiB."
  type        = number
  default     = 20
}

variable "database_max_allocated_storage_gb" {
  description = "Maximum dev RDS autoscaled storage in GiB."
  type        = number
  default     = 50
}

variable "database_backup_retention_days" {
  description = "Dev RDS backup retention in days."
  type        = number
  default     = 1
}

variable "database_multi_az" {
  description = "Whether dev RDS uses Multi-AZ."
  type        = bool
  default     = false
}

variable "database_deletion_protection" {
  description = "Whether dev RDS deletion protection is enabled."
  type        = bool
  default     = false
}

variable "database_skip_final_snapshot" {
  description = "Whether dev skips final snapshot on deletion."
  type        = bool
  default     = true
}

variable "redis_engine_version" {
  description = "Managed Redis OSS 7.2 compatibility line; AWS supplies the patched engine build."
  type        = string
  default     = "7.2"
}

variable "redis_node_type" {
  description = "Dev Redis node type."
  type        = string
  default     = "cache.t4g.micro"
}

variable "redis_num_cache_clusters" {
  description = "Number of dev Redis cache clusters."
  type        = number
  default     = 1
}

variable "redis_automatic_failover_enabled" {
  description = "Whether dev Redis automatic failover is enabled."
  type        = bool
  default     = false
}

variable "redis_multi_az_enabled" {
  description = "Whether dev Redis Multi-AZ is enabled."
  type        = bool
  default     = false
}

variable "redis_snapshot_retention_days" {
  description = "Dev Redis snapshot retention in days."
  type        = number
  default     = 1
}

variable "redis_apply_immediately" {
  description = "Whether dev Redis changes apply immediately."
  type        = bool
  default     = true
}

variable "ecr_repository_names" {
  description = "Application image repositories."
  type        = list(string)
  default     = ["api", "migration", "web"]
}

variable "max_tagged_images" {
  description = "Tagged image retention count per repository."
  type        = number
  default     = 20
}

variable "ecr_force_delete" {
  description = "Whether ECR repositories can be deleted while containing images."
  type        = bool
  default     = false
}

variable "secret_names" {
  description = "Distinct runtime, web-session and migration-owner containers; values stay outside Terraform state."
  type        = list(string)
  default     = ["runtime", "web-session", "migration"]
}

variable "secret_recovery_window_in_days" {
  description = "Secrets Manager recovery window for dev."
  type        = number
  default     = 7
}

variable "budget_alert_enabled" {
  description = "Whether to create the optional dev monthly AWS Budget alert."
  type        = bool
  default     = false
}

variable "budget_monthly_limit_usd" {
  description = "Dev monthly AWS Budget limit in USD."
  type        = string
  default     = "75"
}

variable "budget_alert_threshold_percent" {
  description = "Dev monthly budget percentage that triggers an alert."
  type        = number
  default     = 80
}

variable "budget_alert_subscriber_emails" {
  description = "Email addresses for optional dev AWS Budget alerts."
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

variable "bootstrap_principal_arn" {
  description = "Existing trusted AWS role for approved cluster/bootstrap operations; distinct from app release roles."
  type        = string
  validation {
    condition     = can(regex("^arn:aws:iam::[0-9]{12}:role/.+$", var.bootstrap_principal_arn))
    error_message = "Provide the existing bootstrap IAM role ARN."
  }
}

variable "eks_addon_versions" {
  description = "Exact region/Kubernetes-compatible EKS build versions, resolved and reviewed at launch preflight. No implicit latest selection."
  type = object({
    vpc_cni        = string
    coredns        = string
    kube_proxy     = string
    ebs_csi        = string
    metrics_server = string
  })
  validation {
    condition     = alltrue([for version in values(var.eks_addon_versions) : can(regex("^v[0-9]+[.][0-9]+[.][0-9]+-eksbuild[.][0-9]+$", version))])
    error_message = "Pin each add-on to an explicit EKS build version after checking regional compatibility."
  }
}

variable "redis_auth_token" {
  description = "Externally supplied Redis AUTH token; ephemeral input reaches only the provider write-only field."
  type        = string
  sensitive   = true
  ephemeral   = true
  validation {
    condition     = can(regex("^[a-zA-Z0-9!&#$^<>-]{16,128}$", var.redis_auth_token))
    error_message = "Redis requires a supported 16-128 character authentication token."
  }
}

variable "redis_auth_token_version" {
  description = "Explicit token change version; increment only with approved credential change."
  type        = number
  default     = 1
  validation {
    condition     = var.redis_auth_token_version >= 1 && floor(var.redis_auth_token_version) == var.redis_auth_token_version
    error_message = "Token version must be a positive integer."
  }
}

variable "bootstrap_addons_enabled" {
  description = "Enable CoreDNS/CSI only after strict-mode bootstrap policies exist; keep enabled after approved bootstrap."
  type        = bool
  default     = false
}
