# Dedicated add-on identities keep CNI/storage AWS privileges off the node role.
locals {
  addon_identities = {
    vpc_cni = {
      service_account = "aws-node"
      policy_arn      = "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy"
    }
    ebs_csi = {
      service_account = "ebs-csi-controller-sa"
      policy_arn      = "arn:aws:iam::aws:policy/service-role/AmazonEBSCSIDriverPolicy"
    }
  }
}

data "aws_iam_policy_document" "addon_assume" {
  for_each = local.addon_identities
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.cluster.arn]
    }
    condition {
      test     = "StringEquals"
      variable = "${replace(aws_eks_cluster.this.identity[0].oidc[0].issuer, "https://", "")}:aud"
      values   = ["sts.amazonaws.com"]
    }
    condition {
      test     = "StringEquals"
      variable = "${replace(aws_eks_cluster.this.identity[0].oidc[0].issuer, "https://", "")}:sub"
      values   = ["system:serviceaccount:kube-system:${each.value.service_account}"]
    }
  }
}

resource "aws_iam_role" "addon" {
  for_each           = local.addon_identities
  name               = "${var.name_prefix}-${replace(each.key, "_", "-")}"
  assume_role_policy = data.aws_iam_policy_document.addon_assume[each.key].json
  tags               = var.tags
}

resource "aws_iam_role_policy_attachment" "addon" {
  for_each   = local.addon_identities
  role       = aws_iam_role.addon[each.key].name
  policy_arn = each.value.policy_arn
  # AWS managed policies contain documented EC2 discovery/create permissions;
  # only the exact CNI/CSI service account can assume its own role.
}

resource "aws_eks_addon" "vpc_cni" {
  cluster_name                = aws_eks_cluster.this.name
  addon_name                  = "vpc-cni"
  addon_version               = var.addon_versions.vpc_cni
  service_account_role_arn    = aws_iam_role.addon["vpc_cni"].arn
  resolve_conflicts_on_create = "NONE"
  resolve_conflicts_on_update = "NONE"
  preserve                    = true
  configuration_values = jsonencode({
    enableNetworkPolicy = "true"
    env = {
      NETWORK_POLICY_ENFORCING_MODE = "strict"
    }
  })
  tags       = var.tags
  depends_on = [aws_iam_role_policy_attachment.addon]
}

resource "aws_eks_addon" "kube_proxy" {
  cluster_name                = aws_eks_cluster.this.name
  addon_name                  = "kube-proxy"
  addon_version               = var.addon_versions.kube_proxy
  resolve_conflicts_on_create = "NONE"
  resolve_conflicts_on_update = "NONE"
  preserve                    = true
  tags                        = var.tags
}

# Strict CNI starts ordinary pods in default deny. Install bootstrap namespace,
# DNS/control-plane and controller policies BEFORE enabling these ordinary-pod add-ons.
resource "aws_eks_addon" "coredns" {
  count                       = var.bootstrap_addons_enabled ? 1 : 0
  cluster_name                = aws_eks_cluster.this.name
  addon_name                  = "coredns"
  addon_version               = var.addon_versions.coredns
  resolve_conflicts_on_create = "NONE"
  resolve_conflicts_on_update = "NONE"
  preserve                    = true
  tags                        = var.tags
  depends_on                  = [aws_eks_node_group.managed]
}

resource "aws_eks_addon" "ebs_csi" {
  count                       = var.bootstrap_addons_enabled ? 1 : 0
  cluster_name                = aws_eks_cluster.this.name
  addon_name                  = "aws-ebs-csi-driver"
  addon_version               = var.addon_versions.ebs_csi
  service_account_role_arn    = aws_iam_role.addon["ebs_csi"].arn
  resolve_conflicts_on_create = "NONE"
  resolve_conflicts_on_update = "NONE"
  preserve                    = true
  tags                        = var.tags
  depends_on                  = [aws_eks_node_group.managed, aws_iam_role_policy_attachment.addon]
}

# HPA in staging/prod requires the resource metrics API; no implicit add-on selection.
resource "aws_eks_addon" "metrics_server" {
  count                       = var.bootstrap_addons_enabled ? 1 : 0
  cluster_name                = aws_eks_cluster.this.name
  addon_name                  = "metrics-server"
  addon_version               = var.addon_versions.metrics_server
  resolve_conflicts_on_create = "NONE"
  resolve_conflicts_on_update = "NONE"
  preserve                    = true
  tags                        = var.tags
  depends_on                  = [aws_eks_node_group.managed]
}
