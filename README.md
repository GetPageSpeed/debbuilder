https://chatgpt.com/c/66eeef52-90fc-8011-8554-a025ed2c2438

# DEB builder Docker images

This project provides Docker images for building Debian packages (.deb files) across different Ubuntu distributions. It's designed to be simple to use - just mount a directory containing a `debian` folder and get built .deb files as output.

## Features

- **Fast builds**: Optimized for quick package building with proper dependency handling
- **Multiple Ubuntu versions**: Support for different Ubuntu releases (Focal, Noble, etc.)
- **Simple usage**: Just mount your source directory and get .deb files as output
- **Robust error handling**: Retry logic for network operations and better error reporting

## Available versions

Currently supported Ubuntu versions:
- `ubuntu/focal` - Ubuntu 20.04 LTS
- `ubuntu/noble` - Ubuntu 24.04 LTS

## Quick Start

### 1. Build the Docker image

For Ubuntu Noble (24.04):
```bash
docker build --tag debbuilder:ubuntu-noble ubuntu/noble
```

### 2. Build a package

Mount a directory containing your package source and get .deb files as output:

```bash
# Set up directories
SOURCE_DIR=$(pwd)/your-package-source
OUTPUT_DIR=$(pwd)/output

# Create output directory
mkdir -p ${OUTPUT_DIR}

# Build the package
docker run -v ${SOURCE_DIR}:/sources -v ${OUTPUT_DIR}:/output debbuilder:ubuntu-noble
```

The built .deb files will be available in `OUTPUT_DIR`.

**Note**: The source directory should contain both your package directory (with the `debian` folder) and any original tarballs (`.orig.tar.gz` files) in the same directory structure.

### 3. Example with test package

```bash
# Build the test hello package
mkdir -p output
docker run -v $(pwd)/tests:/sources -v $(pwd)/output:/output debbuilder:ubuntu-noble
```

## Usage Options

### Force rebuild
To force rebuild even if the package already exists in the repository:
```bash
docker run -v ${SOURCE_DIR}:/sources -v ${OUTPUT_DIR}:/output debbuilder:ubuntu-noble --force
```

### Enable additional repositories
To enable additional APT repositories before building:
```bash
docker run -v ${SOURCE_DIR}:/sources -v ${OUTPUT_DIR}:/output debbuilder:ubuntu-noble --enable-repos "ppa:some-ppa/ppa"
```

## Debugging

For interactive debugging, you can run the container with a bash shell:

```bash
docker run --rm -it --entrypoint bash \
    -v ${SOURCE_DIR}:/sources \
    -v ${OUTPUT_DIR}:/output \
    debbuilder:ubuntu-noble
```

From within the container, you can run `build` to build packages or debug issues.

## Volumes

The following volumes can be mounted from the host:

| Volume | Description |
|:-------|:------------|
| `/sources` | Source directory containing the `debian` folder |
| `/output` | Output directory where built .deb files are placed |

## Package Structure

Your source directory should contain:
```
your-source-directory/
├── your-package/
│   ├── debian/
│   │   ├── control
│   │   ├── changelog
│   │   ├── rules
│   │   └── ...
│   └── src/
├── your-package_1.0.orig.tar.gz  # Original source tarball
└── ...
```

The build script will automatically find packages by looking for directories containing a `debian` folder.

## Troubleshooting

### Build takes too long
- The first build may take longer due to package installation
- Subsequent builds should be faster as dependencies are cached
- Check your internet connection as the build process downloads packages

### Missing dependencies
- The build script automatically installs build dependencies using `mk-build-deps`
- If you encounter dependency issues, check that your `debian/control` file has correct `Build-Depends` entries

### Permission issues
- The container runs as root, so output files will be owned by root
- Use the `OUTPUT_UID` environment variable to change ownership if needed

## GitHub Actions CI/CD

The project includes GitHub Actions workflows for automated multi-architecture Docker image building and testing.

### Workflow Features

- **Multi-architecture builds**: Automatically builds for both `linux/amd64` and `linux/arm64`
- **Matrix builds**: Builds all supported Ubuntu and Debian versions in parallel
- **Retry logic**: Robust retry mechanism for network-related build failures
- **Automated testing**: Tests both architectures after successful builds
- **Scheduled builds**: Runs every 6 hours to ensure images stay up-to-date

### Configuration Files

- **`.github/workflows/dockerbuild.yml`**: Main CI workflow
- **`distro_versions.json`**: Matrix configuration for supported distributions
- **`matrix.json`**: Detailed configuration for distributions and collections

### Required Secrets

Set these secrets in your GitHub repository settings:

- `DOCKER_USER`: Docker Hub username
- `DOCKER_PASS`: Docker Hub password/token

### Matrix Configuration

The `distro_versions.json` file defines which distributions to build:

```json
{
    "include": [
        {
            "os": "ubuntu",
            "version": "focal"
        },
        {
            "os": "ubuntu", 
            "version": "jammy"
        },
        {
            "os": "ubuntu",
            "version": "noble"
        },
        {
            "os": "debian",
            "version": "bookworm"
        },
        {
            "os": "debian",
            "version": "trixie"
        }
    ]
}
```

### Adding New Versions

1. **Add to `distro_versions.json`**:
   ```json
   {
       "os": "ubuntu",
       "version": "kinetic"
   }
   ```

2. **Add to `defaults`**:
   ```bash
   echo "ubuntu kinetic" >> defaults
   ```

3. **Generate and test locally**:
   ```bash
   ./crypt-keeper.sh generate ubuntu kinetic
   docker build --tag debbuilder:ubuntu-kinetic ubuntu/kinetic
   ```

4. **Commit and push**: The GitHub Actions will automatically build the new version.

## Development

### Adding new Ubuntu/Debian versions

1. **Add the new version to `defaults`**:
   ```bash
   echo "ubuntu kinetic" >> defaults  # For Ubuntu 22.10
   echo "debian sid" >> defaults      # For Debian unstable
   ```

2. **Generate the Dockerfile**:
   ```bash
   ./crypt-keeper.sh generate ubuntu kinetic
   ./crypt-keeper.sh generate debian sid
   ```

3. **Build and test the image**:
   ```bash
   docker build --tag debbuilder:ubuntu-kinetic ubuntu/kinetic
   docker run -v $(pwd)/tests:/sources -v $(pwd)/output:/output debbuilder:ubuntu-kinetic
   ```

4. **Generate all versions** (optional):
   ```bash
   ./crypt-keeper.sh generate all
   ```

### Customizing the build process

The build process can be customized by modifying:
- `assets/build` - Main build script (copied to all generated versions)
- `assets/transient/setup.sh` - Container setup script (copied to all generated versions)
- `crypt-keeper.sh` - Dockerfile generation script

**Note**: Changes to `assets/build` and `assets/transient/setup.sh` will only affect newly generated versions. To update existing versions, regenerate them with `./crypt-keeper.sh generate all`.

## Version Control and Dist Tags

For detailed information about version control strategy and the dist tag system (similar to RPM's `%{?dist}`), see [VERSION_CONTROL.md](VERSION_CONTROL.md).
