# How to Update the Version Number

The version number is centralized in a single location for easy updates.

## Quick Method: Edit the VERSION File

**Simply edit the `VERSION` file in the repository root:**

```bash
echo "0.5.0" > VERSION
```

Or open `VERSION` in your text editor and change the version number.

That's it! The version will automatically propagate to:
- `multilaser/__init__.py` (`__version__`)
- `setup.py` (package version)
- All PyInstaller builds (via imported `__version__`)

## Alternative Method: Edit _version.py

You can also edit `multilaser/_version.py` directly:

```python
__version__ = "0.5.0"
```

## After Updating the Version

1. **Update the README.md version history** if needed
2. **Commit your changes:**
   ```bash
   git add VERSION
   git commit -m "Bump version to 0.5.0"
   ```

3. **Create a git tag for release:**
   ```bash
   git tag -a v0.5.0 -m "Release version 0.5.0"
   git push origin main
   git push origin v0.5.0
   ```

4. **GitHub Actions** will automatically build executables when you push the tag

## Version Numbering Guidelines

Follow Semantic Versioning (SemVer):

- **Major version** (1.0.0 → 2.0.0): Breaking changes, incompatible API changes
- **Minor version** (1.0.0 → 1.1.0): New features, backwards compatible
- **Patch version** (1.0.0 → 1.0.1): Bug fixes, backwards compatible

Examples:
- `0.4.2` → `0.4.3` (bug fix)
- `0.4.2` → `0.5.0` (new feature)
- `0.4.2` → `1.0.0` (major release, breaking changes)

## Verifying the Version

After updating, verify the version propagated correctly:

```bash
# Check Python package version
python -c "import multilaser; print(multilaser.__version__)"

# Check setup.py
python setup.py --version

# View VERSION file
cat VERSION
```
