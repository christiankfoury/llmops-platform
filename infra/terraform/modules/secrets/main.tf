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
  external_secrets_oidc_subject = "system:serviceaccount:${var.external_secrets_namespace}:${var.external_secrets_service_account}"
  external_secrets_oidc_issuer  = var.eks_oidc_issuer_url == null ? null : replace(var.eks_oidc_issuer_url, "https://", "")
  external_secrets_enabled      = var.enable_external_secrets_irsa && var.eks_oidc_provider_arn != null && var.eks_oidc_issuer_url != null
}

data "aws_iam_policy_document" "external_secrets_assume" {
  count = local.external_secrets_enabled ? 1 : 0

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
      values   = [local.external_secrets_oidc_subject]
    }
  }
}

resource "aws_iam_role" "external_secrets" {
  count = local.external_secrets_enabled ? 1 : 0

  name               = "${var.name_prefix}-external-secrets"
  assume_role_policy = data.aws_iam_policy_document.external_secrets_assume[0].json

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-external-secrets"
  })
}

data "aws_iam_policy_document" "external_secrets_read" {
  count = local.external_secrets_enabled ? 1 : 0

  statement {
    sid = "ReadPlatformSecrets"
    actions = [
      "secretsmanager:DescribeSecret",
      "secretsmanager:GetSecretValue",
      "secretsmanager:ListSecretVersionIds"
    ]
    resources = [for secret in aws_secretsmanager_secret.this : secret.arn]
  }
}

resource "aws_iam_policy" "external_secrets_read" {
  count = local.external_secrets_enabled ? 1 : 0

  name        = "${var.name_prefix}-external-secrets-read"
  description = "Allow External Secrets Operator to read ${var.name_prefix} Secrets Manager values."
  policy      = data.aws_iam_policy_document.external_secrets_read[0].json

  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "external_secrets_read" {
  count = local.external_secrets_enabled ? 1 : 0

  role       = aws_iam_role.external_secrets[0].name
  policy_arn = aws_iam_policy.external_secrets_read[0].arn
}
