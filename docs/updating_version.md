# How to Update the Version Number

## Version Management System

**For releases**, git tags are the **authoritative source** of version information. The GitHub Actions workflow automatically extracts the version from the tag that triggers the build.

**For development**, version is determined from multiple sources (in priority order):
1. `VERSION` file (if present) - for local development convenience
2. Git tags (`git describe --tags`) - for git-based development workflows
3. Fallback to `"0.0.0-dev"` for unknown builds

## Creating a Release

**Simple one-step process:**

1. **Ensure all changes are committed and pushed to main:**
   ```bash
   git add .
   git commit -m "Your commit message"
   git push origin main
   ```

2. **Create and push an annotated tag:**
   ```bash
   # Format: v{major}.{minor}.{patch}
   git tag -a v0.7.0 -m "Release version 0.7.0"
   git push origin v0.7.0
   ```

3. **GitHub Actions automatically:**
   - Extracts version `0.7.0` from tag `v0.7.0`
   - Builds executable: `MultiLaserController-v0.7.0.exe`
   - Creates GitHub release with versioned executable
   - Generates release notes from commit history

That's it! No need to manually edit VERSION file for releases.

## Updating VERSION File (Optional)

You can optionally update the `VERSION` file to match the release tag for local development convenience:

```bash
echo "0.7.0" > VERSION
git add VERSION
git commit -m "Update VERSION file to 0.7.0"
git push
```

**Note:** This is purely for development convenience. GitHub Actions ignores the VERSION file when building tagged releases.

## Version Numbering Guidelines

Follow Semantic Versioning (SemVer):

- **Major version** (1.0.0 → 2.0.0): Breaking changes, incompatible API changes
- **Minor version** (1.0.0 → 1.1.0): New features, backwards compatible
- **Patch version** (1.0.0 → 1.0.1): Bug fixes, backwards compatible

Examples:
- `v0.4.2` → `v0.4.3` (bug fix)
- `v0.4.2` → `v0.5.0` (new feature)
- `v0.4.2` → `v1.0.0` (major release, breaking changes)

**Tag format must be:** `v{major}.{minor}.{patch}`
- ✅ Correct: `v0.7.0`, `v1.0.0`, `v2.3.15`
- ❌ Wrong: `0.7.0`, `v1.0`, `release-1.0.0`

## Verifying the Version

After creating a release tag, verify the version is detected correctly:

```bash
# Check Python package version (from VERSION file or git tags)
python -c "import multilaser; print(multilaser.__version__)"

# Check git tags
git describe --tags --abbrev=0

# View VERSION file (may be behind git tags - that's OK)
cat VERSION
```

## Manual/Development Builds

For manual testing without creating an official release:

1. Use the workflow_dispatch trigger in GitHub Actions
2. Specify a custom version (e.g., `0.7.0-rc1`, `0.7.0-beta`)
3. Or build locally with PyInstaller (uses VERSION file or git tags)

## Deleting a Release (if needed)

If you need to delete a release tag:

```bash
# Delete local tag
git tag -d v0.7.0

# Delete remote tag
git push origin :refs/tags/v0.7.0

# Delete GitHub release (using GitHub CLI)
gh release delete v0.7.0 --yes

# Or delete via GitHub web interface: Releases → Edit → Delete release
```
