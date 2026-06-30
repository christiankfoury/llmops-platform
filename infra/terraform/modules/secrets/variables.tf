variable "name_prefix" {
  description = "Name prefix used for Secrets Manager placeholders."
  type        = string
}

variable "secret_names" {
  description = "Logical secret placeholders to create without committing secret values."
  type        = list(string)
  default = [
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
