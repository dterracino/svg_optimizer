# clean.ps1 - Clean build artifacts for color_tools
# Run this after building/publishing to PyPI to remove temporary build files

Write-Host "Cleaning build artifacts..." -ForegroundColor Cyan

# Remove build directories
$artifacts = @("dist", "build", "*.egg-info")
foreach ($item in $artifacts) {
    if (Test-Path $item) {
        Write-Host "  Removing $item" -ForegroundColor Yellow
        Remove-Item -Recurse -Force $item -ErrorAction SilentlyContinue
    }
}

# Remove all __pycache__ directories recursively
$pycacheDirs = Get-ChildItem -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue
if ($pycacheDirs) {
    Write-Host "  Removing $($pycacheDirs.Count) __pycache__ director(ies)" -ForegroundColor Yellow
    $pycacheDirs | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Host "Clean complete! ✨" -ForegroundColor Green
