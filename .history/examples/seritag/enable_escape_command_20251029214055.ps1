# Enable ACR122U PC/SC Escape Command via Registry
#
# This script sets the EscapeCommandEnable registry key required for
# ACR122U escape mode (control() vs transmit()) operations.
#
# Reference: ACR122U API v2.04 Appendix A

Write-Host "================================================================================"
Write-Host "ACR122U Escape Command Registry Setup"
Write-Host "================================================================================"
Write-Host ""

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "[ERROR] This script requires Administrator privileges!" -ForegroundColor Red
    Write-Host ""
    Write-Host "To run as Administrator:"
    Write-Host "  1. Right-click PowerShell"
    Write-Host "  2. Select 'Run as Administrator'"
    Write-Host "  3. Navigate to this directory"
    Write-Host "  4. Run: .\enable_escape_command.ps1"
    Write-Host ""
    exit 1
}

Write-Host "[OK] Running with Administrator privileges" -ForegroundColor Green
Write-Host ""

# Registry path (adjust if needed for different ACR122U models)
$registryPaths = @(
    "HKLM:\SYSTEM\CurrentControlSet\Enum\USB\VID_072F&PID_2200\Device Parameters",
    "HKLM:\SYSTEM\CurrentControlSet\Enum\USB\VID_072F&PID_90CC\Device Parameters"
)

# Find the actual device path
$found = $false
$targetPath = $null

Write-Host "Searching for ACR122U device..."
Write-Host ""

$usbBase = "HKLM:\SYSTEM\CurrentControlSet\Enum\USB"
if (Test-Path $usbBase) {
    $devices = Get-ChildItem $usbBase | Where-Object { $_.Name -match "VID_072F.*PID_2200|VID_072F.*PID_90CC" }
    
    foreach ($device in $devices) {
        $deviceParamsPath = Join-Path $device.PSPath "Device Parameters"
        
        Write-Host "[FOUND] Device: $($device.Name)" -ForegroundColor Yellow
        
        if (Test-Path $deviceParamsPath) {
            Write-Host "  Device Parameters path exists: $deviceParamsPath" -ForegroundColor Green
            $targetPath = $deviceParamsPath
            $found = $true
            break
        } else {
            Write-Host "  [WARN] Device Parameters subkey not found" -ForegroundColor Yellow
            Write-Host "         Creating it..."
            
            try {
                New-Item -Path $deviceParamsPath -Force | Out-Null
                Write-Host "  [OK] Created Device Parameters subkey" -ForegroundColor Green
                $targetPath = $deviceParamsPath
                $found = $true
                break
            } catch {
                Write-Host "  [ERROR] Could not create Device Parameters: $_" -ForegroundColor Red
            }
        }
    }
}

if (-not $found) {
    Write-Host "[ERROR] ACR122U device not found in registry!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Make sure:"
    Write-Host "  1. ACR122U reader is connected via USB"
    Write-Host "  2. USB drivers are installed"
    Write-Host "  3. Device appears in Device Manager"
    Write-Host ""
    exit 1
}

Write-Host ""
Write-Host "Target registry path: $targetPath" -ForegroundColor Cyan
Write-Host ""

# Check if key already exists
$keyName = "EscapeCommandEnable"
$fullKeyPath = Join-Path $targetPath $keyName

if (Test-Path $fullKeyPath) {
    $currentValue = Get-ItemProperty -Path $targetPath -Name $keyName -ErrorAction SilentlyContinue
    
    if ($currentValue -and $currentValue.EscapeCommandEnable -eq 1) {
        Write-Host "[OK] EscapeCommandEnable already set to 1" -ForegroundColor Green
        Write-Host ""
        Write-Host "Registry key is correctly configured!"
        Write-Host ""
        exit 0
    } else {
        Write-Host "[WARN] EscapeCommandEnable exists but value is not 1" -ForegroundColor Yellow
        Write-Host "       Current value: $($currentValue.EscapeCommandEnable)" -ForegroundColor Yellow
        Write-Host ""
    }
} else {
    Write-Host "[INFO] EscapeCommandEnable key does not exist" -ForegroundColor Yellow
    Write-Host "       Will create it..."
    Write-Host ""
}

# Set the registry key
Write-Host "Setting EscapeCommandEnable = 1..." -ForegroundColor Cyan

try {
    Set-ItemProperty -Path $targetPath -Name $keyName -Value 1 -Type DWord -Force
    Write-Host "[OK] Registry key set successfully!" -ForegroundColor Green
    Write-Host ""
    
    # Verify
    $verify = Get-ItemProperty -Path $targetPath -Name $keyName -ErrorAction SilentlyContinue
    if ($verify -and $verify.EscapeCommandEnable -eq 1) {
        Write-Host "[VERIFIED] EscapeCommandEnable = 1" -ForegroundColor Green
        Write-Host ""
    }
    
} catch {
    Write-Host "[ERROR] Failed to set registry key: $_" -ForegroundColor Red
    Write-Host ""
    exit 1
}

Write-Host "================================================================================"
Write-Host "SETUP COMPLETE"
Write-Host "================================================================================"
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Unplug and replug the ACR122U reader (if connected)"
Write-Host "  2. Restart any applications using the reader"
Write-Host "  3. Test Phase 2 authentication again"
Write-Host ""
Write-Host "[NOTE] Escape mode (control() vs transmit()) should now work correctly"
Write-Host ""

