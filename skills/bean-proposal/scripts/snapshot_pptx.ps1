# Export slides of a pptx to PNG through PowerPoint (read-only) for visual review.
# For DRM decks write only to the system temp folder and delete the images after review.
param([Parameter(Mandatory = $true)][string]$Path, [Parameter(Mandatory = $true)][string]$OutDir, [string]$Slides = '', [int]$Width = 1280)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
New-Item -ItemType Directory -Force $OutDir | Out-Null
$app = New-Object -ComObject PowerPoint.Application
try {
  $p = $app.Presentations.Open($Path, -1, 0, 0)
  $ratio = $p.PageSetup.SlideHeight / $p.PageSetup.SlideWidth
  $want = @()
  if ($Slides) { $want = $Slides.Split(',') | ForEach-Object { [int]$_ } } else { $want = 1..$p.Slides.Count }
  $files = @()
  foreach ($i in $want) {
    if ($i -lt 1 -or $i -gt $p.Slides.Count) { continue }
    $f = Join-Path $OutDir ('slide_{0:D2}.png' -f $i)
    $p.Slides.Item($i).Export($f, 'PNG', $Width, [int]($Width * $ratio))
    $files += $f
  }
  $p.Close()
  @{ ok = $true; files = $files } | ConvertTo-Json -Compress
} finally {
  $app.Quit(); [void][Runtime.InteropServices.Marshal]::ReleaseComObject($app)
}
