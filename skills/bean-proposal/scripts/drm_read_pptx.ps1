# Read a (DRM-protected) pptx through PowerPoint, read-only, and print its structure as JSON.
# No decrypted copy is written to disk. ASCII-only on purpose (Windows PowerShell 5.1 reads scripts as ANSI).
param([Parameter(Mandatory = $true)][string]$Path)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

function Cm($v) { if ($null -eq $v) { return $null }; return [math]::Round($v / 28.3465, 2) }
function Hex($rgb) { if ($null -eq $rgb) { return $null }; $r = $rgb -band 0xFF; $g = ($rgb -shr 8) -band 0xFF; $b = ($rgb -shr 16) -band 0xFF; return ('{0:X2}{1:X2}{2:X2}' -f $r, $g, $b) }
function Clean($s) { if ($null -eq $s) { return '' }; return (($s -replace '\s+', ' ').Trim()) }

function Shape-Record($sh) {
  $rec = [ordered]@{ name = $sh.Name; left = (Cm $sh.Left); top = (Cm $sh.Top); width = (Cm $sh.Width); height = (Cm $sh.Height); kind = 'other'; text = ''; paras = @() }
  $t = $sh.Type
  if ($t -eq 13) { $rec.kind = 'picture' }
  elseif ($sh.HasChart) { $rec.kind = 'chart' }
  elseif ($sh.HasTable) {
    $rec.kind = 'table'; $rows = @()
    for ($r = 1; $r -le $sh.Table.Rows.Count; $r++) {
      $cells = @(); for ($c = 1; $c -le $sh.Table.Columns.Count; $c++) { $cells += (Clean $sh.Table.Cell($r, $c).Shape.TextFrame.TextRange.Text) }
      $rows += , $cells
    }
    $rec.table = $rows; $rec.text = (($rows | ForEach-Object { $_ -join ' | ' }) -join ' | ')
  }
  elseif ($t -eq 9) { $rec.kind = 'line' }
  elseif ($t -eq 1) { $rec.kind = 'autoshape' }
  elseif ($t -eq 17) { $rec.kind = 'textbox' }
  elseif ($t -eq 14) { $rec.kind = 'placeholder' }
  if ($sh.HasTextFrame -and $sh.TextFrame.HasText) {
    $paras = @()
    foreach ($p in $sh.TextFrame.TextRange.Paragraphs()) {
      $txt = Clean $p.Text
      if ($txt.Length -eq 0) { continue }
      $col = $null; try { if ($p.Font.Color.Type -eq 1) { $col = Hex $p.Font.Color.RGB } } catch {}
      $size = $p.Font.Size; if ($size -le 0 -or $size -gt 400) { $size = $null }
      $paras += [ordered]@{ text = $txt; size = $size; font = $p.Font.Name; bold = ($p.Font.Bold -eq -1); color = $col; level = ($p.IndentLevel - 1) }
    }
    $rec.paras = $paras
    if (-not $rec.text) { $rec.text = (($paras | ForEach-Object { $_.text }) -join ' ') }
  }
  return $rec
}

function Walk($shapes) {
  foreach ($sh in $shapes) {
    if ($sh.Type -eq 6) { Walk $sh.GroupItems } else { $sh }
  }
}

$app = New-Object -ComObject PowerPoint.Application
try {
  $p = $app.Presentations.Open($Path, -1, 0, 0)
  $slides = @()
  foreach ($s in $p.Slides) {
    $shapes = @(); foreach ($sh in (Walk $s.Shapes)) { $shapes += (Shape-Record $sh) }
    $notes = ''
    try { $notes = Clean $s.NotesPage.Shapes.Placeholders(2).TextFrame.TextRange.Text } catch {}
    $slides += [ordered]@{ n = $s.SlideIndex; layout = $s.CustomLayout.Name; notes = $notes; shapes = $shapes }
  }
  $out = [ordered]@{ size_cm = @((Cm $p.PageSetup.SlideWidth), (Cm $p.PageSetup.SlideHeight)); masters = $p.Designs.Count; slides = $slides }
  $p.Close()
  $out | ConvertTo-Json -Depth 12 -Compress
} finally {
  $app.Quit(); [void][Runtime.InteropServices.Marshal]::ReleaseComObject($app)
}
