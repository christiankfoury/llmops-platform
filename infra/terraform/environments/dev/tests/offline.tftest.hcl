# Every provider is mocked and every run is plan-only: no AWS credentials/API/resource changes.
mock_provider "aws" {
  mock_data "aws_availability_zones" {
    defaults = { names = ["us-east-1a", "us-east-1b", "us-east-1c"] }
  }
  mock_data "aws_caller_identity" {
    defaults = { account_id = "000000000000" }
  }
  mock_data "aws_partition" {
    defaults = { partition = "aws" }
  }
  mock_data "aws_region" {
    defaults = { region = "us-east-1" }
  }
  mock_data "aws_iam_policy_document" {
    defaults = { json = "{\"Version\":\"2012-10-17\",\"Statement\":[]}" }
  }
}
mock_provider "tls" {}

variables {
  bootstrap_principal_arn    = "arn:aws:iam::000000000000:role/synthetic-bootstrap"
  create_github_actions_role = true
  redis_auth_token           = "synthetic-test-token-not-a-secret"
  # Syntactically valid fixtures only; these are NOT deployment version recommendations.
  eks_addon_versions = {
    vpc_cni        = "v1.21.0-eksbuild.1"
    coredns        = "v1.12.0-eksbuild.1"
    kube_proxy     = "v1.36.0-eksbuild.1"
    ebs_csi        = "v1.50.0-eksbuild.1"
    metrics_server = "v0.8.0-eksbuild.1"
  }
}

run "new_foundation_with_computed_ids" {
  command = plan
  variables { bootstrap_addons_enabled = false }
}

run "after_bootstrap_policies_exist" {
  command = plan
  variables { bootstrap_addons_enabled = true }
}


run "terraform_owned_load_balancing" {
  command = plan
  variables {
    load_balancing = {
      internal           = true
      certificate_arn    = "arn:aws:acm:us-east-1:000000000000:certificate/00000000-0000-0000-0000-000000000000"
      access_logs_bucket = "synthetic-approved-alb-logs"
      allowed_cidrs      = ["10.0.0.0/8"]
      api_hostname       = "api.platform.example.com"
      web_hostname       = "platform.example.com"
    }
  }
  assert {
    condition     = toset(keys(output.load_balancing_bootstrap_values.targetBindings)) == toset(["ai-platform-api", "ai-platform-web"])
    error_message = "Only API and web target groups may be exposed."
  }
}
