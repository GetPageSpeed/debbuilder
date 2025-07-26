https://chatgpt.com/c/66eeef52-90fc-8011-8554-a025ed2c2438

# DEB builder Docker images

This project provides Docker images for building Debian packages (.deb files) across different Ubuntu distributions. It's designed to be simple to use - just mount a directory containing a `debian` folder and get built .deb files as output.

## Features

- **Fast builds**: Optimized for quick package building with proper dependency handling
- **Multiple Ubuntu versions**: Support for different Ubuntu releases (Focal, Noble, etc.)
- **Simple usage**: Just mount your source directory and get .deb files as output
- **Robust error handling**: Retry logic for network operations and better error reporting

## Available versions

Currently supported Ubuntu and Debian versions:
- `ubuntu/focal` - Ubuntu 20.04 LTS
- `ubuntu/jammy` - Ubuntu 22.04 LTS  
- `ubuntu/noble` - Ubuntu 24.04 LTS
- `debian/bookworm` - Debian 12
- `debian/trixie` - Debian 13 (testing)

## Docker Image Tags

The debbuilder images use multiple tag formats for flexibility:

### Primary Tags (Full Names)
- `getpagespeed/debuilder:ubuntu-noble`
- `getpagespeed/debuilder:ubuntu-jammy`
- `getpagespeed/debuilder:debian-bookworm`

### Dist Tags (Version Numbers - Similar to RPM %{?dist})
- `getpagespeed/debuilder:ubuntu24.04` (for noble/24.04)
- `getpagespeed/debuilder:ubuntu22.04` (for jammy/22.04)
- `getpagespeed/debuilder:ubuntu20.04` (for focal/20.04)
- `getpagespeed/debuilder:debian12` (for bookworm/12)
- `getpagespeed/debuilder:debian13` (for trixie/13)

### Alternative Tags (Short Names)
- `getpagespeed/debuilder:ubuntunoble`
- `getpagespeed/debuilder:ubuntujammy`
- `getpagespeed/debuilder:debianbookworm`

**Usage Examples:**
```bash
# Using full name
docker run -v /path/to/source:/sources -v /path/to/output:/output getpagespeed/debuilder:ubuntu-noble

# Using dist tag (recommended for CI/CD - similar to RPM's el7, fc38)
docker run -v /path/to/source:/sources -v /path/to/output:/output getpagespeed/debuilder:ubuntu24.04

# Using short name
docker run -v /path/to/source:/sources -v /path/to/output:/output getpagespeed/debuilder:ubuntunoble
```

## Quick Start

### 1. Generate Dockerfiles for all supported versions

```bash
# Generate all versions
./crypt-keeper.sh generate all

# Or generate a specific version
./crypt-keeper.sh generate ubuntu noble
./crypt-keeper.sh generate debian bookworm
```

### 2. Build the Docker images

```bash
# Build a specific version locally
docker build --tag debbuilder:ubuntu-noble ubuntu/noble
docker build --tag debbuilder:ubuntu-jammy ubuntu/jammy
docker build --tag debbuilder:debian-bookworm debian/bookworm

# Or build all versions locally (without pushing to registry)
for version in focal jammy noble; do
    docker build --tag debbuilder:ubuntu-$version ubuntu/$version
done

# Note: The crypt-keeper build command pushes to Docker Hub registry
# ./crypt-keeper.sh build all  # Requires Docker Hub authentication
```

### 3. Build a package

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

### 4. Example with test package

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
