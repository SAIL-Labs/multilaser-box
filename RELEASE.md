# Release Guide

This document explains how to create releases with standalone executables for Windows and macOS.

## Automated Releases via GitHub Actions

The project includes a GitHub Actions workflow that automatically builds standalone executables for Windows and macOS.

### Creating a Release

#### Method 1: Create a Git Tag (Recommended)

When you push a version tag, the workflow automatically builds executables and creates a GitHub release.

```bash
# Create and push a version tag
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin v1.0.0
```

The workflow will:
1. Build Windows `.exe` executable
2. Build macOS `.app` bundle
3. Package all necessary files (README, manual, Arduino firmware)
4. Create a GitHub release with downloadable archives
5. Attach `MultiLaserController-Windows.zip` and `MultiLaserController-macOS.tar.gz`

#### Method 2: Manual Trigger

You can also manually trigger the workflow from the GitHub Actions tab:

1. Go to your repository on GitHub
2. Click on "Actions" tab
3. Select "Build Standalone Executables" workflow
4. Click "Run workflow"
5. Optionally specify a version number
6. Click "Run workflow" button

This will build the executables but won't create a GitHub release (unless triggered from a tag).

### What Gets Built

#### Windows Package (`MultiLaserController-Windows.zip`)
- `MultiLaserController.exe` - Standalone executable
- `README.md` - User documentation
- `multilaser_manual.md` - Detailed manual
- `laser_ttl_controller/` - Arduino firmware files

#### macOS Package (`MultiLaserController-macOS.tar.gz`)
- `MultiLaserController.app` - macOS application bundle
- `README.md` - User documentation
- `multilaser_manual.md` - Detailed manual
- `laser_ttl_controller/` - Arduino firmware files

### Workflow Features

- **Automatic builds** on version tags (e.g., `v1.0.0`, `v2.1.3`)
- **Manual trigger** option for testing
- **Fallback mechanism** if icon files are missing
- **Includes all necessary files** (documentation, firmware)
- **Cross-platform** builds on native runners for best compatibility

## Manual Local Builds

If you need to build executables manually on your local machine:

### Windows Build

```bash
# Install dependencies
pip install -r requirements.txt
pip install pyinstaller

# Build using spec file (recommended)
pyinstaller multilaser.spec

# Or build with command line
pyinstaller --onefile --windowed --name=MultiLaserController laser_controller_gui.py

# Executable will be in dist/MultiLaserController.exe
```

### macOS Build

```bash
# Install dependencies
pip install -r requirements.txt
pip install pyinstaller

# Build using spec file (recommended)
pyinstaller multilaser.spec

# Or build with command line
pyinstaller --onefile --windowed --name=MultiLaserController laser_controller_gui.py

# Application will be in dist/MultiLaserController.app
```

### Linux Build (Not in CI)

```bash
# Install dependencies
pip install -r requirements.txt
pip install pyinstaller

# Build
pyinstaller --onefile --name=MultiLaserController laser_controller_gui.py

# Executable will be in dist/MultiLaserController
```

## Customizing the Build

### Using the Spec File

The `multilaser.spec` file provides advanced customization options:

- **Adding data files**: Modify the `datas` list
- **Hidden imports**: Add to `hiddenimports` if modules aren't detected
- **Excluding modules**: Add to `excludes` to reduce size
- **Icons**: Uncomment and set icon paths for `.ico` (Windows) and `.icns` (macOS)
- **Console mode**: Set `console=True` for debugging

To use the spec file:

```bash
pyinstaller multilaser.spec
```

### Adding Application Icons

To add custom icons:

1. Create icon files:
   - Windows: `figures/icon.ico` (256x256 or multiple sizes)
   - macOS: `figures/icon.icns` (multiple resolutions)

2. Update the spec file:
   ```python
   exe = EXE(
       ...
       icon='figures/icon.ico',  # Uncomment this line
   )

   app = BUNDLE(
       ...
       icon='figures/icon.icns',  # Set the icon path
   )
   ```

3. Update the GitHub Actions workflow to remove `continue-on-error: true`

## Version Numbering

Follow semantic versioning (SemVer):

- `v1.0.0` - Major release (breaking changes)
- `v1.1.0` - Minor release (new features, backwards compatible)
- `v1.1.1` - Patch release (bug fixes)

## Pre-release Checklist

Before creating a release:

- [ ] Update version number in `setup.py`
- [ ] Update version in `multilaser.spec` info_plist
- [ ] Test on target platforms (Windows, macOS)
- [ ] Update `README.md` if needed
- [ ] Update `CLAUDE.MD` with recent changes
- [ ] Ensure all tests pass
- [ ] Update `multilaser_manual.md` if features changed
- [ ] Check Arduino firmware is up to date

## Testing Releases

After creating a release:

1. Download the executables from GitHub Releases
2. Test on clean systems (no Python installed)
3. Verify Arduino connection works
4. Test all laser control functions
5. Check emergency stop functionality
6. Verify documentation is included

## Troubleshooting Builds

### Build fails with missing modules

Add them to `hiddenimports` in `multilaser.spec`:

```python
hiddenimports=[
    'PyQt6.QtCore',
    'your.missing.module',
],
```

### Executable is too large

Add unused modules to `excludes` in `multilaser.spec`:

```python
excludes=[
    'matplotlib',
    'pandas',
    'scipy',
],
```

### Application won't start

1. Build with console enabled for debugging:
   ```python
   console=True  # in multilaser.spec
   ```

2. Check for missing dependencies or data files

### macOS Gatekeeper blocks app

Users need to:
1. Right-click the app
2. Select "Open"
3. Click "Open" in the dialog

Or disable Gatekeeper (not recommended):
```bash
sudo xattr -rd com.apple.quarantine MultiLaserController.app
```

### Windows Defender blocks executable

This is common for unsigned executables. Options:

1. Code sign the executable (requires certificate)
2. Ask users to add exception
3. Submit to Microsoft for analysis

## GitHub Actions Logs

To debug build issues:

1. Go to repository > Actions tab
2. Click on the failed workflow run
3. Expand the failed step to see error logs
4. Check Python version, dependency installation, and PyInstaller output
