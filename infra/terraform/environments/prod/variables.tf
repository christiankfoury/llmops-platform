variable "aws_region" {
  description = "AWS region for the prod environment."
  type        = string
  default     = "us-east-1"
}

variable "vpc_cidr" {
  description = "VPC CIDR block for the prod environment."
  type        = string
  default     = "10.40.0.0/16"
}

variable "az_count" {
  description = "Number of availability zones for prod."
  type        = number
  default     = 3
}

variable "enable_nat_gateway" {
  description = "Whether prod creates a NAT gateway."
  type        = bool
  default     = true
}

variable "ecr_repository_names" {
  description = "Application image repositories."
  type        = list(string)
  default     = ["api", "web"]
}

variable "max_tagged_images" {
  description = "Tagged image retention count per repository."
  type        = number
  default     = 60
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
    "database-password",
    "redis-auth-token",
    "openai-api-key",
    "gateway-signing-secret"
  ]
}

variable "secret_recovery_window_in_days" {
  description = "Secrets Manager recovery window for prod."
  type        = number
  default     = 30
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
