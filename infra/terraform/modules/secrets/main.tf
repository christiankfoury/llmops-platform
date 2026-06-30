resource "aws_secretsmanager_secret" "this" {
  for_each = toset(var.secret_names)

  name                    = "${var.name_prefix}/${each.key}"
  description             = "Placeholder secret for ${each.key}; secret values are created outside Terraform state."
  recovery_window_in_days = var.recovery_window_in_days

  tags = merge(var.tags, {
    Name = "${var.name_prefix}/${each.key}"
  })
}
