<#
.SYNOPSIS
  Inspect / dismiss modal dialogs in the running Fusion 360 process (they block the bridge).

.EXAMPLE
  .\fusion_dialog.ps1                      # list Fusion's visible top-level windows, dump any modal dialog
  .\fusion_dialog.ps1 -Click Continue      # click a button by name in the modal dialog
  .\fusion_dialog.ps1 -Select 'Suspend*'   # select a radio button / list row by (wildcard) name
  .\fusion_dialog.ps1 -Select 'Suspend*' -Click Continue
#>
param(
    [string]$Click,
    [string]$Select,
    [switch]$All          # dump every window, not just the modal one
)

Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
Add-Type @"
using System; using System.Text; using System.Runtime.InteropServices; using System.Collections.Generic;
public class FusionWinEnum {
  public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumWindowsProc cb, IntPtr lParam);
  [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr hWnd, StringBuilder sb, int max);
  [DllImport("user32.dll")] public static extern int GetClassName(IntPtr hWnd, StringBuilder sb, int max);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr hWnd);
  [DllImport("user32.dll")] public static extern bool IsWindowEnabled(IntPtr hWnd);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint pid);
  public class Win { public IntPtr Handle; public string Class; public string Title; public bool Enabled; }
  public static List<Win> List(uint targetPid) {
    var res = new List<Win>();
    EnumWindows((h, l) => {
      uint pid; GetWindowThreadProcessId(h, out pid);
      if (pid != targetPid || !IsWindowVisible(h)) return true;
      var t = new StringBuilder(512); GetWindowText(h, t, 512);
      var c = new StringBuilder(256); GetClassName(h, c, 256);
      res.Add(new Win { Handle = h, Class = c.ToString(), Title = t.ToString(), Enabled = IsWindowEnabled(h) });
      return true; }, IntPtr.Zero);
    return res; }
}
"@

$proc = Get-Process -Name Fusion360 -ErrorAction SilentlyContinue
if (-not $proc) { Write-Host 'Fusion360 is not running.'; exit 1 }

$wins = [FusionWinEnum]::List([uint32]$proc.Id)
$main = $wins | Where-Object { $_.Title -like '*Autodesk Fusion*' } | Select-Object -First 1
$modal = $wins | Where-Object { $_.Enabled -and $_.Class -like 'Qt*QWindowIcon' -and $_.Title -notlike '*Autodesk Fusion*' }

Write-Host ("Fusion pid {0}; main window enabled = {1}" -f $proc.Id, $(if ($main) { $main.Enabled } else { 'n/a' }))
foreach ($w in $wins) { Write-Host ("  {0,-10} {1,-28} enabled={2,-5} '{3}'" -f $w.Handle, $w.Class, $w.Enabled, $w.Title) }

$targets = if ($All) { $wins } else { $modal }
if (-not $targets) { Write-Host 'No modal dialog detected.'; exit 0 }

$A = [System.Windows.Automation.AutomationElement]
$ct = [System.Windows.Automation.ControlType]
foreach ($w in $targets) {
    $root = $A::FromHandle($w.Handle)
    Write-Host ("`n=== {0} [{1}] ===" -f $w.Handle, $root.Current.ClassName)
    $all = $root.FindAll([System.Windows.Automation.TreeScope]::Descendants, [System.Windows.Automation.Condition]::TrueCondition)
    foreach ($e in $all) {
        $c = $e.Current
        if (-not $c.Name -and $c.ControlType -ne $ct::Button) { continue }
        $sel = ''
        try { $sel = ' [selected=' + $e.GetCurrentPattern([System.Windows.Automation.SelectionItemPattern]::Pattern).Current.IsSelected + ']' } catch {}
        Write-Host ("  {0,-12} '{1}'{2}" -f $c.ControlType.ProgrammaticName.Replace('ControlType.', ''), ($c.Name -replace "`r?`n", ' | '), $sel)
    }
    if ($Select) {
        $hit = $null
        foreach ($e in $all) { if ($e.Current.Name -like $Select -and ($e.Current.ControlType -eq $ct::RadioButton -or $e.Current.ControlType -eq $ct::DataItem -or $e.Current.ControlType -eq $ct::ListItem)) { $hit = $e; break } }
        if ($hit) { $hit.GetCurrentPattern([System.Windows.Automation.SelectionItemPattern]::Pattern).Select(); Write-Host "-> selected '$($hit.Current.Name)'" }
        else { Write-Host "-> nothing selectable matches '$Select'" }
        Start-Sleep -Milliseconds 300
    }
    if ($Click) {
        $hit = $null
        foreach ($e in $all) { if ($e.Current.ControlType -eq $ct::Button -and $e.Current.Name -like $Click) { $hit = $e; break } }
        if ($hit) { $hit.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke(); Write-Host "-> clicked '$($hit.Current.Name)'" }
        else { Write-Host "-> no button matches '$Click'" }
    }
}
