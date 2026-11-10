# Put every POINT bar of a pptx at the same place and size, through PowerPoint (works on DRM decks).
# A POINT bar = a shape whose text starts with "POINT" (or whose name starts with "POINT").
# -Check: read only, report positions and overlaps. Otherwise move the bars and save in place
# (use on a freshly copied version file only).
# Geometry in cm. Top < 0 means "slide height - BottomGap - Height".
# ASCII-only on purpose (Windows PowerShell 5.1 reads scripts as ANSI).
param(
  [Parameter(Mandatory = $true)][string]$Path,
  [switch]$Check,
  [double]$Left = 1.2, [double]$Top = -1, [double]$Width = -1, [double]$Height = 1.15, [double]$BottomGap = 2.45,
  [double]$Size = 11.5
)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$PT = 28.3465
function Cm($v) { return [math]::Round($v / $PT, 2) }
function Clean($s) { if ($null -eq $s) { return '' }; return (($s -replace '\s+', ' ').Trim()) }
function Walk($shapes) { foreach ($sh in $shapes) { if ($sh.Type -eq 6) { Walk $sh.GroupItems } else { $sh } } }
function Is-Point($sh) {
  if ($sh.Name -match '^(?i)point') { return $true }
  if ($sh.Top -lt $script:HalfPt) { return $false }     # the header message may also start with "POINT"
  try { if ($sh.HasTextFrame -and $sh.TextFrame.HasText) { return ($sh.TextFrame.TextRange.Text -match '^\s*POINT\b') } } catch {}
  return $false
}

$app = New-Object -ComObject PowerPoint.Application
$before = $app.Presentations.Count     # leave PowerPoint open if the user already had decks open
$readOnly = if ($Check) { -1 } else { 0 }
try {
  $p = $app.Presentations.Open($Path, $readOnly, 0, 0)
  $W = Cm $p.PageSetup.SlideWidth; $H = Cm $p.PageSetup.SlideHeight; $script:HalfPt = $p.PageSetup.SlideHeight / 2
  if ($Width -le 0) { $Width = [math]::Round($W - 2 * $Left, 2) }
  if ($Top -lt 0) { $Top = [math]::Round($H - $BottomGap - $Height, 2) }
  $footerTop = $H - 1.4
  # reference label style: the first bar whose "POINT" word is styled apart from the sentence
  $ref = $null
  foreach ($s in $p.Slides) { foreach ($sh in (Walk $s.Shapes)) {
    if ($null -eq $ref -and (Is-Point $sh)) {
      $tr = $sh.TextFrame.TextRange
      if ($tr.Length -gt 7 -and $tr.Characters(1, 5).Text -eq 'POINT' -and $tr.Characters(1, 1).Font.Color.RGB -ne $tr.Characters($tr.Length, 1).Font.Color.RGB) {
        $ref = @{ color = $tr.Characters(1, 1).Font.Color.RGB; font = $tr.Characters(1, 1).Font.Name; fill = $sh.Fill.ForeColor.RGB }
      }
    } } }
  $rows = @()
  foreach ($s in $p.Slides) {
    $points = @(); $others = @()
    foreach ($sh in (Walk $s.Shapes)) { if (Is-Point $sh) { $points += $sh } else { $others += $sh } }
    if ($points.Count -eq 0) { continue }
    $bar = $points[0]
    $was = [ordered]@{ left = (Cm $bar.Left); top = (Cm $bar.Top); width = (Cm $bar.Width); height = (Cm $bar.Height) }
    $text = Clean $bar.TextFrame.TextRange.Text
    if (-not $Check) {
      $bar.Left = $Left * $PT; $bar.Top = $Top * $PT; $bar.Width = $Width * $PT; $bar.Height = $Height * $PT
      $tf = $bar.TextFrame
      $tf.AutoSize = 0; $tf.WordWrap = -1; $tf.VerticalAnchor = 3
      $tf.MarginLeft = 0.4 * $PT; $tf.MarginRight = 0.4 * $PT; $tf.MarginTop = 0.15 * $PT; $tf.MarginBottom = 0.15 * $PT
      if ($Size -gt 0) { $tf.TextRange.Font.Size = $Size }
      try { $bar.Line.Visible = 0 } catch {}
      if ($ref) {
        $tr = $tf.TextRange
        if ($tr.Characters(1, 5).Text -eq 'POINT') { $lab = $tr.Characters(1, 5); $lab.Font.Color.RGB = $ref.color; $lab.Font.Name = $ref.font }
        $bar.Fill.Visible = -1; $bar.Fill.Solid(); $bar.Fill.ForeColor.RGB = $ref.fill
      }
    }
    # content that runs into the POINT bar (footer line, logo and page number excluded)
    $hits = @()
    foreach ($o in $others) {
      $ot = Cm $o.Top; $ob = Cm ($o.Top + $o.Height)
      if ($ot -ge $footerTop) { continue }
      if ($ob -gt ($Top - 0.1) -and $ot -lt ($Top + $Height)) { $hits += ('{0} ({1}~{2}cm)' -f $o.Name, $ot, $ob) }
    }
    $rows += [ordered]@{ slide = $s.SlideIndex; was = $was; moved = (-not $Check) -and (([math]::Abs($was.top - $Top) -gt 0.05) -or ([math]::Abs($was.left - $Left) -gt 0.05) -or ([math]::Abs($was.height - $Height) -gt 0.05) -or ([math]::Abs($was.width - $Width) -gt 0.05)); extra_points = ($points.Count - 1); overlaps = $hits; text = $text }
  }
  if (-not $Check) { $p.Save() }
  $p.Close()
  [ordered]@{ ok = $true; box = [ordered]@{ left = $Left; top = $Top; width = $Width; height = $Height }; slide_cm = @($W, $H); points = $rows } | ConvertTo-Json -Compress -Depth 6
} finally {
  if ($before -eq 0 -and $app.Presentations.Count -eq 0) { $app.Quit() }
  [void][Runtime.InteropServices.Marshal]::ReleaseComObject($app)
}
