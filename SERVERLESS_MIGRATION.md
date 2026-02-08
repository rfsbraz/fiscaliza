# Serverless Migration Guide

## Overview

This guide provides a comprehensive path to migrate your Portuguese Parliament Flask application from ECS Fargate to AWS Lambda using the **AWS Lambda Web Adapter**. This approach requires **zero code changes** to your Flask application.

## Architecture Comparison

### Current (ECS Fargate)
- **Infrastructure**: VPC, ALB, ECS Cluster, Fargate Tasks
- **Cost**: ~$176/month (2 x 512 CPU, 1024MB tasks running 24/7)
- **Scaling**: Auto-scaling based on CPU/memory metrics
- **Cold Start**: None (always running)

### Serverless (AWS Lambda)
- **Infrastructure**: Lambda Function, Function URL, CloudFront
- **Cost**: ~$2-20/month (pay-per-request model)
- **Scaling**: Automatic (0 to 1000+ concurrent executions)
- **Cold Start**: 1-3 seconds for first request after idle period

## Migration Approaches

### 1. AWS Lambda Web Adapter (Recommended - Zero Code Changes)

**Pros:**
- ✅ **Zero code changes** required
- ✅ Existing Flask routes work unchanged
- ✅ Embedded SQLite database works as-is
- ✅ Fastest migration path (1-2 hours)
- ✅ Easy rollback to Fargate if needed

**Cons:**
- ⚠️ Cold start latency (1-3 seconds)
- ⚠️ 15-minute execution timeout limit
- ⚠️ Limited to 10GB memory

### 2. Native Lambda Functions (Not Recommended)

**Pros:**
- ✅ Potentially better performance
- ✅ More granular function-level scaling

**Cons:**
- ❌ Requires significant code restructuring
- ❌ Need to rewrite Flask routes as Lambda handlers
- ❌ Database migration required (SQLite → DynamoDB/Aurora)
- ❌ 2-4 weeks development time
- ❌ Complex state management

## Cost Analysis

### Current Fargate Costs (Monthly)
```
ECS Fargate (2 tasks):
- vCPU: 2 × 0.5 × 0.04856 × 730 hours = $35.46
- Memory: 2 × 1GB × 0.00532 × 730 hours = $7.77
- ALB: $18.00
- Data Transfer: ~$10-20
- CloudWatch Logs: ~$5
- VPC Endpoints: ~$100
Total: ~$176/month
```

### Serverless Lambda Costs (Monthly)
```
Lambda (1M requests, 2s avg duration):
- Requests: 1,000,000 × $0.0000002 = $0.20
- Duration: 1M × 2s × 1024MB × $0.0000166667 = $34.13
- Function URLs: Free
- CloudWatch Logs: ~$2
- S3 (frontend): ~$0.50
Total: ~$37/month (for 1M requests)

For typical usage (100K requests/month): ~$4/month
```

### Break-even Analysis
- **Low traffic** (< 50K requests/month): Lambda saves 95% costs
- **Medium traffic** (100K-500K requests/month): Lambda saves 70-80% costs  
- **High traffic** (> 2M requests/month): Fargate may be more cost-effective

## Migration Steps

### Phase 1: Preparation (30 minutes)

1. **Backup Current Deployment**
   ```bash
   # Create backup of current database
   cp parlamento.db parlamento.db.backup.$(date +%Y%m%d_%H%M%S)
   
   # Export current Terraform state
   cd terraform
   terraform show > current-state-backup.txt
   ```

2. **Verify Prerequisites**
   ```bash
   # Check AWS CLI
   aws --version
   aws sts get-caller-identity
   
   # Check Docker
   docker --version
   
   # Check Terraform
   terraform --version
   ```

### Phase 2: Build Serverless Image (15 minutes)

The `Dockerfile` is already created and ready to use:

```dockerfile
# Uses AWS Lambda Web Adapter for zero-code-change migration
FROM public.ecr.aws/lambda/python:3.12

# Install Lambda Web Adapter (this is the magic!)
COPY --from=public.ecr.aws/awsguru/aws-lambda-adapter:0.8.1 /lambda-adapter ${LAMBDA_RUNTIME_DIR}

# Copy your existing Flask app (unchanged!)
COPY app/ ${LAMBDA_TASK_ROOT}/app/
COPY config/ ${LAMBDA_TASK_ROOT}/config/
COPY parlamento.db ${LAMBDA_TASK_ROOT}/parlamento.db
COPY requirements.txt ${LAMBDA_TASK_ROOT}/

# Install dependencies
RUN pip install -r requirements.txt gunicorn

# Environment variables for Lambda Web Adapter
ENV AWS_LWA_INVOKE_MODE=response_stream
ENV AWS_LWA_PORT=8000
ENV PYTHONPATH=${LAMBDA_TASK_ROOT}

# Your Flask app runs exactly as before!
CMD ["python", "-m", "gunicorn", "--bind", "0.0.0.0:8000", "app.main:app"]
```

### Phase 3: Deploy Infrastructure (15 minutes)

Use the automated deployment script:

```bash
# Make script executable (if not already)
chmod +x scripts/deploy-serverless.sh

# Deploy serverless infrastructure
ENVIRONMENT=prod ./scripts/deploy-serverless.sh
```

Or deploy manually:

```bash
# Build and push Docker image
docker build -f Dockerfile -t parliament-serverless .

# Tag and push to ECR
aws ecr get-login-password --region eu-west-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.eu-west-1.amazonaws.com
docker tag parliament-serverless <account-id>.dkr.ecr.eu-west-1.amazonaws.com/parliament-backend-serverless:latest
docker push <account-id>.dkr.ecr.eu-west-1.amazonaws.com/parliament-backend-serverless:latest

# Deploy with Terraform
cd terraform
terraform plan -var="deployment_type=serverless" -out=serverless.tfplan
terraform apply serverless.tfplan
```

### Phase 4: Testing (15 minutes)

1. **Test Lambda Function URL**
   ```bash
   # Get the function URL from Terraform output
   FUNCTION_URL=$(terraform output -raw lambda_function_url)
   
   # Test health endpoint
   curl "${FUNCTION_URL}api/health"
   
   # Test a data endpoint
   curl "${FUNCTION_URL}api/deputados?limit=5"
   ```

2. **Test via CloudFront**
   ```bash
   # Get CloudFront URL
   CF_URL=$(terraform output -raw cloudfront_domain_name)
   
   # Test API via CloudFront
   curl "https://${CF_URL}/api/health"
   ```

### Phase 5: Frontend Deployment (15 minutes)

Deploy your React frontend to the S3 bucket:

```bash
# Build React app
cd frontend  # or wherever your React app is
npm run build

# Get S3 bucket name
S3_BUCKET=$(terraform output -raw s3_bucket_name)

# Upload to S3
aws s3 sync build/ s3://${S3_BUCKET}/ --delete

# Invalidate CloudFront cache
CF_DISTRIBUTION_ID=$(terraform output -raw cloudfront_distribution_id)
aws cloudfront create-invalidation --distribution-id ${CF_DISTRIBUTION_ID} --paths "/*"
```

## Performance Optimization

### Cold Start Mitigation

1. **Provisioned Concurrency** (adds cost but eliminates cold starts)
   ```hcl
   resource "aws_lambda_provisioned_concurrency_config" "backend" {
     function_name                     = aws_lambda_function.backend[0].function_name
     provisioned_concurrent_executions = 1
     qualifier                        = aws_lambda_function.backend[0].version
   }
   ```

2. **Memory Optimization**
   - Start with 1024MB (good balance of cost/performance)
   - Monitor CloudWatch metrics and adjust based on usage
   - Higher memory = faster CPU = potentially lower overall cost

3. **Keep-Warm Strategy**
   ```bash
   # Optional: Set up EventBridge rule to ping every 10 minutes
   aws events put-rule --name keep-lambda-warm --schedule-expression "rate(10 minutes)"
   ```

### Database Optimization

Since you're using embedded SQLite:

1. **Database Size Monitoring**
   ```bash
   # Check database size (Lambda has 10GB limit)
   ls -lh parlamento.db
   ```

2. **Read Replicas for Scaling** (if needed later)
   ```python
   # Could implement read-only database copies for heavy read workloads
   # But for current use case, single SQLite file should handle 100+ concurrent reads
   ```

## Monitoring and Observability

### CloudWatch Metrics
- **Invocations**: Number of function calls
- **Duration**: Execution time per request
- **Errors**: Failed invocations
- **Cold Starts**: Functions starting from cold state

### Log Monitoring
```bash
# Tail Lambda logs
aws logs tail /aws/lambda/parliament-prod-backend --follow

# Search for errors
aws logs filter-log-events --log-group-name /aws/lambda/parliament-prod-backend --filter-pattern "ERROR"
```

### Alerting Setup
```hcl
resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  alarm_name          = "parliament-lambda-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Sum"
  threshold           = "5"
  alarm_description   = "This metric monitors lambda errors"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    FunctionName = aws_lambda_function.backend[0].function_name
  }
}
```

## Rollback Plan

If issues arise, you can quickly rollback to Fargate:

```bash
# Rollback to Fargate deployment
cd terraform
terraform plan -var="deployment_type=fargate" -out=rollback.tfplan
terraform apply rollback.tfplan
```

The infrastructure supports both deployment types, so switching is seamless.

## Security Considerations

### IAM Permissions
The Lambda function has minimal required permissions:
- CloudWatch Logs (for logging)
- VPC access (if enabled)
- No database permissions needed (embedded SQLite)

### Network Security
- Function URL has CORS configured
- CloudFront provides DDoS protection
- No VPC required (unless accessing other AWS resources)

### Data Security
- Database is embedded in the Lambda function
- Data at rest encryption via Lambda's built-in encryption
- HTTPS enforced via CloudFront

## Limitations and Considerations

### Lambda Limits
- **Execution Time**: 15 minutes maximum
- **Memory**: 128MB to 10GB
- **Package Size**: 10GB (container images)
- **Concurrent Executions**: 1000 (can be increased)

### SQLite Considerations
- **Read-heavy workloads**: SQLite handles this well
- **Write-heavy workloads**: May need to consider Aurora Serverless
- **Concurrent writes**: SQLite has limitations, but your use case is primarily read-only

### When NOT to Use Serverless
- Consistent high traffic (> 2M requests/month)
- Long-running background jobs
- WebSocket connections
- Real-time applications requiring < 100ms response times

## Cost Optimization Tips

1. **Right-size Memory**: Monitor and adjust based on actual usage
2. **Optimize Cold Starts**: Use provisioned concurrency only if needed
3. **CloudFront Caching**: Cache static API responses where possible
4. **Request Batching**: Combine multiple operations into single requests
5. **Database Optimization**: Ensure indexes are optimized for query patterns

## Migration Timeline

**Total Time**: 1-2 hours for basic migration

- **Phase 1** (Preparation): 30 minutes
- **Phase 2** (Build): 15 minutes  
- **Phase 3** (Deploy): 15 minutes
- **Phase 4** (Testing): 15 minutes
- **Phase 5** (Frontend): 15 minutes
- **Buffer/Documentation**: 30 minutes

## Success Metrics

After migration, monitor these KPIs:

1. **Cost Reduction**: Target 70-95% cost savings
2. **Response Time**: < 3 seconds for cold starts, < 500ms for warm requests
3. **Availability**: 99.9%+ uptime
4. **Error Rate**: < 0.1%

## Conclusion

The AWS Lambda Web Adapter approach provides the fastest and lowest-risk path to serverless migration. Your Flask application runs unchanged, and you get immediate cost savings with improved scalability.

The architecture is production-ready and can handle significant traffic while maintaining the flexibility to rollback or scale further as needed.