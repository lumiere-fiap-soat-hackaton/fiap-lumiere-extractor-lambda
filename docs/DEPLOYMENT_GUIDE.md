# Deployment Guide

## Quick Start

This guide provides step-by-step instructions for deploying the FIAP Lumiere Media Processor Lambda function using GitHub Actions.

## Prerequisites

1. **AWS Account**: Access to AWS account with appropriate permissions
2. **GitHub Repository**: Repository with admin access to configure secrets
3. **Lambda Function**: Pre-existing Lambda function created by Terraform infrastructure

## Setup Instructions

### 1. Configure GitHub Secrets

Before the pipeline can deploy to AWS, you need to configure the required secrets:

1. Navigate to your GitHub repository
2. Go to **Settings** → **Secrets and variables** → **Actions**
3. Add the following repository secrets:

| Secret Name | Description | Example |
|-------------|-------------|---------|
| `AWS_ACCESS_KEY_ID` | AWS access key ID | `AKIAIOSFODNN7EXAMPLE` |
| `AWS_SECRET_ACCESS_KEY` | AWS secret access key | `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY` |
| `AWS_SESSION_TOKEN` | AWS session token | `AgoJb3JpZ2luX2VjEJr//...` |

### 2. Verify AWS Permissions

Ensure your AWS credentials have the following permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "lambda:UpdateFunctionCode",
        "lambda:UpdateFunctionConfiguration",
        "lambda:GetFunction",
        "lambda:PublishLayerVersion",
        "lambda:ListLayerVersions",
        "lambda:InvokeFunction"
      ],
      "Resource": [
        "arn:aws:lambda:us-east-1:904106077871:function:FiapLumiereMediaProcessorLambda",
        "arn:aws:lambda:us-east-1:904106077871:layer:VideoExtractorDependencies:*"
      ]
    }
  ]
}
```

### 3. Trigger Deployment

The deployment is automatically triggered when:

- Code is pushed to the `main` branch
- A pull request is merged to the `main` branch

Manual deployment can be triggered by:

1. Go to **Actions** tab in your GitHub repository
2. Select the **Deploy Lambda Function** workflow
3. Click **Run workflow** and select the `main` branch

## Deployment Process

### Stage 1: Lint and Test

The pipeline first runs code quality checks and tests:

1. **Code Linting**: Checks Python code style with flake8
2. **Code Formatting**: Verifies code formatting with black
3. **Unit Tests**: Runs pytest with coverage reporting

### Stage 2: Build and Deploy

If tests pass, the pipeline proceeds with deployment:

1. **Layer Build**: Creates Lambda layer with dependencies
2. **Function Build**: Packages Lambda function code
3. **Layer Deployment**: Publishes new layer version to AWS
4. **Function Deployment**: Updates Lambda function code and configuration
5. **Verification**: Confirms successful deployment

## Monitoring Deployment

### GitHub Actions

Monitor deployment progress in the GitHub Actions interface:

1. Go to **Actions** tab
2. Click on the running workflow
3. Expand job steps to see detailed logs

### AWS Console

Verify deployment in AWS Lambda Console:

1. Navigate to AWS Lambda service
2. Find function: `FiapLumiereMediaProcessorLambda`
3. Check **Configuration** tab for layer updates
4. Review **Monitoring** tab for recent activity

## Troubleshooting

### Common Issues

#### 1. Authentication Failures

**Error**: `Unable to locate credentials`

**Solution**:
- Verify AWS secrets are correctly set in GitHub
- Check secret names match exactly: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`
- Ensure credentials are not expired

#### 2. Permission Denied

**Error**: `Access denied` or `User: arn:aws:sts::... is not authorized to perform: lambda:UpdateFunctionCode`

**Solution**:
- Review IAM permissions for the user/role
- Ensure the policy includes all required Lambda permissions
- Verify the function ARN is correct

#### 3. Layer Size Limits

**Error**: `Unzipped size must be smaller than 262144000 bytes`

**Solution**:
- Review dependencies in `lambda-layer/requirements.txt`
- Consider removing unnecessary dependencies
- Use smaller alternative packages where possible

#### 4. Function Not Found

**Error**: `ResourceNotFoundException: The resource you requested does not exist`

**Solution**:
- Verify the Lambda function name and ARN are correct
- Ensure the function exists in the specified region (us-east-1)
- Check if Terraform infrastructure has been deployed

### Debugging Steps

1. **Check Pipeline Logs**:
   - Go to GitHub Actions → Failed workflow
   - Expand failed steps to see detailed error messages

2. **Verify AWS Resources**:
   - Check if Lambda function exists in AWS Console
   - Verify function name matches pipeline configuration

3. **Test AWS Credentials**:
   - Use AWS CLI locally with same credentials
   - Test basic operations: `aws lambda list-functions`

4. **Validate Dependencies**:
   - Check if all requirements can be installed locally
   - Verify Python version compatibility

## Rollback Procedures

If deployment fails or introduces issues:

### 1. Automatic Rollback

AWS Lambda automatically retains previous versions:

1. Go to AWS Lambda Console
2. Select the function
3. Click **Versions** tab
4. Use **Actions** → **Promote to $LATEST** for previous version

### 2. Manual Rollback

Revert to a previous commit:

1. Identify the last working commit
2. Create a new commit reverting changes
3. Push to `main` branch to trigger new deployment

### 3. Emergency Rollback

For critical issues:

1. Use AWS CLI to update function code directly
2. Upload previous deployment package
3. Update function configuration if needed

## Best Practices

1. **Test Locally**: Always test changes locally before pushing
2. **Small Changes**: Make incremental changes for easier debugging
3. **Monitor Logs**: Watch CloudWatch logs after deployment
4. **Documentation**: Update documentation with any configuration changes
5. **Backup**: Keep copies of working deployment packages

## Support

For deployment issues:

1. Check this documentation
2. Review GitHub Actions logs
3. Check AWS CloudWatch logs
4. Consult AWS Lambda documentation
5. Contact the development team

## Configuration Reference

### Environment Variables

| Variable | Value | Description |
|----------|-------|-------------|
| `AWS_REGION` | `us-east-1` | AWS region for deployment |
| `LAMBDA_FUNCTION_NAME` | `FiapLumiereMediaProcessorLambda` | Lambda function name |
| `PYTHON_VERSION` | `3.9` | Python runtime version |

### File Locations

| File | Purpose |
|------|---------|
| `.github/workflows/deploy.yml` | CI/CD pipeline configuration |
| `src/` | Lambda function source code |
| `lambda-layer/requirements.txt` | Layer dependencies |
| `requirements-dev.txt` | Development dependencies |
| `tests/` | Test files |

### AWS Resources

| Resource | Type | Purpose |
|----------|------|---------|
| `FiapLumiereMediaProcessorLambda` | Lambda Function | Main application logic |
| `VideoExtractorDependencies` | Lambda Layer | External dependencies |
