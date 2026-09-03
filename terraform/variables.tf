variable "aws_region" {
  type    = string
  default = "us-east-1"
}
variable "project" {
  type    = string
  default = "pulse"
}
variable "lastfm_api_key" {
  type      = string
  sensitive = true
}
variable "alert_email" {
  type    = string
  default = "charanlokku15@gmail.com"
}
variable "schedule_expression" {
  type    = string
  default = "cron(0 9 * * ? *)"
}
variable "image_tag" {
  type    = string
  default = "latest"
}
variable "task_cpu" {
  type    = string
  default = "512"
}
variable "task_memory" {
  type    = string
  default = "1024"
}
