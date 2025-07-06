#!/bin/bash

# Local deployment script for FIAP Lumiere Media Processor Lambda
# This script helps with local testing and manual deployment

set -e

# Configuration
AWS_REGION="us-east-1"
LAMBDA_FUNCTION_NAME="FiapLumiereMediaProcessorLambda"
LAYER_NAME="VideoExtractorDependencies"

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
    rm -rf lambda-layer-build lambda-layer.zip
    
    # Create layer directory structure
    mkdir -p lambda-layer-build/python/lib/python3.9/site-packages
    
    # Install layer dependencies
    pip install -r lambda-layer/requirements.txt -t lambda-layer-build/python/lib/python3.9/site-packages/
    
    # Create layer zip
    cd lambda-layer-build
    zip -r ../lambda-layer.zip .
    cd ..
    
    print_status "Lambda layer built successfully."
}

# Build Lambda function
build_function() {
    print_status "Building Lambda function..."
    
    # Clean previous build
    rm -rf lambda-function-build lambda-function.zip
    
    # Create function directory
    mkdir -p lambda-function-build
    
    # Copy source code
    cp -r src/* lambda-function-build/
    
    # Install function dependencies (if any)
    if [ -f requirements.txt ]; then
        pip install -r requirements.txt -t lambda-function-build/
    fi
    
    # Create function zip
    cd lambda-function-build
    zip -r ../lambda-function.zip .
    cd ..
    
    print_status "Lambda function built successfully."
}

# Deploy Lambda layer
deploy_layer() {
    print_status "Deploying Lambda layer..."
    
    LAYER_ARN=$(aws lambda publish-layer-version \
        --layer-name $LAYER_NAME \
        --description "Dependencies for FIAP Lumiere Media Processor Lambda - $(date)" \
        --zip-file fileb://lambda-layer.zip \
        --compatible-runtimes python3.9 \
        --region $AWS_REGION \
        --query 'LayerVersionArn' \
        --output text)
    
    print_status "Layer deployed successfully: $LAYER_ARN"
    echo $LAYER_ARN > .layer_arn
}

# Deploy Lambda function
deploy_function() {
    print_status "Deploying Lambda function..."
    
    # Update function code
    aws lambda update-function-code \
        --function-name $LAMBDA_FUNCTION_NAME \
        --zip-file fileb://lambda-function.zip \
        --region $AWS_REGION
    
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
    rm -rf lambda-layer-build lambda-function-build
    rm -f lambda-layer.zip lambda-function.zip .layer_arn
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
    echo "Examples:"
    echo "  $0            # Run full pipeline"
    echo "  $0 test       # Run tests only"
    echo "  $0 build      # Build only"
    echo "  $0 deploy     # Deploy only (requires existing build)"
    echo "  $0 clean      # Clean build artifacts"
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
            deploy_layer
            deploy_function
            verify_deployment
            ;;
        full)
            check_aws_config
            run_tests
            build_layer
            build_function
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
