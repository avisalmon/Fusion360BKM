<#
.SYNOPSIS
  Save a PNG of Fusion's main window, for the editors where `fusion.py shot` cannot work
  (schematic and 2D board have no 3D viewport: gotcha 18).

.EXAMPLE
  .\fusion_window_shot.ps1 -Out examples\11_555_blinker\media\schematic.png
  .\fusion_window_shot.ps1 -Out shot.png -Crop 0,120,0,40     # trim left,top,right,bottom pixels

  Uses PrintWindow with PW_RENDERFULLCONTENT, so the window may be behind others (not minimised).
#>
param(
    [Parameter(Mandatory = $true)][string]$Out,
    [int[]]$Crop = @(0, 0, 0, 0)
)

Add-Type -AssemblyName System.Drawing
Add-Type @"
using System; using System.Runtime.InteropServices;
public class FusionShot {
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L, T, R, B; }
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr hdc, uint flags);
  [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr h);
}
"@

$proc = Get-Process -Name Fusion360 -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1
if (-not $proc) { Write-Host 'Fusion360 is not running (or has no main window).'; exit 1 }
$h = $proc.MainWindowHandle
if ([FusionShot]::IsIconic($h)) { Write-Host 'Fusion is minimised: restore its window first.'; exit 1 }

$r = New-Object FusionShot+RECT
[void][FusionShot]::GetWindowRect($h, [ref]$r)
$w = $r.R - $r.L; $ht = $r.B - $r.T
$bmp = New-Object System.Drawing.Bitmap $w, $ht
$g = [System.Drawing.Graphics]::FromImage($bmp)
$hdc = $g.GetHdc()
$ok = [FusionShot]::PrintWindow($h, $hdc, 2)   # 2 = PW_RENDERFULLCONTENT (Qt / GPU windows)
$g.ReleaseHdc($hdc); $g.Dispose()
if (-not $ok) { Write-Host 'PrintWindow failed.'; exit 1 }

$cw = $w - $Crop[0] - $Crop[2]; $ch = $ht - $Crop[1] - $Crop[3]
$outBmp = $bmp.Clone((New-Object System.Drawing.Rectangle $Crop[0], $Crop[1], $cw, $ch), $bmp.PixelFormat)
$dir = Split-Path -Parent ([IO.Path]::GetFullPath($Out))
if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Force $dir | Out-Null }
$outBmp.Save([IO.Path]::GetFullPath($Out), [System.Drawing.Imaging.ImageFormat]::Png)
Write-Host ("saved {0} ({1} x {2})" -f $Out, $cw, $ch)
