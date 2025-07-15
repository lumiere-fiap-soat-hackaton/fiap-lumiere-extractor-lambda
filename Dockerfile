FROM public.ecr.aws/lambda/python:3.9 AS build

# Install zip utility and other necessary tools
RUN yum update -y && yum install -y zip

# Set working directory
WORKDIR /app

# Create dist directory
RUN mkdir -p /app/dist

# Build Lambda Layer
RUN mkdir -p /app/layer/python
COPY lambda-layer/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt -t /app/layer/python/

# Create layer zip
WORKDIR /app/layer
RUN zip -r /app/dist/lambda-layer.zip .

# Build Lambda Function
WORKDIR /app
COPY src/ /app/function/src
WORKDIR /app/function
RUN zip -r /app/dist/lambda-function.zip .

# Final stage to copy artifacts
FROM scratch AS export
COPY --from=build /app/dist/ /