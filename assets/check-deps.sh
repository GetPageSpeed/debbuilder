#!/usr/bin/env bash

# Script to check for missing build dependencies and suggest solutions
set -e

echo "Checking build dependencies..."

# Function to check if a package is available
check_package() {
    local package="$1"
    if apt-cache show "$package" >/dev/null 2>&1; then
        echo "✅ $package - available"
        return 0
    else
        echo "❌ $package - not available"
        return 1
    fi
}

# Function to suggest alternatives
suggest_alternatives() {
    local package="$1"
    case "$package" in
        python3-appdirs)
            echo "   💡 Alternative: python3-appdirs might be available as python3-appdirs2 or similar"
            echo "   💡 Or you can add it to debian/control as a conditional dependency"
            ;;
        python3-requests)
            echo "   💡 Alternative: python3-urllib3 or python3-httplib2"
            ;;
        *)
            echo "   💡 Check if this package has a different name in this distribution"
            ;;
    esac
}

# Read Build-Depends from debian/control
if [[ -f "debian/control" ]]; then
    echo "Reading Build-Depends from debian/control..."
    
    # Extract Build-Depends line and parse packages
    build_deps=$(grep "^Build-Depends:" debian/control | sed 's/Build-Depends://' | tr ',' '\n' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    
    missing_packages=()
    
    while IFS= read -r dep; do
        # Skip empty lines and version constraints for now
        if [[ -n "$dep" && ! "$dep" =~ ^[[:space:]]*$ ]]; then
            # Extract package name (remove version constraints)
            package=$(echo "$dep" | sed 's/[[:space:]]*([^)]*)[[:space:]]*$//')
            
            if ! check_package "$package"; then
                missing_packages+=("$package")
                suggest_alternatives "$package"
            fi
        fi
    done <<< "$build_deps"
    
    if [[ ${#missing_packages[@]} -eq 0 ]]; then
        echo "✅ All build dependencies are available!"
        exit 0
    else
        echo ""
        echo "❌ Missing packages: ${missing_packages[*]}"
        echo ""
        echo "💡 Suggestions:"
        echo "1. Check if packages have different names in this distribution"
        echo "2. Add missing packages to the distribution repositories"
        echo "3. Use conditional dependencies in debian/control"
        echo "4. Consider using alternative packages"
        echo ""
        echo "Example of conditional dependency in debian/control:"
        echo "Build-Depends: debhelper (>= 10),"
        echo "               dh-python,"
        echo "               python3-all,"
        echo "               python3-setuptools,"
        echo "               python3-appdirs | python3-appdirs2,"
        echo "               ..."
        exit 1
    fi
else
    echo "❌ debian/control not found"
    exit 1
fi 