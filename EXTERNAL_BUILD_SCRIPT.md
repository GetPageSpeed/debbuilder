# External Build Script Feature

## Overview

The debbuilder now supports fetching build scripts from external sources, allowing you to update build logic without rebuilding Docker images. This addresses the maintenance burden of constantly rebuilding images when the build script changes.

**NEW**: The build script now automatically fetches the latest version from the [GetPageSpeed/debbuilder repository](https://raw.githubusercontent.com/GetPageSpeed/debbuilder/refs/heads/main/assets/build) before executing, ensuring you always get the latest build logic without waiting for Docker image rebuilds.

## Usage

### Automatic Latest Version (Default Behavior)

By default, the build script automatically fetches and executes the latest version from GitHub:

```bash
# Automatically gets latest build logic
docker run -v /path/to/source:/sources -v /path/to/output:/output \
    getpagespeed/debbuilder:ubuntu-noble \
    build
```

### Skip Latest Version Fetch

If you want to use the local version (for testing or offline builds):

```bash
# Use local version only
docker run -v /path/to/source:/sources -v /path/to/output:/output \
    getpagespeed/debbuilder:ubuntu-noble \
    build --no-fetch
```

### Custom External Build Script

```bash
# Use custom external build script
docker run -v /path/to/source:/sources -v /path/to/output:/output \
    getpagespeed/debbuilder:ubuntu-noble \
    build --external-build-script https://raw.githubusercontent.com/your-repo/build-script/main/build.sh
```

### With Additional Options

```bash
docker run -v /path/to/source:/sources -v /path/to/output:/output \
    getpagespeed/debbuilder:ubuntu-noble \
    build --external-build-script https://raw.githubusercontent.com/your-repo/build-script/main/build.sh \
    --force --enable-repos "ppa:some-ppa/ppa"
```

## Benefits

1. **Always Latest Logic**: Automatically gets the latest build logic without Docker rebuilds
2. **No Docker Image Rebuilds**: Update build logic by simply updating the external script
3. **Version Control**: Keep build scripts in version control alongside your project
4. **Flexibility**: Different projects can use different build scripts
5. **Rapid Iteration**: Test build script changes without rebuilding images
6. **Distribution-Specific Logic**: Use different scripts for different distributions
7. **Offline Fallback**: Falls back to local version if network is unavailable

## Implementation

### Automatic Latest Version Fetching

The build script now automatically:

1. **Fetches the latest version** from [GetPageSpeed/debbuilder](https://raw.githubusercontent.com/GetPageSpeed/debbuilder/refs/heads/main/assets/build)
2. **Executes the latest version** if fetch succeeds (with `--no-fetch` to prevent recursion)
3. **Falls back to local version** if fetch fails (network issues, etc.)
4. **Preserves all arguments** passed to the original command

This ensures you always get the latest build logic without waiting for Docker image rebuilds.

**Important**: The fetched script is executed with `--no-fetch` to prevent infinite recursion. This means the fetched script will run once and not try to fetch again.

### Recursion Prevention

To prevent infinite recursion, the system works as follows:

1. **Local script** checks if `--no-fetch` is present
2. **If not present**: Fetches latest version and executes it with `--no-fetch`
3. **Fetched script**: Sees `--no-fetch` and skips fetching, runs normally
4. **Result**: Only one fetch per execution, no infinite loops

```
Execution Flow:
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   User runs     │───▶│  Local script   │───▶│  Fetched script │
│   build         │    │  (no --no-fetch)│    │  (with --no-fetch)│
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │                        │
                              ▼                        ▼
                       Fetches latest           Runs normally
                       Adds --no-fetch          (no more fetching)
```

This ensures that:
- ✅ You always get the latest logic
- ✅ No infinite recursion occurs
- ✅ Network failures are handled gracefully
- ✅ Offline builds still work

### External Script Requirements

Your external build script should:

1. **Accept the same arguments** as the built-in script
2. **Use the same environment variables** (`SOURCES`, `OUTPUT`, `DISTRO`, etc.)
3. **Follow the same conventions** for package discovery and building
4. **Handle errors gracefully** and provide meaningful output

### Example External Script

```bash
#!/usr/bin/env bash
set -exo pipefail

export DEBIAN_FRONTEND=noninteractive

SOURCES=${SOURCES-/sources}
OUTPUT=${OUTPUT-${SOURCES}}

# Parse arguments (same as built-in script)
FORCE=false
ENABLE_REPOS=""

while [[ "$1" != "" ]]; do
    case $1 in
        --force )
            FORCE=true
            ;;
        --enable-repos )
            shift
            if [[ -n $1 ]]; then
                ENABLE_REPOS=$1
            else
                echo "Error: --enable-repos requires a value."
                exit 1
            fi
            ;;
        * )
            echo "Invalid option: $1"
            exit 1
            ;;
    esac
    shift
done

# Your custom build logic here
echo "Using external build script..."

# Find packages
find_packages() {
    find "${SOURCES}" -mindepth 1 -type d -name debian -exec dirname {} \;
}

# Build packages
package_dirs=$(find_packages)
for package_dir in $package_dirs; do
    echo "Building package in $package_dir..."
    cd "$package_dir"
    
    # Your custom build steps
    # ...
    
    # Move output
    mkdir -p "${OUTPUT}"
    mv ../*.deb "${OUTPUT}/"
done
```

## Hosting Options

### GitHub Raw URLs

```bash
--external-build-script https://raw.githubusercontent.com/your-org/your-repo/main/scripts/build.sh
```

### GitLab Raw URLs

```bash
--external-build-script https://gitlab.com/your-org/your-repo/-/raw/main/scripts/build.sh
```

### Self-Hosted

```bash
--external-build-script https://your-domain.com/build-scripts/latest.sh
```

### Version-Specific Scripts

```bash
--external-build-script https://raw.githubusercontent.com/your-org/your-repo/v1.2.3/scripts/build.sh
```

## Security Considerations

1. **HTTPS Only**: Always use HTTPS URLs for external scripts
2. **Verification**: Consider adding checksums for script verification
3. **Access Control**: Ensure your script hosting has appropriate access controls
4. **Audit Trail**: Keep logs of which external scripts are being used

## Fallback Behavior

If the external script fails to download or execute, the debbuilder will:

1. Log the failure
2. Fall back to the built-in script
3. Continue with the build process

## Integration with CI/CD

### CircleCI Example

```yaml
- run:
    name: Build with external script
    command: |
      build --external-build-script \
        https://raw.githubusercontent.com/${CIRCLE_PROJECT_USERNAME}/${CIRCLE_PROJECT_REPONAME}/${CIRCLE_BRANCH}/scripts/build.sh
```

### GitHub Actions Example

```yaml
- name: Build with external script
  run: |
    docker run -v ${{ github.workspace }}:/sources -v /tmp/output:/output \
      getpagespeed/debbuilder:ubuntu-noble \
      build --external-build-script \
        https://raw.githubusercontent.com/${{ github.repository }}/${{ github.ref_name }}/scripts/build.sh
```

## Best Practices

1. **Keep Scripts Simple**: External scripts should focus on build logic, not complex setup
2. **Version Your Scripts**: Use versioned URLs for stability
3. **Test Locally**: Always test external scripts before deploying
4. **Document Dependencies**: Clearly document what your external script requires
5. **Handle Errors**: Provide clear error messages and fallback options

## Migration Strategy

1. **Start with Built-in**: Use the built-in script for initial development
2. **Extract Logic**: Move custom logic to external scripts gradually
3. **Test Thoroughly**: Ensure external scripts work across all target distributions
4. **Monitor Usage**: Track which scripts are being used and their success rates

## Troubleshooting

### Common Issues

1. **Script Not Found**: Check the URL and ensure the script is publicly accessible
2. **Permission Denied**: Ensure the script is executable and has proper permissions
3. **Network Issues**: Verify network connectivity and DNS resolution
4. **Script Errors**: Check the script syntax and logic
5. **Latest Version Fetch Fails**: The script will automatically fall back to local version
6. **GitHub Rate Limiting**: If you hit GitHub API limits, use `--no-fetch` to skip fetching

### Debug Commands

```bash
# Test script download
curl -fsSL https://your-script-url.sh

# Test script execution
curl -fsSL https://your-script-url.sh | bash -x

# Check script in container
docker run --rm getpagespeed/debbuilder:ubuntu-noble \
  bash -c "curl -fsSL https://your-script-url.sh > /tmp/test.sh && chmod +x /tmp/test.sh && /tmp/test.sh --help"
``` 