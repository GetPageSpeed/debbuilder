#!/bin/bash

# Example workflow for debbuilder
# This script demonstrates the complete process from generating Dockerfiles to building packages

set -e

echo "=== DEB Builder Example Workflow ==="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker and try again."
    exit 1
fi

print_step "Step 1: Generate Dockerfiles for all supported versions"
print_status "Running: ./crypt-keeper.sh generate all"
./crypt-keeper.sh generate all

print_step "Step 2: Build Docker images for all versions"
print_status "Building Ubuntu Noble..."
docker build --tag debbuilder:ubuntu-noble ubuntu/noble

print_status "Building Ubuntu Jammy..."
docker build --tag debbuilder:ubuntu-jammy ubuntu/jammy

print_status "Building Ubuntu Focal..."
docker build --tag debbuilder:ubuntu-focal ubuntu/focal

print_status "Building Debian Bookworm..."
docker build --tag debbuilder:debian-bookworm debian/bookworm

print_step "Step 3: Test package building with different versions"
OUTPUT_DIR="$(pwd)/output"

# Test with Ubuntu Noble
print_status "Testing Ubuntu Noble..."
rm -rf "$OUTPUT_DIR" && mkdir -p "$OUTPUT_DIR"
if docker run --rm -v "$(pwd)/tests:/sources" -v "$OUTPUT_DIR:/output" debbuilder:ubuntu-noble; then
    print_status "✅ Ubuntu Noble build successful"
    ls -la "$OUTPUT_DIR"
else
    print_error "❌ Ubuntu Noble build failed"
fi

# Test with Ubuntu Jammy
print_status "Testing Ubuntu Jammy..."
rm -rf "$OUTPUT_DIR" && mkdir -p "$OUTPUT_DIR"
if docker run --rm -v "$(pwd)/tests:/sources" -v "$OUTPUT_DIR:/output" debbuilder:ubuntu-jammy; then
    print_status "✅ Ubuntu Jammy build successful"
    ls -la "$OUTPUT_DIR"
else
    print_error "❌ Ubuntu Jammy build failed"
fi

# Test with Debian Bookworm
print_status "Testing Debian Bookworm..."
rm -rf "$OUTPUT_DIR" && mkdir -p "$OUTPUT_DIR"
if docker run --rm -v "$(pwd)/tests:/sources" -v "$OUTPUT_DIR:/output" debbuilder:debian-bookworm; then
    print_status "✅ Debian Bookworm build successful"
    ls -la "$OUTPUT_DIR"
else
    print_error "❌ Debian Bookworm build failed"
fi

print_step "Step 4: Demonstrate adding a new version"
print_status "Adding Ubuntu Kinetic (22.10) to defaults..."
echo "ubuntu kinetic" >> defaults

print_status "Generating Dockerfile for Ubuntu Kinetic..."
./crypt-keeper.sh generate ubuntu kinetic

print_status "Building Ubuntu Kinetic image..."
docker build --tag debbuilder:ubuntu-kinetic ubuntu/kinetic

print_status "Testing Ubuntu Kinetic..."
rm -rf "$OUTPUT_DIR" && mkdir -p "$OUTPUT_DIR"
if docker run --rm -v "$(pwd)/tests:/sources" -v "$OUTPUT_DIR:/output" debbuilder:ubuntu-kinetic; then
    print_status "✅ Ubuntu Kinetic build successful"
    ls -la "$OUTPUT_DIR"
else
    print_error "❌ Ubuntu Kinetic build failed"
fi

print_step "Step 5: Show available images"
print_status "Available debbuilder images:"
docker images | grep debbuilder

print_status "Example workflow completed successfully!"
print_status "You can now use any of these images to build your packages:"
echo "  - debbuilder:ubuntu-noble"
echo "  - debbuilder:ubuntu-jammy" 
echo "  - debbuilder:ubuntu-focal"
echo "  - debbuilder:debian-bookworm"
echo "  - debbuilder:ubuntu-kinetic" 