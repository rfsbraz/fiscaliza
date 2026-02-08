# S3 Static Website for Frontend
# Hosts the React/Vue frontend application
# CloudFlare points to this for the main domain

# S3 Bucket for static website
# Bucket name MUST match domain name exactly for S3 website hosting with custom domain
resource "aws_s3_bucket" "static_website" {
  bucket = var.domain_name

  tags = merge(local.storage_tags, {
    Name         = var.domain_name
    ResourceType = "s3-bucket"
    Purpose      = "static-website-hosting"
    Billable     = "true"
  })
}

# S3 Bucket public access configuration
resource "aws_s3_bucket_public_access_block" "static_website" {
  bucket = aws_s3_bucket.static_website.id

  block_public_acls       = var.enable_cloudfront_for_website ? true : false
  block_public_policy     = var.enable_cloudfront_for_website ? true : false
  ignore_public_acls      = var.enable_cloudfront_for_website ? true : false
  restrict_public_buckets = var.enable_cloudfront_for_website ? true : false
}

# S3 Bucket website configuration
resource "aws_s3_bucket_website_configuration" "static_website" {
  bucket = aws_s3_bucket.static_website.id

  index_document {
    suffix = "index.html"
  }

  error_document {
    key = "index.html" # SPA routing - all errors go to index.html
  }
}

# S3 Bucket policy for CloudFront or public access
resource "aws_s3_bucket_policy" "static_website" {
  bucket = aws_s3_bucket.static_website.id

  policy = var.enable_cloudfront_for_website ? jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowCloudFrontServicePrincipal"
        Effect = "Allow"
        Principal = {
          Service = "cloudfront.amazonaws.com"
        }
        Action   = "s3:GetObject"
        Resource = "${aws_s3_bucket.static_website.arn}/*"
        Condition = {
          StringEquals = {
            "AWS:SourceArn" = aws_cloudfront_distribution.static_website[0].arn
          }
        }
      }
    ]
    }) : jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "PublicReadGetObject"
        Effect    = "Allow"
        Principal = "*"
        Action    = "s3:GetObject"
        Resource  = "${aws_s3_bucket.static_website.arn}/*"
      }
    ]
  })

  depends_on = [aws_s3_bucket_public_access_block.static_website]
}

# S3 Bucket versioning (optional, for rollbacks)
resource "aws_s3_bucket_versioning" "static_website" {
  bucket = aws_s3_bucket.static_website.id

  versioning_configuration {
    status = var.environment == "prod" ? "Enabled" : "Suspended"
  }
}

# S3 Bucket CORS configuration for API calls
resource "aws_s3_bucket_cors_configuration" "static_website" {
  bucket = aws_s3_bucket.static_website.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "HEAD"]
    allowed_origins = ["*"]
    expose_headers  = ["ETag"]
    max_age_seconds = 3000
  }
}

# CloudFront Origin Access Control for S3
resource "aws_cloudfront_origin_access_control" "static_website" {
  count = var.enable_cloudfront_for_website ? 1 : 0

  name                              = "${local.name_prefix}-static-website-oac"
  description                       = "OAC for static website S3 bucket"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

# SSL Certificate for CloudFront (must be in us-east-1)
resource "aws_acm_certificate" "website" {
  count    = var.enable_cloudfront_for_website ? 1 : 0
  provider = aws.us_east_1

  domain_name               = var.domain_name
  subject_alternative_names = ["www.${var.domain_name}"]
  validation_method         = "DNS"

  lifecycle {
    create_before_destroy = true
  }

  tags = merge(local.security_tags, {
    Name         = "${local.name_prefix}-website-ssl-certificate"
    ResourceType = "acm-certificate"
    Purpose      = "cloudfront-ssl-termination"
    Domain       = var.domain_name
  })
}

# SSL Certificate validation records in CloudFlare for website
resource "cloudflare_record" "website_cert_validation" {
  for_each = var.enable_cloudfront_for_website && var.cloudflare_zone_id != "" ? {
    for dvo in aws_acm_certificate.website[0].domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  } : {}

  zone_id = var.cloudflare_zone_id
  name    = each.value.name
  content = trimsuffix(each.value.record, ".")
  type    = each.value.type
  ttl     = 60
  proxied = false

  comment = "SSL certificate validation for CloudFront"
}

# Certificate validation for website
resource "aws_acm_certificate_validation" "website" {
  count    = var.enable_cloudfront_for_website && var.cloudflare_zone_id != "" ? 1 : 0
  provider = aws.us_east_1

  certificate_arn         = aws_acm_certificate.website[0].arn
  validation_record_fqdns = [for record in cloudflare_record.website_cert_validation : record.hostname]

  timeouts {
    create = "5m"
  }
}

# CloudFront distribution for static website with SSL
resource "aws_cloudfront_distribution" "static_website" {
  count = var.enable_cloudfront_for_website ? 1 : 0

  origin {
    domain_name              = aws_s3_bucket.static_website.bucket_regional_domain_name
    origin_id                = "S3-${aws_s3_bucket.static_website.bucket}"
    origin_access_control_id = aws_cloudfront_origin_access_control.static_website[0].id
  }

  enabled             = true
  is_ipv6_enabled     = true
  default_root_object = "index.html"
  price_class         = var.cloudfront_price_class

  # Cache behavior for index.html - no caching
  ordered_cache_behavior {
    path_pattern           = "index.html"
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "S3-${aws_s3_bucket.static_website.bucket}"
    compress               = true
    viewer_protocol_policy = "redirect-to-https"

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    min_ttl     = 0
    default_ttl = 0 # No caching
    max_ttl     = 0 # No caching
  }

  # Cache behavior for static assets - long cache
  default_cache_behavior {
    allowed_methods        = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "S3-${aws_s3_bucket.static_website.bucket}"
    compress               = true
    viewer_protocol_policy = "redirect-to-https"

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    min_ttl     = 0
    default_ttl = 31536000 # 1 year for static assets
    max_ttl     = 31536000 # 1 year for static assets
  }

  # Custom error pages for SPA routing
  custom_error_response {
    error_code         = 404
    response_code      = 200
    response_page_path = "/index.html"
  }

  custom_error_response {
    error_code         = 403
    response_code      = 200
    response_page_path = "/index.html"
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    acm_certificate_arn            = var.enable_cloudfront_for_website && var.cloudflare_zone_id != "" ? aws_acm_certificate_validation.website[0].certificate_arn : (var.enable_cloudfront_for_website ? aws_acm_certificate.website[0].arn : null)
    ssl_support_method             = var.enable_cloudfront_for_website ? "sni-only" : null
    minimum_protocol_version       = var.enable_cloudfront_for_website ? "TLSv1.2_2021" : null
    cloudfront_default_certificate = var.enable_cloudfront_for_website ? false : true
  }

  aliases = var.enable_cloudfront_for_website ? [var.domain_name, "www.${var.domain_name}"] : []

  tags = merge(local.storage_tags, {
    Name         = "${local.name_prefix}-cloudfront-website"
    ResourceType = "cloudfront-distribution"
    Purpose      = "static-website-cdn"
    Billable     = "true"
  })
}

# Default index.html is not needed - will be replaced by actual frontend deployment