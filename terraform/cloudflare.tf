# CloudFlare DNS Configuration
# Frontend: Main domain points to S3 static website
# API: Subdomain points to ALB/ECS

# Main domain CNAME record pointing to CloudFront or S3 static website
resource "cloudflare_record" "main" {
  count = var.cloudflare_zone_id != "" ? 1 : 0

  zone_id = var.cloudflare_zone_id
  name    = var.domain_name
  content = var.enable_cloudfront_for_website ? aws_cloudfront_distribution.static_website[0].domain_name : aws_s3_bucket_website_configuration.static_website.website_endpoint
  type    = "CNAME"
  proxied = true # CloudFlare proxy mode - SSL termination, bucket name matches domain
  ttl     = 1    # Auto TTL when proxied

  comment = var.enable_cloudfront_for_website ? "Main domain pointing to CloudFront distribution" : "Main domain pointing to S3 static website with CloudFlare SSL"
}

# WWW subdomain CNAME record pointing to CloudFront or S3 static website
resource "cloudflare_record" "www" {
  count = var.cloudflare_zone_id != "" ? 1 : 0

  zone_id = var.cloudflare_zone_id
  name    = "www"
  content = var.enable_cloudfront_for_website ? aws_cloudfront_distribution.static_website[0].domain_name : aws_s3_bucket_website_configuration.static_website.website_endpoint
  type    = "CNAME"
  proxied = true # CloudFlare proxy mode - SSL termination, bucket name matches domain
  ttl     = 1    # Auto TTL when proxied

  comment = var.enable_cloudfront_for_website ? "WWW subdomain pointing to CloudFront distribution" : "WWW subdomain pointing to S3 static website with CloudFlare SSL"
}

# API subdomain CNAME record pointing to ALB (for backend API)
resource "cloudflare_record" "api" {
  count = var.cloudflare_zone_id != "" && var.enable_alb ? 1 : 0

  zone_id = var.cloudflare_zone_id
  name    = var.api_subdomain
  content = aws_lb.main[0].dns_name
  type    = "CNAME"
  proxied = false # DNS-only mode for API, ALB handles SSL
  ttl     = 300   # 5 minutes TTL for DNS-only

  comment = "API subdomain pointing to ALB with SSL termination"
}

# CloudFlare Cache Settings - Disable caching for development
resource "cloudflare_zone_settings_override" "fiscaliza" {
  count   = var.cloudflare_zone_id != "" ? 1 : 0
  zone_id = var.cloudflare_zone_id

  settings {
    # SSL mode: flexible = HTTPS to CloudFlare, HTTP to origin (port 80)
    ssl = "flexible"

    # Minimal caching to prevent stale content issues
    cache_level = "basic"

    # Browser cache TTL - minimal (120 seconds - CloudFlare minimum)
    browser_cache_ttl = 120

    # Always use HTTPS
    always_use_https = "on"

    # Security settings
    security_level = "medium"

    # Development mode - bypasses cache
    development_mode = "on"
  }
}

# Page Rules to disable caching for specific paths
resource "cloudflare_page_rule" "disable_cache_all" {
  count    = var.cloudflare_zone_id != "" ? 1 : 0
  zone_id  = var.cloudflare_zone_id
  target   = "${var.domain_name}/*"
  priority = 1

  actions {
    cache_level       = "bypass"
    browser_cache_ttl = 120
  }
}

# Output the retrieved IP for debugging - Temporarily disabled
# output "ecs_task_ip_status" {
#   description = "Status of ECS task IP retrieval"
#   value = var.cloudflare_zone_id != "" ? {
#     ip     = data.external.ecs_task_ip[0].result.ip
#     status = data.external.ecs_task_ip[0].result.status
#   } : {
#     ip     = "not_configured"
#     status = "cloudflare_zone_id_not_set"
#   }
# }