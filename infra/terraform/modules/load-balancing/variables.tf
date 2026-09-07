variable "name_prefix" { type = string }
variable "vpc_id" { type = string }
variable "private_subnet_ids" { type = list(string) }
variable "public_subnet_ids" { type = list(string) }
variable "pod_security_group_id" { type = string }
variable "controller_role_name" { type = string }
variable "tags" { type = map(string) }

variable "configuration" {
  description = "Null until the ALB, certificate, log bucket and exposure have an approved cloud plan. Does not create DNS/TLS certificates or log buckets."
  type = object({
    internal           = optional(bool, true)
    certificate_arn    = string
    access_logs_bucket = string
    allowed_cidrs      = set(string)
    api_hostname       = string
    web_hostname       = string
  })
  default = null
  validation {
    condition = var.configuration == null ? true : (
      can(regex("^arn:aws:acm:[a-z0-9-]+:[0-9]{12}:certificate/[a-f0-9-]+$", var.configuration.certificate_arn)) &&
      length(var.configuration.access_logs_bucket) >= 3 &&
      length(var.configuration.allowed_cidrs) > 0 &&
      alltrue([for cidr in var.configuration.allowed_cidrs : can(cidrnetmask(cidr))]) &&
      var.configuration.api_hostname != var.configuration.web_hostname &&
      alltrue([for host in [var.configuration.api_hostname, var.configuration.web_hostname] : can(regex("^[a-z0-9][a-z0-9.-]+[a-z0-9]$", host))])
    )
    error_message = "Use an explicit ACM certificate, approved access log bucket, nonempty IPv4 CIDRs and distinct exact hostnames."
  }
}
