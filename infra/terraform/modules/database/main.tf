resource "aws_security_group" "this" {
  name        = "${var.name_prefix}-postgres"
  description = "PostgreSQL access for ${var.name_prefix}"
  vpc_id      = var.vpc_id
  egress      = []

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-postgres"
  })
}

resource "aws_security_group_rule" "ingress" {
  for_each = { for index, id in var.allowed_security_group_ids : tostring(index) => id }

  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  security_group_id        = aws_security_group.this.id
  source_security_group_id = each.value
  description              = "Allow PostgreSQL from approved platform workloads."
}

resource "aws_db_subnet_group" "this" {
  name       = "${var.name_prefix}-postgres"
  subnet_ids = var.private_subnet_ids

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-postgres"
  })
}

resource "aws_db_instance" "this" {
  identifier = "${var.name_prefix}-postgres"

  engine         = "postgres"
  engine_version = var.engine_version
  instance_class = var.instance_class

  db_name  = var.database_name
  username = var.master_username

  manage_master_user_password = true

  allocated_storage     = var.allocated_storage_gb
  max_allocated_storage = var.max_allocated_storage_gb
  storage_encrypted     = true
  storage_type          = "gp3"

  backup_retention_period = var.backup_retention_days
  backup_window           = var.backup_window
  maintenance_window      = var.maintenance_window
  copy_tags_to_snapshot   = true
  deletion_protection     = var.deletion_protection
  skip_final_snapshot     = var.skip_final_snapshot
  final_snapshot_identifier = var.skip_final_snapshot ? null : (
    "${var.name_prefix}-postgres-final"
  )

  multi_az            = var.multi_az
  publicly_accessible = false

  db_subnet_group_name   = aws_db_subnet_group.this.name
  vpc_security_group_ids = [aws_security_group.this.id]

  performance_insights_enabled = var.performance_insights_enabled

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-postgres"
  })
}
