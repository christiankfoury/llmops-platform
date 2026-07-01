variable "name_prefix" {
  description = "Name prefix used for IAM resources."
  type        = string
}

variable "environment" {
  description = "Deployment environment name."
  type        = string
}

variable "create_github_actions_role" {
  description = "Whether to create an OIDC-backed GitHub Actions role."
  type        = bool
  default     = false
}

variable "github_repository" {
  description = "GitHub repository in owner/name format allowed to assume the CI/CD role."
  type        = string
  default     = ""
}

variable "github_oidc_thumbprints" {
  description = "Thumbprints for GitHub Actions OIDC provider."
  type        = list(string)
  default     = ["6938fd4d98bab03faadb97b34396831e3780aea1"]
}

variable "ecr_repository_arns" {
  description = "ECR repository ARNs the optional GitHub Actions role can publish to."
  type        = list(string)
  default     = []
}

variable "eks_cluster_name" {
  description = "Optional EKS cluster name the GitHub Actions role can describe for kubeconfig generation."
  type        = string
  default     = ""
}

variable "tags" {
  description = "Common tags applied to all resources."
  type        = map(string)
  default     = {}
}
