variable "name_prefix" {
  description = "Name prefix used for Redis resources."
  type        = string
}

variable "vpc_id" {
  description = "VPC ID where Redis is deployed."
  type        = string
}

variable "private_subnet_ids" {
  description = "Private subnet IDs for the Redis subnet group."
  type        = list(string)
}

variable "allowed_security_group_ids" {
  description = "Security group IDs allowed to connect to Redis."
  type        = list(string)
}

variable "engine_version" {
  description = "Optional Redis engine version. Leave null to use AWS default."
  type        = string
  default     = null
}

variable "node_type" {
  description = "ElastiCache node type."
  type        = string
}

variable "num_cache_clusters" {
  description = "Number of cache clusters in the replication group."
  type        = number
}

variable "automatic_failover_enabled" {
  description = "Whether automatic failover is enabled."
  type        = bool
}

variable "multi_az_enabled" {
  description = "Whether Multi-AZ is enabled."
  type        = bool
}

variable "snapshot_retention_days" {
  description = "Redis snapshot retention in days."
  type        = number
}

variable "snapshot_window" {
  description = "Preferred Redis snapshot window."
  type        = string
  default     = "06:00-07:00"
}

variable "maintenance_window" {
  description = "Preferred Redis maintenance window."
  type        = string
  default     = "sun:07:00-sun:08:00"
}

variable "apply_immediately" {
  description = "Whether Redis changes apply immediately."
  type        = bool
  default     = false
}

variable "tags" {
  description = "Common tags applied to all resources."
  type        = map(string)
  default     = {}
}

variable "auth_token" {
  description = "Ephemeral AUTH token; must only be used with auth_token_wo."
  type        = string
  sensitive   = true
  ephemeral   = true
}

variable "auth_token_version" {
  description = "Approved token change version; token is never recorded in state."
  type        = number
}
