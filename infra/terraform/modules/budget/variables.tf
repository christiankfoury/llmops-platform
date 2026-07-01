variable "enabled" {
  description = "Whether to create the monthly AWS Budget alert."
  type        = bool
  default     = false
}

variable "name_prefix" {
  description = "Name prefix used for the budget."
  type        = string
}

variable "monthly_limit_usd" {
  description = "Monthly cost budget limit in USD."
  type        = string
}

variable "alert_threshold_percent" {
  description = "Percentage of the monthly budget that triggers the alert."
  type        = number
  default     = 80
}

variable "subscriber_email_addresses" {
  description = "Email subscribers for budget alerts. Required when the budget is enabled."
  type        = list(string)
  default     = []
}
