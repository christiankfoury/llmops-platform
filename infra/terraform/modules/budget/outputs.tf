output "budget_name" {
  description = "Created AWS Budget name, or null when disabled."
  value       = try(aws_budgets_budget.monthly[0].name, null)
}

output "budget_enabled" {
  description = "Whether a monthly AWS Budget resource is created."
  value       = local.create_budget
}
