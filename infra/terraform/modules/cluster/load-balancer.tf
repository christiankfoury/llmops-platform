# Policy is the unmodified, checksum-recorded upstream v3.5.0 policy. Its wildcard
# discovery/create statements are required by the controller; tag conditions scope mutations.
data "aws_iam_policy_document" "load_balancer_assume" {
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
      values   = ["system:serviceaccount:kube-system:aws-load-balancer-controller"]
    }
  }
}
resource "aws_iam_role" "load_balancer" {
  name               = "${var.name_prefix}-load-balancer-controller"
  assume_role_policy = data.aws_iam_policy_document.load_balancer_assume.json
  tags               = var.tags
}
resource "aws_iam_policy" "load_balancer" {
  name   = "${var.name_prefix}-load-balancer-controller"
  policy = file("${path.module}/policies/aws-load-balancer-controller-v3.5.0.json")
  tags   = var.tags
}
resource "aws_iam_role_policy_attachment" "load_balancer" {
  role       = aws_iam_role.load_balancer.name
  policy_arn = aws_iam_policy.load_balancer.arn
}
