#!/bin/bash

# Test script for debbuilder
# This script demonstrates how to use the debbuilder Docker image

set -e

echo "=== DEB Builder Test Script ==="

# Configuration
IMAGE_NAME="debbuilder:ubuntu-noble"
SOURCE_DIR="$(pwd)/tests"
OUTPUT_DIR="$(pwd)/output"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if source directory exists
if [ ! -d "$SOURCE_DIR" ]; then
    print_error "Source directory $SOURCE_DIR does not exist."
    exit 1
fi

# Check if debian directory exists in source
if [ ! -d "$SOURCE_DIR/hello/debian" ]; then
    print_error "No debian directory found in $SOURCE_DIR/hello"
    exit 1
fi

# Check if original tarball exists
if [ ! -f "$SOURCE_DIR/hello_1.0.orig.tar.gz" ]; then
    print_warning "Original tarball $SOURCE_DIR/hello_1.0.orig.tar.gz not found"
else
    print_status "Found original tarball: $SOURCE_DIR/hello_1.0.orig.tar.gz"
fi

print_status "Building Docker image..."
if ! docker build --tag "$IMAGE_NAME" ubuntu/noble; then
    print_error "Failed to build Docker image"
    exit 1
fi

print_status "Creating output directory..."
mkdir -p "$OUTPUT_DIR"

print_status "Building package..."
print_status "Source: $SOURCE_DIR"
print_status "Output: $OUTPUT_DIR"

if docker run --rm \
    -v "$SOURCE_DIR:/sources" \
    -v "$OUTPUT_DIR:/output" \
    "$IMAGE_NAME"; then
    
    print_status "Build completed successfully!"
    
    # List output files
    if [ -d "$OUTPUT_DIR" ] && [ "$(ls -A "$OUTPUT_DIR")" ]; then
        print_status "Generated files:"
        ls -la "$OUTPUT_DIR"
    else
        print_warning "No output files found"
    fi
else
    print_error "Build failed"
    exit 1
fi

print_status "Test completed!" 