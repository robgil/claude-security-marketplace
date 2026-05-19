# Security Recommendation Tests

## Test 1: Non-root User Recommendation
**Input**: Dockerfile with USER root
**Expected Output**: 
- Warning about running as root user
- Recommendation to create dedicated non-root user
- Example of proper user creation: USER appuser:appuser

## Test 2: Multi-stage Build Recommendation
**Input**: Dockerfile without multi-stage build
**Expected Output**:
- Suggestion to implement multi-stage build
- Explanation of build vs runtime dependencies
- Benefits of separating build and runtime stages

## Test 3: Chainguard Image Recommendation
**Input**: Dockerfile with standard base image
**Expected Output**:
- Recommendation to use Chainguard base images
- Explanation of enhanced security benefits
- Link to Chainguard documentation

## Test 4: Network Access Restriction
**Input**: Dockerfile with curl/wget commands
**Expected Output**:
- Alert about network access
- Recommendation to restrict network access
- Explanation of safe approaches to network operations

## Test 5: Privileged Mode
**Input**: Dockerfile with privileged mode references
**Expected Output**:
- Warning about privileged mode usage
- Recommendation for safer alternatives
- Explanation of security risks

## Test 6: Shell Script Usage
**Input**: Dockerfile with shell script execution
**Expected Output**:
- Detection of shell script usage
- Recommendation for alternative approaches
- Best practices for script execution in containers

## Test 7: Single Process Container
**Input**: Dockerfile that might run multiple processes
**Expected Output**:
- Verification of single process container
- Recommendation for proper process management
- Solutions for multi-process scenarios