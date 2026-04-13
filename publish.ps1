# publish.ps1 - Build and publish color_tools to PyPI
# This script handles the complete build and upload process
#
# API Key Setup (in priority order):
#
# 1. Automatic from .env file (RECOMMENDED - easiest!)
#    - Copy .env.example to .env
#    - Add your PyPI API token: PYPI_API_KEY=pypi-...
#    - Script automatically loads it on every run
#    - For TestPyPI: TESTPYPI_API_KEY=pypi-...
#
# 2. Set environment variable before running
#    $env:TWINE_PASSWORD = "pypi-your-api-key-here"
#    .\publish.ps1
#
# 3. Let twine prompt for password (paste API key when asked)
#    .\publish.ps1
#
# 4. Configure twine once (stored in config file)
#    python -m twine configure
#    .\publish.ps1

param(
    [switch]$TestPyPI,
    [switch]$SkipTests,
    [switch]$SkipClean,
    [switch]$BuildOnly
)

# Color output helpers
function Write-Step { param($msg) Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Write-Success { param($msg) Write-Host "[OK] $msg" -ForegroundColor Green }
function Write-Error { param($msg) Write-Host "[ERROR] $msg" -ForegroundColor Red }
function Write-Warning { param($msg) Write-Host "[WARN] $msg" -ForegroundColor Yellow }

# Exit on error
$ErrorActionPreference = "Stop"

# Auto-load API key from .env file if it exists
if (Test-Path ".env") {
    Write-Host "Loading API key from .env file..." -ForegroundColor Cyan
    Get-Content .env | ForEach-Object {
        if ($_ -match '^([^=]+)=(.*)$') {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim()
            # Remove surrounding quotes if present
            $value = $value.Trim('"').Trim("'")
            [Environment]::SetEnvironmentVariable($key, $value, "Process")
        }
    }
    
    # Set TWINE_PASSWORD from PYPI_API_KEY or TESTPYPI_API_KEY
    if ($TestPyPI -and $env:TESTPYPI_API_KEY) {
        $env:TWINE_PASSWORD = $env:TESTPYPI_API_KEY
        Write-Success "Using TestPyPI API key from .env"
    } elseif ($env:PYPI_API_KEY) {
        $env:TWINE_PASSWORD = $env:PYPI_API_KEY
        Write-Success "Using PyPI API key from .env"
    } else {
        Write-Warning ".env file found but no API key configured"
    }
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  Color Tools - PyPI Publishing Script" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Step 1: Clean previous builds
if (-not $SkipClean) {
    Write-Step "Cleaning previous build artifacts"
    if (Test-Path ".\clean.ps1") {
        & .\clean.ps1
    } else {
        Write-Warning "clean.ps1 not found, skipping clean step"
    }
} else {
    Write-Warning "Skipping clean step (--SkipClean)"
}

# Step 2: Run tests
if (-not $SkipTests) {
    Write-Step "Running unit tests"
    python -m unittest discover -b -s tests -p "test_*.py"
    if ($LASTEXITCODE -eq 0) {
        Write-Success "All tests passed"
    } else {
        Write-Error "Tests failed!"
        exit 1
    }
} else {
    Write-Warning "Skipping tests (--SkipTests)"
}

# Step 3: Verify version number
Write-Step "Verifying version number"
try {
    $version = python -c "from color_tools import __version__; print(__version__)" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Version: $version"
        
        # Skip confirmation if BuildOnly
        if (-not $BuildOnly) {
            # Confirm with user
            $confirm = Read-Host "`nPublish version $version to PyPI? (y/N)"
            if ($confirm -ne 'y' -and $confirm -ne 'Y') {
                Write-Warning "Publish cancelled by user"
                exit 0
            }
        } else {
            Write-Warning "Build-only mode - will not upload to PyPI"
        }
    } else {
        Write-Error "Failed to get version number"
        exit 1
    }
} catch {
    Write-Error "Failed to verify version: $_"
    exit 1
}

# Step 4: Build package
Write-Step "Building distribution packages"
try {
    python -m build
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Build completed successfully"
        
        # Show what was built
        if (Test-Path "dist") {
            Write-Host "`nBuilt packages:" -ForegroundColor Yellow
            Get-ChildItem dist -Filter "*$version*" | ForEach-Object {
                Write-Host "  - $($_.Name)" -ForegroundColor White
            }
        }
    } else {
        Write-Error "Build failed!"
        exit 1
    }
} catch {
    Write-Error "Failed to build package: $_"
    exit 1
}

# Step 5: Upload to PyPI
if (-not $BuildOnly) {
    Write-Step "Uploading to PyPI"

    if ($TestPyPI) {
        Write-Warning "Uploading to TestPyPI (test.pypi.org)"
        $repository = "--repository testpypi"
    } else {
        Write-Host "Uploading to PyPI (pypi.org)" -ForegroundColor Yellow
        $repository = ""
    }

    try {
        if ($repository) {
            python -m twine upload $repository dist/*$version*
        } else {
            python -m twine upload dist/*$version*
        }
        
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Upload completed successfully!"
            
            Write-Host "`n========================================" -ForegroundColor Green
            Write-Host "       Publication Successful!          " -ForegroundColor Green
            Write-Host "========================================`n" -ForegroundColor Green
            
            if ($TestPyPI) {
                Write-Host "Install with: pip install --index-url https://test.pypi.org/simple/ color-match-tools" -ForegroundColor Cyan
            } else {
                Write-Host "Install with: pip install color-match-tools" -ForegroundColor Cyan
            }
            Write-Host "Version: $version`n" -ForegroundColor Cyan
        } else {
            Write-Error "Upload failed!"
            exit 1
        }
    } catch {
        Write-Error "Failed to upload: $_"
        exit 1
    }

    # Optional: Clean up after successful publish
    $cleanAfter = Read-Host "`nClean up build artifacts? (y/N)"
    if ($cleanAfter -eq 'y' -or $cleanAfter -eq 'Y') {
        Write-Step "Cleaning build artifacts"
        & .\clean.ps1
    }
} else {
    Write-Host "`n========================================" -ForegroundColor Green
    Write-Host "       Build Only Complete!            " -ForegroundColor Green  
    Write-Host "========================================`n" -ForegroundColor Green
    Write-Host "Built packages are ready in dist/ directory" -ForegroundColor Cyan
    Write-Host "Version: $version`n" -ForegroundColor Cyan
}

Write-Host "`nDone!`n" -ForegroundColor Green
