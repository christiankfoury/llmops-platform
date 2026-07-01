variable "name_prefix" {
  description = "Name prefix used for Secrets Manager placeholders."
  type        = string
}

variable "secret_names" {
  description = "Logical secret placeholders to create without committing secret values."
  type        = list(string)
  default = [
    "runtime",
    "database-password",
    "redis-auth-token",
    "openai-api-key",
    "gateway-signing-secret"
  ]
}

variable "recovery_window_in_days" {
  description = "Secrets Manager recovery window."
  type        = number
  default     = 7
}

variable "tags" {
  description = "Common tags applied to all resources."
  type        = map(string)
  default     = {}
}

variable "enable_external_secrets_irsa" {
  description = "Create an IAM role for the External Secrets Operator service account."
  type        = bool
  default     = false
}

variable "eks_oidc_provider_arn" {
  description = "EKS OIDC provider ARN used for External Secrets IRSA."
  type        = string
  default     = null
}

variable "eks_oidc_issuer_url" {
  description = "EKS OIDC issuer URL used for External Secrets IRSA."
  type        = string
  default     = null
}

variable "external_secrets_namespace" {
  description = "Namespace containing the External Secrets Operator service account."
  type        = string
  default     = "external-secrets"
}

variable "external_secrets_service_account" {
  description = "External Secrets Operator Kubernetes service account name."
  type        = string
  default     = "external-secrets"
}
