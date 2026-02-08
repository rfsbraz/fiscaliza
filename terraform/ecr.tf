# ECR Repository for Parliament App Docker Images (existing repository)
# Import existing repository: terraform import aws_ecr_repository.parliament_app parliament-app

resource "aws_ecr_repository" "parliament_app" {
  name                 = "parliament-app"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true # Enable vulnerability scanning
  }

  tags = merge(local.storage_tags, {
    Name         = "${local.name_prefix}-ecr-repository"
    ResourceType = "ecr-repository"
    Purpose      = "docker-image-storage"
    Application  = "parliament-backend"
  })

  lifecycle {
    # Prevent accidental deletion of existing repository
    prevent_destroy = false
  }
}

# Lifecycle Policy to automatically delete old images
resource "aws_ecr_lifecycle_policy" "parliament_app" {
  repository = aws_ecr_repository.parliament_app.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 10 images tagged with timestamp"
        selection = {
          tagStatus     = "tagged"
          tagPrefixList = ["20"] # Matches our YYYYMMDD-HHMMSS format
          countType     = "imageCountMoreThan"
          countNumber   = 10
        }
        action = {
          type = "expire"
        }
      },
      {
        rulePriority = 2
        description  = "Keep only 1 untagged image"
        selection = {
          tagStatus   = "untagged"
          countType   = "imageCountMoreThan"
          countNumber = 1
        }
        action = {
          type = "expire"
        }
      },
      {
        rulePriority = 3
        description  = "Delete images older than 7 days"
        selection = {
          tagStatus   = "any"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = 7
        }
        action = {
          type = "expire"
        }
      }
    ]
  })

  depends_on = [aws_ecr_repository.parliament_app]
}

# Output the ECR repository URL
output "ecr_repository_url" {
  description = "URL of the ECR repository for parliament app"
  value       = aws_ecr_repository.parliament_app.repository_url
}