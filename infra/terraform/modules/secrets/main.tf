resource "aws_secretsmanager_secret" "this" {
  for_each = toset(var.secret_names)

  name                    = "${var.name_prefix}/${each.key}"
  description             = "Placeholder secret for ${each.key}; secret values are created outside Terraform state."
  recovery_window_in_days = var.recovery_window_in_days

  tags = merge(var.tags, {
    Name = "${var.name_prefix}/${each.key}"
  })
}

locals {
  external_secrets_oidc_issuer = var.eks_oidc_issuer_url == null ? "" : replace(var.eks_oidc_issuer_url, "https://", "")
  # Instance keys depend only on configuration, never computed cluster ARN/issuer values.
  readers = var.enable_external_secrets_irsa ? {
    runtime = {
      service_account = "ai-platform-runtime-secrets"
      secret_names    = ["runtime", "web-session"]
    }
    migration = {
      service_account = "ai-platform-migration-secrets"
      secret_names    = ["migration"]
    }
  } : {}
}

data "aws_iam_policy_document" "external_secrets_assume" {
  for_each = local.readers
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals {
      type        = "Federated"
      identifiers = [var.eks_oidc_provider_arn]
    }
    condition {
      test     = "StringEquals"
      variable = "${local.external_secrets_oidc_issuer}:aud"
      values   = ["sts.amazonaws.com"]
    }
    condition {
      test     = "StringEquals"
      variable = "${local.external_secrets_oidc_issuer}:sub"
      values   = ["system:serviceaccount:${var.external_secrets_namespace}:${each.value.service_account}"]
    }
  }
}

resource "aws_iam_role" "external_secrets" {
  for_each           = local.readers
  name               = "${var.name_prefix}-${each.key}-secrets"
  assume_role_policy = data.aws_iam_policy_document.external_secrets_assume[each.key].json
  tags               = var.tags
}

data "aws_iam_policy_document" "external_secrets_read" {
  for_each = local.readers
  statement {
    sid       = "ReadSelectedPlatformSecrets"
    actions   = ["secretsmanager:DescribeSecret", "secretsmanager:GetSecretValue"]
    resources = [for name in each.value.secret_names : aws_secretsmanager_secret.this[name].arn]
  }
}

resource "aws_iam_policy" "external_secrets_read" {
  for_each    = local.readers
  name        = "${var.name_prefix}-${each.key}-secrets-read"
  description = "Read only the ${each.key} secret containers through the dedicated reader identity."
  policy      = data.aws_iam_policy_document.external_secrets_read[each.key].json
  tags        = var.tags
}

resource "aws_iam_role_policy_attachment" "external_secrets_read" {
  for_each   = local.readers
  role       = aws_iam_role.external_secrets[each.key].name
  policy_arn = aws_iam_policy.external_secrets_read[each.key].arn
}
