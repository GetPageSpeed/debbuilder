#!/bin/bash
set -exo pipefail

# Test script to simulate GitHub Actions workflow locally
# This helps verify the workflow before pushing to GitHub

echo "🧪 Testing GitHub Actions workflow simulation..."

# Test 1: Matrix configuration
echo "📋 Testing matrix configuration..."
MATRIX=$(jq -c . < ./distro_versions.json)
echo "Matrix: $MATRIX"

# Test 2: Generate Dockerfiles for all versions
echo "🔨 Generating Dockerfiles for all versions..."
./crypt-keeper.sh generate all

# Test 3: Test multi-architecture build command (without actual build)
echo "🐳 Testing multi-architecture build command..."
# Use the actual matrix from distro_versions.json
jq -r '.include[] | "\(.os) \(.version)"' ./distro_versions.json | while read -r os version; do
    echo "Testing $os-$version..."
    MAIN_TAG=$(./crypt-keeper.sh docker-image-name "$os" "$version")
    DIST_TAG=$(./crypt-keeper.sh docker-image-dist-tag "$os" "$version")
    ALT_TAG=$(./crypt-keeper.sh docker-image-alt-name "$os" "$version")
    
    echo "  Main tag: $MAIN_TAG"
    echo "  Dist tag: $DIST_TAG"
    echo "  Alt tag: $ALT_TAG"
    
    # Check if Dockerfile exists
    if [ -f "$os/$version/Dockerfile" ]; then
        echo "  ✅ Dockerfile exists"
    else
        echo "  ❌ Dockerfile missing"
        exit 1
    fi
done

# Test 4: Test local build (optional - requires Docker)
if [ "${1:-}" = "--build" ]; then
    echo "🔨 Testing local build for ubuntu-noble..."
    docker build --tag debbuilder:ubuntu-noble ubuntu/noble
    echo "✅ Local build successful"
fi

echo "🎉 All tests passed! GitHub Actions workflow is ready."
echo ""
echo "📝 Next steps:"
echo "1. Commit and push to GitHub"
echo "2. Set up DOCKER_USER and DOCKER_PASS secrets in repository settings"
echo "3. GitHub Actions will automatically build multi-architecture images" 