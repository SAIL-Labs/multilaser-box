# Installation Guide

## Quick Start with Conda (Recommended)

This is the easiest way to get started. The conda environment will install all dependencies and the package with shortcuts.

### Step 1: Create the Environment

```bash
# Navigate to the project directory
cd /path/to/multilaser-box

# Create the conda environment from the environment.yml file
conda env create -f environment.yml
```

This will:
- Create a new conda environment named "multilaser"
- Install Python 3.7+ and all required dependencies
- Install the multilaser package in editable mode
- Create the `multilaser` and `multilaser-gui` command shortcuts

### Step 2: Activate the Environment

```bash
conda activate multilaser
```

### Step 3: Run the Application

Simply type:

```bash
multilaser
```

The GUI will launch!

## Alternative: pip Installation

If you prefer to use pip instead of conda:

```bash
# Install in editable mode
pip install -e .

# Run the application
multilaser
```

## Verifying Installation

To verify the installation was successful:

```bash
# Check if the command is available
which multilaser

# Try to run it
multilaser --help  # This will launch the GUI (no --help option implemented yet)
```

## Updating the Environment

If you make changes to the code or dependencies:

```bash
# Update the conda environment
conda env update -f environment.yml --prune

# Or if using pip
pip install -e . --upgrade
```

## Uninstalling

To remove the conda environment:

```bash
conda deactivate
conda env remove -n multilaser
```

To uninstall with pip:

```bash
pip uninstall multilaser-controller
```

## Troubleshooting

### Command not found after installation

If `multilaser` command is not found:

1. Make sure you've activated the conda environment:
   ```bash
   conda activate multilaser
   ```

2. Verify the package is installed:
   ```bash
   pip list | grep multilaser
   ```

3. Try reinstalling:
   ```bash
   pip install -e . --force-reinstall
   ```

### Import errors

If you get import errors when running:

1. Check that all dependencies are installed:
   ```bash
   conda list
   # Should show: numpy, pyserial, pyqt6
   ```

2. Reinstall dependencies:
   ```bash
   conda env update -f environment.yml --prune
   ```

### Serial port access issues

On Linux, you may need to add your user to the dialout group:

```bash
sudo usermod -a -G dialout $USER
# Log out and log back in for this to take effect
```

On macOS, no special permissions are typically needed.

On Windows, ensure the Arduino drivers are properly installed.
