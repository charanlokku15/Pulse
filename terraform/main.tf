resource "aws_ecr_repository" "pulse" {
  name                 = "${var.project}-pipeline"
  image_tag_mutability = "MUTABLE"
  force_delete         = true
  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ssm_parameter" "lastfm_api_key" {
  name  = "/pulse/lastfm_api_key"
  type  = "SecureString"
  value = var.lastfm_api_key
}

resource "aws_cloudwatch_log_group" "pulse" {
  name              = "/ecs/${var.project}"
  retention_in_days = 30
}

resource "aws_ecs_cluster" "pulse" {
  name = "${var.project}-cluster"
}

resource "aws_ecs_task_definition" "pulse" {
  family                   = "${var.project}-pipeline"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.task_cpu
  memory                   = var.task_memory
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn

  runtime_platform {
    cpu_architecture        = "ARM64"
    operating_system_family = "LINUX"
  }

  container_definitions = jsonencode([
    {
      name      = "pulse"
      image     = local.image_uri
      essential = true
      environment = [
        { name = "S3_BUCKET", value = local.bucket_name },
        { name = "AWS_DEFAULT_REGION", value = var.aws_region },
      ]
      secrets = [
        {
          name      = "LASTFM_API_KEY"
          valueFrom = aws_ssm_parameter.lastfm_api_key.arn
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.pulse.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "pulse"
        }
      }
    }
  ])
}

resource "aws_scheduler_schedule" "daily" {
  name = "${var.project}-daily"
  flexible_time_window {
    mode = "OFF"
  }
  schedule_expression = var.schedule_expression
  target {
    arn      = aws_ecs_cluster.pulse.arn
    role_arn = aws_iam_role.scheduler.arn
    ecs_parameters {
      task_definition_arn = aws_ecs_task_definition.pulse.arn_without_revision
      launch_type         = "FARGATE"
      network_configuration {
        subnets          = data.aws_subnets.default.ids
        security_groups  = [data.aws_security_group.default.id]
        assign_public_ip = true
      }
    }
  }
}

resource "aws_sns_topic" "alerts" {
  name = "${var.project}-alerts"
}

resource "aws_sns_topic_subscription" "email" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

resource "aws_cloudwatch_log_metric_filter" "errors" {
  name           = "${var.project}-errors"
  log_group_name = aws_cloudwatch_log_group.pulse.name
  pattern        = "?ERROR ?Error ?\"exited with\" ?\"FAIL \""
  metric_transformation {
    name          = "PulsePipelineErrors"
    namespace     = "Pulse"
    value         = "1"
    default_value = "0"
  }
}

resource "aws_cloudwatch_metric_alarm" "failure" {
  alarm_name          = "${var.project}-pipeline-failure"
  alarm_description   = "Pulse pipeline logged an error or failed"
  namespace           = "Pulse"
  metric_name         = "PulsePipelineErrors"
  statistic           = "Sum"
  period              = 86400
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alerts.arn]
}
