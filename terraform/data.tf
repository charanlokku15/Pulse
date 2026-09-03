data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

locals {
  bucket_name = "pulse-data-${data.aws_caller_identity.current.account_id}"
  image_uri   = "${aws_ecr_repository.pulse.repository_url}:${var.image_tag}"
}

data "aws_s3_bucket" "pulse" {
  bucket = local.bucket_name
}
data "aws_vpc" "default" {
  default = true
}
data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}
data "aws_security_group" "default" {
  vpc_id = data.aws_vpc.default.id
  name   = "default"
}
