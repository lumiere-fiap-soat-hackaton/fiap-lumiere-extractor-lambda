#!/bin/bash

# Local deployment script for FIAP Lumiere Media Processor Lambda
# This script helps with local testing and manual deployment

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
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
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

# Run tests
run_tests() {
    print_status "Running tests..."
    python -m pytest tests/ -v --cov=src/
    if [ $? -eq 0 ]; then
        print_status "All tests passed!"
    else
        print_error "Tests failed. Fix issues before deploying."
        exit 1
    fi
}

# Build Lambda layer
build_layer() {
    print_status "Building Lambda layer..."
    
    # Clean previous build
    rm -rf $DIST_DIR/layer $DIST_DIR/lambda-layer.zip
    
    # Create layer directory structure
    mkdir -p $DIST_DIR/layer/python/lib/python3.9/site-packages
    
    # Install layer dependencies
    pip install -r lambda-layer/requirements.txt -t $DIST_DIR/layer/python/lib/python3.9/site-packages/
    
    # Create layer zip
    cd $DIST_DIR/layer
    zip -r ../lambda-layer.zip .
    cd ../..
    
    print_status "Lambda layer built successfully."
}

# Build Lambda function
build_function() {
    print_status "Building Lambda function..."
    
    # Clean previous build
    rm -rf $DIST_DIR/function $DIST_DIR/lambda-function.zip
    
    # Create function directory
    mkdir -p $DIST_DIR/function
    
    # Copy source code
    cp -r src/* $DIST_DIR/function/
    
    # Install function dependencies (if any)
    if [ -f requirements.txt ]; then
        pip install -r requirements.txt -t $DIST_DIR/function/
    fi
    
    # Create function zip
    cd $DIST_DIR/function
    zip -r ../lambda-function.zip .
    cd ../..
    
    print_status "Lambda function built successfully."
}

# Upload artifacts to S3
upload_artifacts() {
    print_status "Uploading artifacts to S3..."
    
    # Create S3 keys with timestamp for versioning
    TIMESTAMP=$(date +%Y%m%d-%H%M%S)
    LAYER_S3_KEY="layers/lambda-layer-${TIMESTAMP}.zip"
    FUNCTION_S3_KEY="functions/lambda-function-${TIMESTAMP}.zip"
    
    # Upload layer zip to S3
    aws s3 cp $DIST_DIR/lambda-layer.zip s3://$S3_BUCKET/$LAYER_S3_KEY \
        --region $AWS_REGION
    
    # Upload function zip to S3
    aws s3 cp $DIST_DIR/lambda-function.zip s3://$S3_BUCKET/$FUNCTION_S3_KEY \
        --region $AWS_REGION
    
    # Store S3 keys for deployment
    echo $LAYER_S3_KEY > .layer_s3_key
    echo $FUNCTION_S3_KEY > .function_s3_key
    
    print_status "Artifacts uploaded successfully to S3."
}

# Deploy Lambda layer
deploy_layer() {
    print_status "Deploying Lambda layer..."
    
    # Get S3 key for layer
    if [ -f .layer_s3_key ]; then
        LAYER_S3_KEY=$(cat .layer_s3_key)
        print_status "Using layer from S3: s3://$S3_BUCKET/$LAYER_S3_KEY"
        
        LAYER_ARN=$(aws lambda publish-layer-version \
            --layer-name $LAYER_NAME \
            --description "Dependencies for FIAP Lumiere Media Processor Lambda - $(date)" \
            --content S3Bucket=$S3_BUCKET,S3Key=$LAYER_S3_KEY \
            --compatible-runtimes python3.9 \
            --region $AWS_REGION \
            --query 'LayerVersionArn' \
            --output text)
    else
        print_status "Using local layer zip file..."
        LAYER_ARN=$(aws lambda publish-layer-version \
            --layer-name $LAYER_NAME \
            --description "Dependencies for FIAP Lumiere Media Processor Lambda - $(date)" \
            --zip-file fileb://$DIST_DIR/lambda-layer.zip \
            --compatible-runtimes python3.9 \
            --region $AWS_REGION \
            --query 'LayerVersionArn' \
            --output text)
    fi
    
    print_status "Layer deployed successfully: $LAYER_ARN"
    echo $LAYER_ARN > .layer_arn
}

# Deploy Lambda function
deploy_function() {
    print_status "Deploying Lambda function..."
    
    # Get S3 key for function
    if [ -f .function_s3_key ]; then
        FUNCTION_S3_KEY=$(cat .function_s3_key)
        print_status "Using function from S3: s3://$S3_BUCKET/$FUNCTION_S3_KEY"
        
        # Update function code from S3
        aws lambda update-function-code \
            --function-name $LAMBDA_FUNCTION_NAME \
            --s3-bucket $S3_BUCKET \
            --s3-key $FUNCTION_S3_KEY \
            --region $AWS_REGION
    else
        print_status "Using local function zip file..."
        # Update function code from local file
        aws lambda update-function-code \
            --function-name $LAMBDA_FUNCTION_NAME \
            --zip-file fileb://$DIST_DIR/lambda-function.zip \
            --region $AWS_REGION
    fi
    
    # Wait for the update to complete
    print_status "Waiting for function update to complete..."
    aws lambda wait function-updated \
        --function-name $LAMBDA_FUNCTION_NAME \
        --region $AWS_REGION
    
    # Update function configuration to use the new layer version
    if [ -f .layer_arn ]; then
        LAYER_ARN=$(cat .layer_arn)
        print_status "Updating function configuration with new layer..."
        aws lambda update-function-configuration \
            --function-name $LAMBDA_FUNCTION_NAME \
            --layers $LAYER_ARN \
            --region $AWS_REGION
        
        # Wait for the configuration update to complete
        aws lambda wait function-updated \
            --function-name $LAMBDA_FUNCTION_NAME \
            --region $AWS_REGION
    fi
    
    print_status "Lambda function deployed successfully."
}

# Verify deployment
verify_deployment() {
    print_status "Verifying deployment..."
    
    FUNCTION_INFO=$(aws lambda get-function \
        --function-name $LAMBDA_FUNCTION_NAME \
        --region $AWS_REGION \
        --query 'Configuration.[FunctionName,Runtime,Handler,LastModified]' \
        --output table)
    
    print_status "Function deployment verified:"
    echo "$FUNCTION_INFO"
}

# Clean up build artifacts
cleanup() {
    print_status "Cleaning up build artifacts..."
    rm -rf $DIST_DIR
    rm -f .layer_arn
    rm -f .layer_s3_key
    rm -f .function_s3_key
    print_status "Cleanup complete."
}

# Show help
show_help() {
    echo "Usage: $0 [OPTION]"
    echo ""
    echo "Options:"
    echo "  test          Run tests only"
    echo "  build         Build Lambda function and layer"
    echo "  deploy        Deploy Lambda function and layer to AWS"
    echo "  full          Run tests, build, and deploy (default)"
    echo "  clean         Clean build artifacts"
    echo "  help          Show this help message"
    echo ""
    echo "Environment Configuration:"
    echo "  S3_BUCKET: $S3_BUCKET"
    echo "  AWS_REGION: $AWS_REGION"
    echo "  LAMBDA_FUNCTION_NAME: $LAMBDA_FUNCTION_NAME"
    echo "  DEPENDENCY_LAYER_NAME: $LAYER_NAME"
    echo "  DIST_DIR: $DIST_DIR"
    echo ""
    echo "Examples:"
    echo "  $0            # Run full pipeline"
    echo "  $0 test       # Run tests only"
    echo "  $0 build      # Build only"
    echo "  $0 deploy     # Deploy only (requires existing build)"
    echo "  $0 clean      # Clean build artifacts"
    echo ""
    echo "Note: The deploy command uploads artifacts to S3 bucket: $S3_BUCKET"
    echo "      and deploys Lambda function and layer from S3."
}

# Main function
main() {
    case "${1:-full}" in
        test)
            check_aws_config
            run_tests
            ;;
        build)
            build_layer
            build_function
            ;;
        deploy)
            check_aws_config
            upload_artifacts
            deploy_layer
            deploy_function
            verify_deployment
            ;;
        full)
            check_aws_config
            run_tests
            build_layer
            build_function
            upload_artifacts
            deploy_layer
            deploy_function
            verify_deployment
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
