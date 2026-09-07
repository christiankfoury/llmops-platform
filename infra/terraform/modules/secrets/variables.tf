variable "name_prefix" {
  description = "Name prefix used for Secrets Manager placeholders."
  type        = string
}

variable "secret_names" {
  description = "Separate app/runtime, web-session and migration-owner containers without secret values."
  type        = list(string)
  default     = ["runtime", "web-session", "migration"]
  validation {
    condition     = alltrue([for name in ["runtime", "web-session", "migration"] : contains(var.secret_names, name)])
    error_message = "Provide runtime, web-session and migration secret containers."
  }
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

variable "application_namespace" {
  description = "Application namespace; migration reader is isolated in the -migration namespace."
  type        = string
}
