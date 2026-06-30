output "secret_arns" {
  description = "Map of placeholder secret names to ARNs."
  value       = { for name, secret in aws_secretsmanager_secret.this : name => secret.arn }
}

output "secret_names" {
  description = "Map of placeholder secret names to AWS Secrets Manager names."
  value       = { for name, secret in aws_secretsmanager_secret.this : name => secret.name }
}
