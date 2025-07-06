# Testing Guidelines for Developers

This document provides comprehensive guidelines for implementing and maintaining unit tests in the Fiap Lumière Extractor Lambda project.

## Table of Contents
1. [Testing Philosophy](#testing-philosophy)
2. [Test Structure Guidelines](#test-structure-guidelines)
3. [Code Coverage Configuration](#code-coverage-configuration)
4. [Test Execution](#test-execution)
5. [Best Practices](#best-practices)
6. [Examples](#examples)

## Testing Philosophy

### 1. Test-Driven Development (TDD)
- Write tests before implementing functionality
- Red-Green-Refactor cycle: Write failing test → Make it pass → Refactor
- Tests serve as living documentation of expected behavior

### 2. ✅ Mock AWS Resources with moto
- Use `@mock_aws` decorator from moto library for AWS service simulation
- Create real S3 buckets and SQS queues in test setup for integration testing
- Avoid expensive AWS API calls during testing
- Ensure tests are isolated and repeatable

### 3. ✅ BDD (Behavior-Driven Development): Given-When-Then
- Structure test method names to follow the pattern:
  `test_given_[condition]_when_[action]_then_[expectation]`
- Organize test code with clear Given-When-Then comments
- Make test scenarios read like natural language specifications

### 4. ✅ AAA (Arrange-Act-Assert) Structure
- **Arrange**: Set up preconditions and inputs in the "Given" section
- **Act**: Call the method being tested in the "When" section  
- **Assert**: Verify expected behavior in the "Then" section

## Test Structure Guidelines

### File Organization
```
tests/
├── common/           # Tests for utility functions
├── infra/           # Tests for infrastructure components
├── service/         # Tests for business logic services
└── __init__.py      # Test package initialization
```

### Test Class Structure
```python
class TestVideoProcessingService:
    def setup_method(self):
        """Set up test fixtures before each test method"""
        # Initialize test data and mocks
        
    def test_given_valid_video_when_processing_then_completes_successfully(self):
        # Given: Setup test conditions
        # When: Execute the functionality
        # Then: Verify expected outcomes
```

### Test Method Naming Convention
- Use descriptive names that explain the test scenario
- Format: `test_given_[condition]_when_[action]_then_[expectation]`
- Examples:
  - `test_given_valid_s3_path_when_downloading_then_file_saved_locally`
  - `test_given_empty_video_when_extracting_frames_then_returns_zero_count`
  - `test_given_invalid_bucket_when_uploading_then_raises_client_error`

### Coverage Thresholds
- **Minimum coverage**: 80% for business logic (services)
- **Target coverage**: 90% for critical components

## Test Execution

### Running Tests Locally
```bash
# Run all tests with verbose output
python -m pytest tests/ -v

# Run tests with HTML coverage report
python -m pytest tests/ --cov=src --cov-report=html

# Run specific test file
python -m pytest tests/service/test_processing_service.py -v

# Run tests matching a pattern
python -m pytest tests/ -k "test_given_valid" -v
```

### CI/CD Integration
Tests are automatically executed in GitHub Actions:
- **On every push**: Full test suite with coverage
- **On pull requests**: Test suite with coverage reporting
- **Coverage threshold**: Must maintain minimum 80% coverage

## Best Practices

### 1. Test Independence
- Each test should be completely independent
- Use `setup_method()` and `teardown_method()` for test isolation
- Avoid shared state between tests

### 2. Mock External Dependencies
```python
@mock_aws
def test_given_s3_bucket_when_uploading_file_then_object_created(self):
    # Given: Mock S3 environment
    s3_client = boto3.client('s3', region_name='us-east-1')
    s3_client.create_bucket(Bucket='test-bucket')
    
    # When: Upload file
    # Then: Verify upload
```

### 3. Test Data Management
- Use fixtures for reusable test data
- Keep test data minimal and focused
- Use factories for complex object creation

### 4. Error Testing
- Test both happy path and error conditions
- Verify exception types and messages
- Test edge cases and boundary conditions

### 5. Performance Considerations
- Keep tests fast (< 1 second per test)
- Use appropriate mocking to avoid I/O operations
- Parallelize tests when possible

## Continuous Improvement

### Code Quality Gates
- All tests must pass before merging
- Coverage must not decrease
- No skipped tests without justification
- Performance regression detection

### Review Process
- Peer review of test cases
- Validate test scenarios cover requirements
- Ensure tests are maintainable and readable
- Verify proper use of mocks and fixtures
