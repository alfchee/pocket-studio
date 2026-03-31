# Branching Strategy & CI/CD

This document describes the branching strategy and CI/CD pipeline for Pocket Studio.

## Branch Structure

```
main          <- Production-ready code, tagged releases
  └── dev     <- Integration branch for features
       └── feature/*  <- Feature branches
```

## Branch Types

### Main Branch (`main`)

- **Purpose**: Production-ready code
- **Protection**: Requires PR reviews, status checks pass
- **Auto-merge**: Never - manual only
- **On push**: Triggers CD pipeline to build and push Docker images

### Dev Branch (`dev`)

- **Purpose**: Integration branch for all features
- **Protection**: Requires PR reviews, status checks pass
- **Source**: Feature branches merge here
- **On PR**: Triggers CI pipeline to run tests and build images

### Feature Branches (`feature/*`)

- **Purpose**: Development of new features
- **Naming**: `feature/voice-cloning`, `feature/new-api`, etc.
- **Source**: Created from and merged back to `dev`
- **On PR**: Triggers CI pipeline

## Version Management

Version is managed via `VERSION` file using Semantic Versioning (SemVer):

```
MAJOR.MINOR.PATCH
```

Example: `0.1.0`

### Version Bump Types

| Type | Description | Example |
|------|-------------|---------|
| `major` | Breaking changes | `0.1.0` → `1.0.0` |
| `minor` | New features (backward compatible) | `0.1.0` → `0.2.0` |
| `patch` | Bug fixes (backward compatible) | `0.1.0` → `0.1.1` |

## CI Pipeline (ci.yml)

**Trigger**: Pull requests to `dev` or `main`

**Jobs**:
1. Checkout code
2. Set up Docker Buildx
3. Install Python dependencies
4. Lint Python code (flake8)
5. Run unit tests with coverage
6. Build all Docker profiles:
   - `pocket-tts`
   - `xtts-v2`
   - `qwen3-tts`
7. Health check for each profile

## CD Pipeline (cd.yml)

**Trigger**: Push to `main` branch OR manual workflow dispatch

**Jobs**:

### 1. Version Bump
- Reads current version from `VERSION` file
- Bumps version based on type (major/minor/patch)
- Updates `VERSION` file
- Creates Git tag
- Creates GitHub Release

### 2. Build & Push to Docker Hub
Builds and pushes all Docker profiles with version tags:

| Image | Tags |
|-------|------|
| `pocket-studio-pocket-tts` | `latest`, `v0.1.0`, `v0.1`, `v0` |
| `pocket-studio-xtts-v2` | `latest`, `v0.1.0`, `v0.1`, `v0` |
| `pocket-studio-qwen3-tts` | `latest`, `v0.1.0`, `v0.1`, `v0` |

## GitHub Actions Secrets Required

| Secret | Description |
|--------|-------------|
| `DOCKERHUB_USERNAME` | Docker Hub username |
| `DOCKERHUB_TOKEN` | Docker Hub access token |
| `HF_TOKEN` | HuggingFace token (for qwen3-tts) |

## Workflow Diagram

```
┌─────────────┐     PR      ┌─────────────────┐
│   Feature   │────────────>│       CI        │
│   Branch    │             │ (tests, build)  │
└─────────────┘             └────────┬────────┘
                                    │
                                   PR
                                    │
                                    ▼
┌─────────────┐             ┌─────────────────┐
│     dev     │<────────────│   Pull Review   │
│  (integration)│            └─────────────────┘
└──────┬──────┘
       │
       │ PR (main)
       ▼
┌─────────────┐             ┌─────────────────┐
│    main     │────────────>│       CD        │
│ (production)│             │ (version, push) │
└─────────────┘             └─────────────────┘
```

## Usage

### Creating a Feature Branch

```bash
git checkout dev
git pull origin dev
git checkout -b feature/my-new-feature
```

### Merging a Feature

```bash
git push origin feature/my-new-feature
# Create PR to dev branch
# CI runs automatically
```

### Releasing (on main)

1. Ensure `dev` is merged to `main`
2. Push to main OR use workflow dispatch
3. Select version bump type
4. Images are built and pushed to Docker Hub

## Docker Hub Images

After CD runs, images are available at:

```
docker pull pocket-studio/pocket-studio-pocket-tts:latest
docker pull pocket-studio/pocket-studio-xtts-v2:latest
docker pull pocket-studio/pocket-studio-qwen3-tts:latest
```
