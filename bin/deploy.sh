#!/bin/bash

# Simplified deployment script for FIAP Lumiere Media Processor Lambda
# Builds using Docker and deploys via S3

set -e

# Configuration
AWS_REGION="${AWS_REGION:-us-east-1}"
LAMBDA_FUNCTION_NAME="${LAMBDA_FUNCTION_NAME:-FiapLumiereMediaProcessorLambda}"
LAYER_NAME="${DEPENDENCY_LAYER_NAME:-VideoExtractorDependencies}"
DIST_DIR="${DIST_DIR:-dist}"
S3_BUCKET="${S3_BUCKET:-fiap-lumiere-lambda-code-bucket}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Build Lambda layer and function using Docker
build() {
    print_status "Building Lambda layer and function using Docker..."
    
    # Check if Docker is available
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed or not available in PATH."
        exit 1
    fi
    
    # Check if Docker daemon is running
    if ! docker info &> /dev/null; then
        print_error "Docker daemon is not running. Please start Docker daemon and try again."
        exit 1
    fi
    
    # Clean previous build
    rm -rf $DIST_DIR
    mkdir -p $DIST_DIR
    
    # Build and extract artifacts using Docker
    docker build --target export --output $DIST_DIR .
    
    print_status "Build completed successfully."
    
    # Show file sizes
    if [ -f "$DIST_DIR/lambda-layer.zip" ]; then
        LAYER_SIZE=$(du -h $DIST_DIR/lambda-layer.zip | cut -f1)
        print_status "Lambda layer built (Size: $LAYER_SIZE)."
    fi
    
    if [ -f "$DIST_DIR/lambda-function.zip" ]; then
        FUNCTION_SIZE=$(du -h $DIST_DIR/lambda-function.zip | cut -f1)
        print_status "Lambda function built (Size: $FUNCTION_SIZE)."
    fi
}

# Check if AWS CLI is configured
check_aws_config() {
    print_status "Checking AWS configuration..."
    if ! aws sts get-caller-identity &> /dev/null; then
        print_error "AWS CLI not configured. Please run 'aws configure' first."
        exit 1
    fi
    print_status "AWS CLI is configured."
}

# Upload artifacts to S3 and deploy
deploy() {
    print_status "Uploading artifacts to S3..."
    
    # Create S3 keys with timestamp
    TIMESTAMP=$(date +%Y%m%d-%H%M%S)
    LAYER_S3_KEY="layers/lambda-layer-${TIMESTAMP}.zip"
    FUNCTION_S3_KEY="functions/lambda-function-${TIMESTAMP}.zip"
    
    # Upload to S3
    aws s3 cp $DIST_DIR/lambda-layer.zip s3://$S3_BUCKET/$LAYER_S3_KEY --region $AWS_REGION
    aws s3 cp $DIST_DIR/lambda-function.zip s3://$S3_BUCKET/$FUNCTION_S3_KEY --region $AWS_REGION
    
    print_status "Deploying Lambda layer..."
    LAYER_ARN=$(aws lambda publish-layer-version \
        --layer-name $LAYER_NAME \
        --description "Dependencies for FIAP Lumiere - $(date)" \
        --content S3Bucket=$S3_BUCKET,S3Key=$LAYER_S3_KEY \
        --compatible-runtimes python3.9 \
        --region $AWS_REGION \
        --query 'LayerVersionArn' \
        --output text)
    
    print_status "Deploying Lambda function..."
    aws lambda update-function-code \
        --function-name $LAMBDA_FUNCTION_NAME \
        --s3-bucket $S3_BUCKET \
        --s3-key $FUNCTION_S3_KEY \
        --region $AWS_REGION
    
    # Wait for update and configure layer
    aws lambda wait function-updated --function-name $LAMBDA_FUNCTION_NAME --region $AWS_REGION
    
    aws lambda update-function-configuration \
        --function-name $LAMBDA_FUNCTION_NAME \
        --layers $LAYER_ARN \
        --handler src/lambda_function.lambda_handler \
        --runtime python3.9 \
        --region $AWS_REGION
    
    print_status "Deployment completed successfully!"
    print_status "Layer ARN: $LAYER_ARN"
}

# Clean up build artifacts
cleanup() {
    print_status "Cleaning up build artifacts..."
    rm -rf $DIST_DIR
    print_status "Cleanup complete."
}

# Show help
show_help() {
    echo "Usage: $0 [OPTION]"
    echo ""
    echo "Options:"
    echo "  build     Build Lambda function and layer using Docker"
    echo "  deploy    Deploy Lambda function and layer to AWS via S3"
    echo "  full      Build and deploy (default)"
    echo "  clean     Clean build artifacts"
    echo "  help      Show this help message"
    echo ""
    echo "Environment Variables:"
    echo "  S3_BUCKET: $S3_BUCKET"
    echo "  AWS_REGION: $AWS_REGION"
    echo "  LAMBDA_FUNCTION_NAME: $LAMBDA_FUNCTION_NAME"
    echo "  DEPENDENCY_LAYER_NAME: $LAYER_NAME"
    echo ""
    echo "Examples:"
    echo "  $0        # Build and deploy"
    echo "  $0 build  # Build only"
    echo "  $0 deploy # Deploy only (requires existing build)"
    echo "  $0 clean  # Clean build artifacts"
}

# Main function
main() {
    case "${1:-full}" in
        build)
            build
            ;;
        deploy)
            check_aws_config
            deploy
            ;;
        full)
            check_aws_config
            build
            deploy
            ;;
        clean)
            cleanup
            ;;
        help)
            show_help
            ;;
        *)
            print_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
