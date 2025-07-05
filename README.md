# Fiap Lumière - Extractor Lambda Function

## Introduction

This application provides a robust, scalable, and event-driven serverless workflow on AWS. It processes videos by listening to job requests on an SQS queue, extracting all frames, and uploading them as a ZIP archive back to S3. Upon completion, it sends a notification message to another SQS queue.

**Deployment of AWS resources (Lambda, SQS Queues, IAM Roles, S3 Bucket) is managed by Terraform.** This README focuses on the application code, local development, and how to build the necessary artifacts for Terraform.

## Code Architecture (Clean Architecture)

-   **`lambda_function.py` (Adapter Layer):** The entry point for AWS Lambda. It translates the SQS event and environment variables into a clean call to the application service.
-   **`processing_service.py` (Application/Use Case Layer):** The core business logic. It orchestrates the workflow: download, extract, zip, upload, and notify. It is completely independent of AWS Lambda.
-   **`s3_handler.py`, `sqs_handler.py`, etc. (Infrastructure Layer):** Modules that handle direct interaction with external services like S3 (Boto3) and SQS.

## Workflow

1.  **Enqueue Job**: A client sends a message to the *Job Queue*. The message must contain a `request_id` and the `s3_path` of the video.
2.  **Trigger Lambda**: The Job Queue triggers the Lambda function.
3.  **Process Video**: The Lambda function executes the core processing logic.
4.  **Upload Output**: The resulting ZIP file is saved to the S3 bucket under a `processed/` prefix.
5.  **Send Notification**: A completion message containing the original `request_id` and the `result_s3_path` is sent to the *Notification Queue*.

## Prerequisites

- Python 3.9+
- AWS CLI configured
- **Docker**: Required for building dependencies and local testing with SAM CLI.
- **AWS SAM CLI**: Used for local development and building deployment artifacts. [Official guide](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html).
- **Terraform**: Used for deploying all AWS resources.

## Local Development & Testing

1.  **Clone & Install Dependencies:**
    ```bash
    git clone <your-repo-url>
    cd video-frame-extractor
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    pip install -r requirements.txt
    ```

2.  **Prepare AWS Resources for Local Testing:**
    Ensure the S3 bucket and a placeholder SQS notification queue exist in your AWS account for testing. Upload a sample video.

3.  **Update `event.json`:**
    Modify `event.json` with your test bucket, video path, and a sample `request_id`.

4.  **Build Lambda Artifacts:**
    The `sam build` command packages the function and its layer dependencies into ZIP files.
    ```bash
    sam build --use-container
    ```

5.  **Invoke the Function Locally:**
    Use `sam local invoke` with the `--env-vars` flag to provide the necessary environment variables for local testing.
    ```bash
    # env.json
    {
      "VideoExtractorFunction": {
        "NOTIFICATION_QUEUE_URL": "YOUR_TEST_NOTIFICATION_QUEUE_URL",
        "OUTPUT_BUCKET": "YOUR_TEST_BUCKET"
      }
    }
    ```
    ```bash
    sam local invoke VideoExtractorFunction \
      --event event.json \
      --env-vars env.json
    ```
    Check your terminal for logs. A ZIP file should appear in your S3 bucket, and a notification message should appear in your test notification queue.

## CI/CD Pipeline

This project includes a robust CI/CD pipeline using GitHub Actions that automates testing, building, and deployment of the Lambda function.

### Features

- **Automated Testing**: Runs linting, formatting checks, and unit tests on every push and pull request
- **Build Automation**: Creates deployment packages for both Lambda function and layer
- **Deployment**: Automatically deploys to AWS Lambda when changes are pushed to the main branch
- **Verification**: Validates successful deployment and function configuration

### Setup

1. **Configure GitHub Secrets**: Add the following secrets to your GitHub repository:
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`
   - `AWS_SESSION_TOKEN`

2. **Deploy**: Push code to the `main` branch to trigger automatic deployment

### Documentation

- [CI/CD Pipeline Documentation](docs/CICD_PIPELINE.md) - Detailed pipeline architecture and configuration
- [Deployment Guide](docs/DEPLOYMENT_GUIDE.md) - Step-by-step deployment instructions

### Local Deployment Script

For manual deployment and testing, use the provided deployment script:

```bash
# Run full pipeline (test, build, deploy)
./bin/deploy.sh

# Run tests only
./bin/deploy.sh test

# Build only
./bin/deploy.sh build

# Deploy only (requires existing build)
./bin/deploy.sh deploy

# Clean build artifacts
./bin/deploy.sh clean
```

### Pipeline Status

The pipeline runs on:
- **Push to main**: Full pipeline including deployment
- **Pull requests**: Linting and testing only

Monitor pipeline execution in the **Actions** tab of your GitHub repository.