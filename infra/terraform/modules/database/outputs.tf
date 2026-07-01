output "instance_arn" {
  description = "RDS instance ARN."
  value       = aws_db_instance.this.arn
}

output "instance_endpoint" {
  description = "RDS instance endpoint."
  value       = aws_db_instance.this.endpoint
}

output "instance_address" {
  description = "RDS instance DNS address."
  value       = aws_db_instance.this.address
}

output "database_name" {
  description = "Application database name."
  value       = aws_db_instance.this.db_name
}

output "security_group_id" {
  description = "RDS security group ID."
  value       = aws_security_group.this.id
}

output "master_user_secret_arn" {
  description = "AWS-managed RDS master user secret ARN."
  value       = try(aws_db_instance.this.master_user_secret[0].secret_arn, null)
  sensitive   = true
}
