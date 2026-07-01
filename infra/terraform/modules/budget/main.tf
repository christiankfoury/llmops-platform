locals {
  create_budget = var.enabled && length(var.subscriber_email_addresses) > 0
}

resource "aws_budgets_budget" "monthly" {
  count = local.create_budget ? 1 : 0

  name         = "${var.name_prefix}-monthly-cost"
  budget_type  = "COST"
  limit_amount = var.monthly_limit_usd
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  notification {
    comparison_operator        = "GREATER_THAN"
    notification_type          = "ACTUAL"
    threshold                  = var.alert_threshold_percent
    threshold_type             = "PERCENTAGE"
    subscriber_email_addresses = var.subscriber_email_addresses
  }
}
