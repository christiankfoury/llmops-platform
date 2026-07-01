variable "name_prefix" {
  description = "Name prefix used for database resources."
  type        = string
}

variable "vpc_id" {
  description = "VPC ID where the database is deployed."
  type        = string
}

variable "private_subnet_ids" {
  description = "Private subnet IDs for the database subnet group."
  type        = list(string)
}

variable "allowed_security_group_ids" {
  description = "Security group IDs allowed to connect to PostgreSQL."
  type        = list(string)
}

variable "database_name" {
  description = "Initial application database name."
  type        = string
  default     = "ai_platform"
}

variable "master_username" {
  description = "RDS master username. Password is managed by AWS, not Terraform."
  type        = string
  default     = "ai_platform"
}

variable "engine_version" {
  description = "Optional PostgreSQL engine version. Leave null to use AWS default."
  type        = string
  default     = null
}

variable "instance_class" {
  description = "RDS instance class."
  type        = string
}

variable "allocated_storage_gb" {
  description = "Initial allocated storage in GiB."
  type        = number
}

variable "max_allocated_storage_gb" {
  description = "Maximum autoscaled storage in GiB."
  type        = number
}

variable "backup_retention_days" {
  description = "Automated backup retention in days."
  type        = number
}

variable "backup_window" {
  description = "Preferred backup window."
  type        = string
  default     = "07:00-08:00"
}

variable "maintenance_window" {
  description = "Preferred maintenance window."
  type        = string
  default     = "sun:08:00-sun:09:00"
}

variable "multi_az" {
  description = "Whether to enable Multi-AZ for the database."
  type        = bool
  default     = false
}

variable "deletion_protection" {
  description = "Whether deletion protection is enabled."
  type        = bool
  default     = true
}

variable "skip_final_snapshot" {
  description = "Whether to skip final snapshot on deletion."
  type        = bool
  default     = false
}

variable "performance_insights_enabled" {
  description = "Whether to enable Performance Insights."
  type        = bool
  default     = true
}

variable "tags" {
  description = "Common tags applied to all resources."
  type        = map(string)
  default     = {}
}
