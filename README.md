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

## Development

### Adding new Ubuntu versions

1. Create a new directory under `ubuntu/` (e.g., `ubuntu/jammy`)
2. Copy the Dockerfile and assets from an existing version
3. Update the base image in the Dockerfile
4. Test with a sample package

### Customizing the build process

The build process can be customized by modifying:
- `assets/build` - Main build script
- `assets/transient/setup.sh` - Container setup script
- `Dockerfile` - Container configuration
