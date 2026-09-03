output "ecr_repository_url" {
  value = aws_ecr_repository.pulse.repository_url
}
output "ecs_cluster_name" {
  value = aws_ecs_cluster.pulse.name
}
output "task_definition_family" {
  value = aws_ecs_task_definition.pulse.family
}
output "log_group" {
  value = aws_cloudwatch_log_group.pulse.name
}
output "schedule_name" {
  value = aws_scheduler_schedule.daily.name
}
output "sns_topic_arn" {
  value = aws_sns_topic.alerts.arn
}
output "subnets" {
  value = data.aws_subnets.default.ids
}
output "security_group" {
  value = data.aws_security_group.default.id
}
