# Version Control and Dist Tags for DEB Builder

## Version Control Strategy

### Generated Directories (Excluded from Git)

The following directories are **generated** by `crypt-keeper.sh` and should **NOT** be committed to version control:

- `ubuntu/` - Generated Ubuntu Dockerfiles and assets
- `debian/` - Generated Debian Dockerfiles and assets  
- `output/` - Build output files (*.deb, *.buildinfo, *.changes)

### Source Files (Included in Git)

The following files are **source files** and should be committed:

- `assets/` - Template files used by crypt-keeper.sh
- `crypt-keeper.sh` - Script to generate Dockerfiles
- `defaults` - List of supported distributions/versions
- `README.md` - Documentation
- `test-build.sh` - Test scripts
- `example-workflow.sh` - Example workflow

### .gitignore Configuration

```bash
# Generated package files
*.deb
*.build
*.buildinfo
*.changes

# Generated directories (created by crypt-keeper.sh)
ubuntu/
debian/

# Output directories
output/

# IDE files
.idea/
.vscode/

# OS files
.DS_Store
Thumbs.db
```

## Dist Tags System

### Overview

Similar to RPM's `%{?dist}` system, the debbuilder uses multiple tag formats for Docker images to provide flexibility and clarity.

### Tag Formats

#### 1. Primary Tags (Full Names)
```
getpagespeed/debbuilder:ubuntu-noble
getpagespeed/debbuilder:ubuntu-jammy
getpagespeed/debbuilder:debian-bookworm
```

#### 2. Dist Tags (Version Numbers - Similar to RPM %{?dist})
```
getpagespeed/debbuilder:ubuntu24.04  # noble/24.04
getpagespeed/debbuilder:ubuntu22.04  # jammy/22.04
getpagespeed/debbuilder:ubuntu20.04  # focal/20.04
getpagespeed/debbuilder:debian12     # bookworm/12
getpagespeed/debbuilder:debian13     # trixie/13
```

#### 3. Alternative Tags (Short Names)
```
getpagespeed/debbuilder:ubuntunoble
getpagespeed/debbuilder:ubuntujammy
getpagespeed/debbuilder:debianbookworm
```

### Comparison with RPM System

| RPM System | DEB System | Purpose |
|------------|------------|---------|
| `el7` | `ubuntu20.04` | Major version identifier |
| `fc38` | `ubuntu22.04` | Distribution + version |
| `amzn2` | `debian12` | Platform + version |

### Usage Recommendations

#### For CI/CD Pipelines
Use dist tags for consistency (similar to RPM's el7, fc38):
```bash
docker run getpagespeed/debbuilder:ubuntu24.04
```

#### For Development
Use full names for clarity:
```bash
docker run getpagespeed/debbuilder:ubuntu-noble
```

#### For Scripts
Use short names for brevity:
```bash
docker run getpagespeed/debbuilder:ubuntunoble
```

### Adding New Versions

When adding new Ubuntu/Debian versions:

1. **Add to `defaults`**:
   ```bash
   echo "ubuntu kinetic" >> defaults
   ```

2. **Update dist tag mapping** in `crypt-keeper.sh`:
   ```bash
   case "${VERSION}" in
       kinetic) echo -n "${DOCKER_REGISTRY_USER}/debbuilder:ub22.10" ;;
   ```

3. **Generate and test**:
   ```bash
   ./crypt-keeper.sh generate ubuntu kinetic
   docker build --tag debbuilder:ubuntu-kinetic ubuntu/kinetic
   ```

**Dist Tag Naming Convention:**
- **Ubuntu**: `ubuntu` + version number (e.g., `ubuntu20.04`, `ubuntu22.04`, `ubuntu24.04`)
- **Debian**: `debian` + version number (e.g., `debian12`, `debian13`)
- **Special cases**: `ubuntu22.10` for Ubuntu 22.10, `debian-sid` for Debian unstable

**Matches real-world patterns:**
- Plesk uses `ubuntu.24.04` in package names: `mod-security-v3_3.0.14-v.ubuntu.24.04+p18.0.70.0+t250430.1158_amd64.deb`
- Our dist tags: `ubuntu24.04` (similar to Plesk's `ubuntu.24.04`)
- Consistent with RPM's `el7`, `fc38` pattern

## Workflow

### Development Workflow

1. **Clone repository** (generated directories are excluded)
2. **Generate Dockerfiles**:
   ```bash
   ./crypt-keeper.sh generate all
   ```
3. **Build images locally**:
   ```bash
   docker build --tag debbuilder:ubuntu-noble ubuntu/noble
   ```
4. **Test builds**:
   ```bash
   ./test-build.sh
   ```
5. **Commit source changes** (not generated files)

### CI/CD Workflow

1. **Generate Dockerfiles** in CI
2. **Build and push images** with multiple tags
3. **Use dist tags** in deployment scripts

### Benefits

- **Clean repository**: No generated files in version control
- **Flexible tagging**: Multiple tag formats for different use cases
- **Consistent naming**: Similar to RPM's proven dist tag system
- **Easy maintenance**: Centralized configuration in `defaults` and `crypt-keeper.sh` 
