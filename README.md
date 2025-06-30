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

## Building and Deploying with Terraform

1.  **Build Artifacts:** Run `sam build --use-container`. This will create the function and layer ZIP files in the `.aws-sam/build` directory.

2.  **Terraform Deployment:** Your Terraform configuration is responsible for:
    *   Creating the S3 bucket.
    *   Creating two SQS queues: one for jobs and one for notifications (along with a DLQ for the job queue).
    *   Creating the necessary IAM roles and policies.
    *   Creating the `aws_lambda_layer_version` resource, pointing to the layer ZIP file from the build step.
    *   Creating the `aws_lambda_function` resource, pointing to the function ZIP file and attaching the layer.
    *   **Crucially**, setting the `NOTIFICATION_QUEUE_URL` environment variable on the Lambda function, providing the URL of the notification queue it just created.

## How to Use the Deployed Application

1.  **Get the Job SQS Queue URL** from your Terraform outputs.
2.  **Send a Message** with a unique `request_id` and the `s3_path` to the job queue.
    ```bash
    # Replace with your values from Terraform
    JOB_QUEUE_URL="YOUR_JOB_QUEUE_URL"
    S3_VIDEO_PATH="s3://your-bucket-name/videos/my-awesome-video.mp4"
    REQUEST_ID=$(uuidgen | tr '[:upper:]' '[:lower:]') # Generate a UUID

    aws sqs send-message \
      --queue-url "$JOB_QUEUE_URL" \
      --message-body "{\"s3_path\": \"$S3_VIDEO_PATH\", \"request_id\": \"$REQUEST_ID\"}"
    ```
3.  **Monitor the Notification Queue** to receive the completion event.