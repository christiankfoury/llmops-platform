data "aws_iam_policy_document" "cluster_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    effect  = "Allow"

    principals {
      type        = "Service"
      identifiers = ["eks.amazonaws.com"]
    }
  }
}

data "aws_caller_identity" "current" {}

resource "aws_iam_role" "cluster" {
  name               = "${var.name_prefix}-eks-cluster"
  assume_role_policy = data.aws_iam_policy_document.cluster_assume.json

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-eks-cluster"
  })
}

resource "aws_iam_role_policy_attachment" "cluster" {
  for_each = toset([
    "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
  ])

  role       = aws_iam_role.cluster.name
  policy_arn = each.value
}

data "aws_iam_policy_document" "cluster_secrets_kms" {
  statement {
    sid     = "EnableAccountKeyAdministration"
    actions = ["kms:*"]

    principals {
      type        = "AWS"
      identifiers = ["arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"]
    }

    resources = ["*"]
  }

  statement {
    sid = "AllowEksClusterSecretsEncryption"
    actions = [
      "kms:CreateGrant",
      "kms:Decrypt",
      "kms:DescribeKey",
      "kms:Encrypt",
      "kms:GenerateDataKey",
      "kms:ListGrants",
      "kms:ReEncryptFrom",
      "kms:ReEncryptTo",
      "kms:RevokeGrant"
    ]

    principals {
      type        = "AWS"
      identifiers = [aws_iam_role.cluster.arn]
    }

    resources = ["*"]
  }
}

resource "aws_kms_key" "cluster_secrets" {
  description             = "EKS Kubernetes secret envelope encryption for ${var.name_prefix}"
  deletion_window_in_days = 30
  enable_key_rotation     = true
  policy                  = data.aws_iam_policy_document.cluster_secrets_kms.json

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-eks-secrets"
  })
}

resource "aws_kms_alias" "cluster_secrets" {
  name          = "alias/${var.name_prefix}-eks-secrets"
  target_key_id = aws_kms_key.cluster_secrets.key_id
}

resource "aws_eks_cluster" "this" {
  name     = "${var.name_prefix}-eks"
  role_arn = aws_iam_role.cluster.arn
  version  = var.kubernetes_version

  enabled_cluster_log_types = var.enabled_cluster_log_types

  encryption_config {
    resources = ["secrets"]

    provider {
      key_arn = aws_kms_key.cluster_secrets.arn
    }
  }

  vpc_config {
    subnet_ids              = var.private_subnet_ids
    endpoint_private_access = var.endpoint_private_access
    endpoint_public_access  = var.endpoint_public_access
    public_access_cidrs     = var.public_access_cidrs
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-eks"
  })

  depends_on = [aws_iam_role_policy_attachment.cluster]
}

data "tls_certificate" "cluster" {
  url = aws_eks_cluster.this.identity[0].oidc[0].issuer
}

resource "aws_iam_openid_connect_provider" "cluster" {
  url = aws_eks_cluster.this.identity[0].oidc[0].issuer

  client_id_list = ["sts.amazonaws.com"]
  thumbprint_list = [
    data.tls_certificate.cluster.certificates[0].sha1_fingerprint
  ]

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-eks-oidc"
  })
}

data "aws_iam_policy_document" "node_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    effect  = "Allow"

    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "node" {
  name               = "${var.name_prefix}-eks-node"
  assume_role_policy = data.aws_iam_policy_document.node_assume.json

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-eks-node"
  })
}

resource "aws_iam_role_policy_attachment" "node" {
  for_each = toset([
    "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy",
    "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy",
    "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
  ])

  role       = aws_iam_role.node.name
  policy_arn = each.value
}

resource "aws_eks_node_group" "managed" {
  for_each = var.node_groups

  cluster_name    = aws_eks_cluster.this.name
  node_group_name = "${var.name_prefix}-${each.key}"
  node_role_arn   = aws_iam_role.node.arn
  subnet_ids      = var.private_subnet_ids

  ami_type       = each.value.ami_type
  capacity_type  = each.value.capacity_type
  disk_size      = each.value.disk_size
  instance_types = each.value.instance_types

  scaling_config {
    desired_size = each.value.desired_size
    max_size     = each.value.max_size
    min_size     = each.value.min_size
  }

  update_config {
    max_unavailable = each.value.max_unavailable
  }

  labels = merge(each.value.labels, {
    environment = var.environment
    node_group  = each.key
  })

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-${each.key}"
  })

  depends_on = [aws_iam_role_policy_attachment.node]
}

locals {
  access_policy_associations = flatten([
    for entry_name, entry in var.access_entries : [
      for policy_name, association in entry.policy_associations : {
        key           = "${entry_name}.${policy_name}"
        entry_name    = entry_name
        principal_arn = entry.principal_arn
        policy_arn    = association.policy_arn
        access_scope  = association.access_scope
      }
    ]
  ])
}

resource "aws_eks_access_entry" "this" {
  for_each = var.access_entries

  cluster_name      = aws_eks_cluster.this.name
  principal_arn     = each.value.principal_arn
  kubernetes_groups = each.value.kubernetes_groups
  type              = each.value.type

  depends_on = [aws_eks_node_group.managed]
}

resource "aws_eks_access_policy_association" "this" {
  for_each = {
    for association in local.access_policy_associations : association.key => association
  }

  cluster_name  = aws_eks_cluster.this.name
  principal_arn = each.value.principal_arn
  policy_arn    = each.value.policy_arn

  access_scope {
    type       = each.value.access_scope.type
    namespaces = each.value.access_scope.namespaces
  }

  depends_on = [aws_eks_access_entry.this]
}
