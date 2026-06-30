variable "name_prefix" {
  description = "Name prefix used for ECR repositories."
  type        = string
}

variable "repository_names" {
  description = "Logical application image repositories to create."
  type        = list(string)
  default     = ["api", "web"]
}

variable "max_tagged_images" {
  description = "Number of tagged images to retain per repository."
  type        = number
  default     = 30
}

variable "force_delete" {
  description = "Whether repositories can be force-deleted while containing images."
  type        = bool
  default     = false
}

variable "tags" {
  description = "Common tags applied to all resources."
  type        = map(string)
  default     = {}
}
