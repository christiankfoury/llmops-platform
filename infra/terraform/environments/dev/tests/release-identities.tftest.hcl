mock_provider "aws" {
  mock_data "aws_iam_policy_document" {
    defaults = { json = "{\"Version\":\"2012-10-17\",\"Statement\":[]}" }
  }
}

run "separate_publisher_application_and_migration_identities" {
  command = plan
  module {
    source = "../../modules/iam"
  }
  variables {
    name_prefix                = "production-ai-platform-dev"
    environment                = "dev"
    create_github_actions_role = true
    github_repository          = "example/platform"
    eks_cluster_name           = "production-ai-platform-dev-eks"
    ecr_repository_arns        = ["arn:aws:ecr:us-east-1:123456789012:repository/platform-dev/api"]
  }
  assert {
    condition     = aws_iam_role_policy_attachment.github_actions_ecr[0].role == aws_iam_role.github_publisher[0].name
    error_message = "Only the distinct publisher receives ECR write permissions."
  }
  assert {
    condition     = jsondecode(aws_iam_role_policy.github_application[0].policy).Statement[0].Action == ["eks:DescribeCluster"]
    error_message = "Application deployment must not receive ECR publishing or cloud management permissions."
  }
  assert {
    condition     = !contains(flatten([for statement in data.aws_iam_policy_document.github_actions_ecr[0].statement : tolist(statement.actions)]), "eks:DescribeCluster")
    error_message = "Publisher cannot describe or administer EKS."
  }
  assert {
    condition = one(one([
      for condition in one(data.aws_iam_policy_document.publisher_assume[0].statement).condition : condition.values
      if condition.variable == "token.actions.githubusercontent.com:sub"
    ])) == "repo:example/platform:environment:dev-publish"
    error_message = "Publishing requires its exact protected GitHub environment subject."
  }
}
