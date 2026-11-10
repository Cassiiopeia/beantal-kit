# PowerPoint helper for the HTML workflow. ASCII-only on purpose (Windows PowerShell 5.1 reads scripts as ANSI).
#   -Mode plain  : open -Path read-only and save a plain copy to -Out (put -Out in the temp folder: DRM leaves it plain)
#   -Mode saveas : open -Path (a plain pptx) and save it as -Out (PowerPoint applies the PC's DRM as usual)
#   -Mode export : export shapes listed in -ListJson ([{slide, id, out}]) of -Path to PNG
# The user's own open PowerPoint windows are left alone (Quit only when PowerPoint had nothing open).
param(
  [Parameter(Mandatory = $true)][string]$Mode,
  [Parameter(Mandatory = $true)][string]$Path,
  [string]$Out, [string]$ListJson
)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

function Find-Shape($shapes, $id) {
  foreach ($sh in $shapes) {
    if ($sh.Id -eq $id) { return $sh }
    if ($sh.Type -eq 6) { $c = Find-Shape $sh.GroupItems $id; if ($c) { return $c } }
  }
  return $null
}

$app = New-Object -ComObject PowerPoint.Application
$before = $app.Presentations.Count
$p = $null
try {
  if ($Mode -eq 'plain') {
    $p = $app.Presentations.Open($Path, -1, 0, 0)
    $p.SaveCopyAs($Out)
    $res = @{ ok = $true; out = $Out }
  } elseif ($Mode -eq 'saveas') {
    $p = $app.Presentations.Open($Path, 0, 0, 0)
    $p.SaveAs($Out, 24)
    $res = @{ ok = $true; out = $Out }
  } elseif ($Mode -eq 'export') {
    $items = Get-Content -Raw -Encoding UTF8 $ListJson | ConvertFrom-Json
    $p = $app.Presentations.Open($Path, -1, 0, 0)
    $done = 0; $failed = @()
    foreach ($it in $items) {
      try {
        $sh = Find-Shape $p.Slides.Item([int]$it.slide).Shapes ([int]$it.id)
        if ($null -eq $sh) { $failed += ('{0}-{1} not found' -f $it.slide, $it.id); continue }
        $sh.Export([string]$it.out, 2, 0, 0, 1); $done++
      } catch { $failed += ('{0}-{1} {2}' -f $it.slide, $it.id, $_.Exception.Message) }
    }
    $res = @{ ok = $true; exported = $done; failed = $failed }
  } else { throw "unknown mode $Mode" }
  if ($p) { $p.Close(); $p = $null }
  $res | ConvertTo-Json -Compress -Depth 4
} finally {
  if ($p) { try { $p.Close() } catch {} }
  if ($before -eq 0 -and $app.Presentations.Count -eq 0) { $app.Quit() }
  [void][Runtime.InteropServices.Marshal]::ReleaseComObject($app)
}
