#!/usr/bin/env pwsh
# Push_Version.ps1 - Script to tag and push a new version
#
# This script handles the tagging workflow for releasing a new version:
# 1. Creates an annotated git tag for the version
# 2. Pushes the tag to GitHub
#
# Assumes version changes have already been committed and pushed.
#
# Usage:
#   .\Push_Version.ps1 -Version "3.6.1"

param(
    [Parameter(Mandatory=$true)]
    [string]$Version
)

# Colors for output
$Green = "`e[32m"
$Yellow = "`e[33m"
$Red = "`e[31m"
$Reset = "`e[0m"

function Write-Success($msg) { Write-Host "$Green✅ $msg$Reset" }
function Write-Info($msg) { Write-Host "$Yellow📋 $msg$Reset" }
function Write-Error($msg) { Write-Host "$Red❌ $msg$Reset" }

try {
    Write-Info "Starting version tagging process for v$Version..."
    
    # Check if we're in a git repository
    if (-not (Test-Path ".git")) {
        Write-Error "Not in a git repository!"
        exit 1
    }
    
    # Default commit message if not provided
    if (-not $Message) {
        $Message = "Release v$Version"
    }
    
    # Step 1: Create annotated tag
    Write-Info "Creating annotated tag v$Version..."
    $tagMessage = "Version $Version

See CHANGELOG.md for details of changes in this release."
    
    git tag -a "v$Version" -m $tagMessage
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Git tag creation failed!"
        exit 1
    }
    Write-Success "Tag v$Version created"
    
    # Step 2: Push tag
    Write-Info "Pushing tag to GitHub..."
    git push origin "v$Version"
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Git push tags failed!"
        exit 1
    }
    Write-Success "Tag v$Version pushed"
    
    # Summary
    Write-Host ""
    Write-Success "Version $Version successfully tagged and pushed!"
    Write-Info "Summary:"
    Write-Host "  - Created annotated tag v$Version"
    Write-Host "  - Pushed tag to GitHub"
    Write-Host ""
    Write-Info "Next steps:"
    Write-Host "  - Check GitHub for the new tag: https://github.com/dterracino/color_tools/releases"
    Write-Host "  - Build and publish to PyPI: .\publish.ps1"
    
} catch {
    Write-Error "An error occurred: $_"
    exit 1
}