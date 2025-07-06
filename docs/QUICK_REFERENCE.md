# Quick Reference - CI/CD Pipeline

## GitHub Actions Workflow

### 🚀 Triggers
- **Auto Deploy**: Push to `main` branch
- **Testing**: Pull requests to `main`
- **Manual**: Actions tab → Run workflow

### 📋 Prerequisites
Configure these GitHub secrets:
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY` 
- `AWS_SESSION_TOKEN`

### 🔍 Pipeline Steps

#### Stage 1: Quality Checks
```bash
# What runs automatically:
flake8 src/           # Linting
black --check src/    # Formatting
pytest tests/         # Unit tests
```

#### Stage 2: Build & Deploy
```bash
# What runs automatically:
# 1. Build Lambda Layer (dependencies)
# 2. Build Lambda Function (source code)
# 3. Deploy to AWS Lambda
# 4. Update function configuration
# 5. Verify deployment
```

### 🛠️ Manual Deployment

```bash
# Local deployment script
./bin/deploy.sh           # Full pipeline
./bin/deploy.sh test      # Tests only
./bin/deploy.sh build     # Build only
./bin/deploy.sh deploy    # Deploy only
./bin/deploy.sh clean     # Cleanup
```

### 📍 AWS Resources

| Resource | Name | ARN |
|----------|------|-----|
| Lambda Function | `FiapLumiereMediaProcessorLambda` | `arn:aws:lambda:us-east-1:904106077871:function:FiapLumiereMediaProcessorLambda` |
| Lambda Layer | `VideoExtractorDependencies` | Auto-generated |
| Region | `us-east-1` | - |

### 🔧 Common Tasks

#### Check Pipeline Status
1. Go to **Actions** tab
2. Click on latest workflow run
3. Check job status and logs

#### Deploy Hotfix
1. Create feature branch
2. Make changes
3. Test locally: `./bin/deploy.sh test`
4. Create PR to `main`
5. Merge PR (auto-deploys)

#### Rollback
1. AWS Console → Lambda → Function
2. **Versions** tab
3. Select previous version
4. **Actions** → **Promote to $LATEST**

### 📚 Documentation Links

- [Pipeline Architecture](CICD_PIPELINE.md)
- [Deployment Guide](DEPLOYMENT_GUIDE.md)
- [Main README](../README.md)

### 🆘 Troubleshooting

| Issue | Solution |
|-------|----------|
| Authentication failed | Check GitHub secrets |
| Tests failing | Run `./bin/deploy.sh test` locally |
| Permission denied | Verify AWS IAM permissions |
| Function not found | Ensure Terraform resources exist |

### 📊 Monitoring

- **GitHub Actions**: Pipeline execution logs
- **AWS CloudWatch**: Lambda function logs
- **AWS Console**: Function configuration and metrics

### 🏁 Quick Start Checklist

- [ ] GitHub secrets configured
- [ ] AWS resources exist (via Terraform)
- [ ] Tests pass locally
- [ ] Code pushed to `main` branch
- [ ] Pipeline completes successfully
- [ ] Function tested in AWS Console
