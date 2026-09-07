output "secret_arns" {
  description = "Map of placeholder secret names to ARNs."
  value       = { for name, secret in aws_secretsmanager_secret.this : name => secret.arn }
}

output "secret_names" {
  description = "Map of placeholder secret names to AWS Secrets Manager names."
  value       = { for name, secret in aws_secretsmanager_secret.this : name => secret.name }
}

output "external_secrets_role_arn" {
  description = "IAM role ARN for the External Secrets Operator service account."
  value       = try(aws_iam_role.external_secrets["runtime"].arn, null)
}

output "external_secrets_role_arns" {
  description = "Separate runtime/session and migration-owner reader roles for privileged bootstrap."
  value       = { for name, role in aws_iam_role.external_secrets : name => role.arn }
}
