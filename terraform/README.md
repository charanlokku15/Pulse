# Pulse — Infrastructure (Terraform)

Codifies the Pulse cloud stack: ECR, IAM roles, SSM secret, ECS/Fargate,
EventBridge Scheduler, CloudWatch logs + alarm, and SNS alerts.

The S3 bucket (pulse-data-<account>) and its raw data are intentionally NOT
managed here -- referenced read-only so destroy/apply never touch source data.

## Usage
    cp terraform.tfvars.example terraform.tfvars   # edit in your Last.fm key
    terraform init
    terraform validate
    terraform plan
    terraform apply

State and terraform.tfvars are gitignored (both can contain the secret).
