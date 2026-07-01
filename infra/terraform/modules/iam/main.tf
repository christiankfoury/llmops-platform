locals {
  create_github_actions_role = var.create_github_actions_role && var.github_repository != ""
  allow_eks_describe         = local.create_github_actions_role && var.eks_cluster_name != ""
}

data "aws_caller_identity" "current" {
  count = local.allow_eks_describe ? 1 : 0
}

data "aws_partition" "current" {
  count = local.allow_eks_describe ? 1 : 0
}

data "aws_region" "current" {
  count = local.allow_eks_describe ? 1 : 0
}

resource "aws_iam_openid_connect_provider" "github" {
  count = local.create_github_actions_role ? 1 : 0

  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = var.github_oidc_thumbprints

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-github-oidc"
  })
}

data "aws_iam_policy_document" "github_actions_assume" {
  count = local.create_github_actions_role ? 1 : 0

  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    effect  = "Allow"

    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github[0].arn]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      values = [
        "repo:${var.github_repository}:ref:refs/heads/main",
        "repo:${var.github_repository}:environment:${var.environment}"
      ]
    }
  }
}

resource "aws_iam_role" "github_actions" {
  count = local.create_github_actions_role ? 1 : 0

  name               = "${var.name_prefix}-github-actions"
  assume_role_policy = data.aws_iam_policy_document.github_actions_assume[0].json

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-github-actions"
  })
}

data "aws_iam_policy_document" "github_actions_ecr" {
  count = local.create_github_actions_role ? 1 : 0

  statement {
    sid = "EcrAuthTokenRequiresWildcard"
    actions = [
      "ecr:GetAuthorizationToken"
    ]
    resources = ["*"]
  }

  statement {
    sid = "PublishImagesToPlatformRepositories"
    actions = [
      "ecr:BatchCheckLayerAvailability",
      "ecr:BatchGetImage",
      "ecr:CompleteLayerUpload",
      "ecr:DescribeRepositories",
      "ecr:InitiateLayerUpload",
      "ecr:PutImage",
      "ecr:UploadLayerPart"
    ]
    resources = var.ecr_repository_arns
  }

  dynamic "statement" {
    for_each = local.allow_eks_describe ? [1] : []

    content {
      sid       = "DescribeEksClusterForKubeconfig"
      actions   = ["eks:DescribeCluster"]
      resources = ["arn:${data.aws_partition.current[0].partition}:eks:${data.aws_region.current[0].name}:${data.aws_caller_identity.current[0].account_id}:cluster/${var.eks_cluster_name}"]
    }
  }
}

resource "aws_iam_policy" "github_actions_ecr" {
  count = local.create_github_actions_role ? 1 : 0

  name        = "${var.name_prefix}-github-actions-ecr"
  description = "Least-privilege ECR publish and EKS describe policy for Production AI Platform CI/CD."
  policy      = data.aws_iam_policy_document.github_actions_ecr[0].json

  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "github_actions_ecr" {
  count = local.create_github_actions_role ? 1 : 0

  role       = aws_iam_role.github_actions[0].name
  policy_arn = aws_iam_policy.github_actions_ecr[0].arn
}
