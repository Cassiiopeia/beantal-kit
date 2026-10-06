# Apply text replacements to a pptx through PowerPoint (works on DRM decks) and save in place.
# Use on a freshly copied version file only; never on an older version.
# Edits: JSON file [{ "slide": 5, "find": "old", "replace": "new" }, ...]  (slide 0 = every slide)
param([Parameter(Mandatory = $true)][string]$Path, [Parameter(Mandatory = $true)][string]$EditsJson)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$edits = Get-Content -Raw -Encoding UTF8 $EditsJson | ConvertFrom-Json
$app = New-Object -ComObject PowerPoint.Application
$results = @()
try {
  $p = $app.Presentations.Open($Path, 0, 0, 0)
  foreach ($e in $edits) {
    $n = 0
    $slides = if ([int]$e.slide -eq 0) { 1..$p.Slides.Count } else { @([int]$e.slide) }
    foreach ($i in $slides) {
      foreach ($sh in $p.Slides.Item($i).Shapes) {
        $stack = @($sh)
        while ($stack.Count) {
          $cur = $stack[0]; $stack = $stack[1..($stack.Count)] | Where-Object { $_ }
          if ($cur.Type -eq 6) { foreach ($c in $cur.GroupItems) { $stack += $c } ; continue }
          if ($cur.HasTextFrame -and $cur.TextFrame.HasText) {
            while ($true) {
              $r = $cur.TextFrame.TextRange.Replace([string]$e.find, [string]$e.replace)
              if ($null -eq $r) { break }
              $n++
              if ([string]$e.replace -like ('*' + [string]$e.find + '*')) { break }
            }
          }
          if ($cur.HasTable) {
            foreach ($row in $cur.Table.Rows) { foreach ($cell in $row.Cells) {
              $tr = $cell.Shape.TextFrame.TextRange
              while ($true) { $r = $tr.Replace([string]$e.find, [string]$e.replace); if ($null -eq $r) { break }; $n++; if ([string]$e.replace -like ('*' + [string]$e.find + '*')) { break } }
            } }
          }
        }
      }
    }
    $results += @{ slide = [int]$e.slide; find = [string]$e.find; replaced = $n }
  }
  $p.Save(); $p.Close()
  @{ ok = $true; results = $results } | ConvertTo-Json -Compress -Depth 4
} finally {
  $app.Quit(); [void][Runtime.InteropServices.Marshal]::ReleaseComObject($app)
}
