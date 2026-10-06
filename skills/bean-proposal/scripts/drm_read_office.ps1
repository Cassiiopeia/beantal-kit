# Read a (DRM-protected) docx / xlsx / pdf through Word or Excel, read-only, and print its text as JSON.
# Same rule as drm_read_pptx.ps1: the file is opened by the Office app the DRM agent trusts, read in memory,
# closed without saving. No decrypted copy is written to disk.
# ASCII-only on purpose (Windows PowerShell 5.1 reads scripts as ANSI).
param(
  [Parameter(Mandatory = $true)][string]$Path,
  [Parameter(Mandatory = $true)][ValidateSet('docx', 'xlsx', 'pdf', 'hwp')][string]$Kind
)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

function Clean($s) { if ($null -eq $s) { return '' }; return ((("$s") -replace '[\r\n\a\x07]+', ' ' -replace '\s+', ' ').Trim()) }

function Cell-Text($v) {
  if ($null -eq $v) { return '' }
  # Excel error values (#REF!, #N/A ...) come back as Int32 around -2146826xxx
  if ($v -is [int] -and $v -lt -2146820000) { return '#ERR' }
  if ($v -is [datetime]) { if ($v.TimeOfDay.TotalSeconds -eq 0) { return $v.ToString('yyyy-MM-dd') } else { return $v.ToString('yyyy-MM-dd HH:mm') } }
  if ($v -is [double] -and $v -eq [math]::Floor($v) -and [math]::Abs($v) -lt 1e15) { return ([int64]$v).ToString() }
  return (Clean $v)
}

function Read-Word($file, $isPdf) {
  # Word shows a modal "convert this PDF" notice that hangs a hidden instance.
  # Turn it off for this run only (HKCU, restored in finally).
  $optKey = 'HKCU:\Software\Microsoft\Office\16.0\Word\Options'
  $prevPdfWarn = $null
  if ($isPdf) {
    if (-not (Test-Path $optKey)) { New-Item -Path $optKey -Force | Out-Null }
    $prevPdfWarn = (Get-ItemProperty -Path $optKey -Name DisableConvertPdfWarning -ErrorAction SilentlyContinue).DisableConvertPdfWarning
    Set-ItemProperty -Path $optKey -Name DisableConvertPdfWarning -Value 1 -Type DWord
  }
  $app = New-Object -ComObject Word.Application
  $app.Visible = $false
  $app.DisplayAlerts = 0
  try {
    # Open(FileName, ConfirmConversions, ReadOnly, AddToRecentFiles) - Word's COM signature wants [ref] in PS 5.1
    $f = [string]$file; $no = $false; $yes = $true
    $doc = $app.Documents.Open([ref]$f, [ref]$no, [ref]$yes, [ref]$no)
    $paras = @()
    foreach ($p in $doc.Paragraphs) {
      $txt = Clean $p.Range.Text
      if ($txt.Length -eq 0) { continue }
      $inTable = $false; try { $inTable = [bool]$p.Range.Information(12) } catch {}
      if ($inTable) { continue }
      $style = ''; try { $style = $p.Style.NameLocal } catch {}
      $paras += [ordered]@{ text = $txt; style = $style }
    }
    $tables = @()
    foreach ($t in $doc.Tables) {
      $rows = @()
      for ($r = 1; $r -le $t.Rows.Count; $r++) {
        $cells = @()
        for ($c = 1; $c -le $t.Columns.Count; $c++) {
          $v = ''; try { $v = Clean $t.Cell($r, $c).Range.Text } catch {}
          $cells += $v
        }
        $rows += , $cells
      }
      $tables += , $rows
    }
    $dontSave = 0; $doc.Close([ref]$dontSave)
    if ($isPdf) {
      # Word reflows the pdf into paragraphs; there are no real page breaks, so treat it as one page.
      $lines = @(); foreach ($p in $paras) { $lines += $p.text }
      foreach ($t in $tables) { foreach ($row in $t) { $lines += ('| ' + ($row -join ' | ') + ' |') } }
      return [ordered]@{ pages = @([ordered]@{ n = 1; text = ($lines -join "`n") }); via = 'word' }
    }
    return [ordered]@{ paras = $paras; tables = $tables; via = 'word' }
  } finally {
    $dontSave = 0; try { $app.Quit([ref]$dontSave) } catch { try { $app.Quit() } catch {} }; [void][Runtime.InteropServices.Marshal]::ReleaseComObject($app)
    if ($isPdf) {
      if ($null -eq $prevPdfWarn) { Remove-ItemProperty -Path $optKey -Name DisableConvertPdfWarning -ErrorAction SilentlyContinue }
      else { Set-ItemProperty -Path $optKey -Name DisableConvertPdfWarning -Value $prevPdfWarn -Type DWord }
    }
  }
}

function Read-Excel($file) {
  $app = New-Object -ComObject Excel.Application
  $app.Visible = $false
  $app.DisplayAlerts = $false
  $app.EnableEvents = $false
  try { $app.AutomationSecurity = 3 } catch {}  # msoAutomationSecurityForceDisable: never run macros
  try {
    # Open(Filename, UpdateLinks=0, ReadOnly=true)
    $wb = $app.Workbooks.Open($file, 0, $true)
    $sheets = [ordered]@{}
    foreach ($ws in $wb.Worksheets) {
      $ur = $ws.UsedRange
      $vals = $ur.Value(10)
      $nr = $ur.Rows.Count; $nc = $ur.Columns.Count
      $rows = @()
      if ($nr -eq 1 -and $nc -eq 1) {
        $one = Cell-Text $vals
        if ($one) { $rows += , @($one) }
      } else {
        for ($r = 1; $r -le $nr; $r++) {
          $cells = @()
          for ($c = 1; $c -le $nc; $c++) { $cells += (Cell-Text $vals[$r, $c]) }
          $last = $cells.Count - 1
          while ($last -ge 0 -and $cells[$last] -eq '') { $last-- }
          if ($last -lt 0) { continue }
          # skip rows that hold nothing but formula errors (broken dashboard sheets)
          if (@($cells | Where-Object { $_ -ne '' -and $_ -ne '#ERR' }).Count -eq 0) { continue }
          $rows += , @($cells[0..$last])
        }
      }
      $sheets[$ws.Name] = $rows
    }
    $wb.Close($false)
    return [ordered]@{ sheets = $sheets; via = 'excel' }
  } finally {
    $app.Quit(); [void][Runtime.InteropServices.Marshal]::ReleaseComObject($app)
  }
}

function Read-Hangul($file) {
  # Hancom Office automation. Text is pulled into memory with GetTextFile; nothing is saved.
  $hwp = New-Object -ComObject HWPFrame.HwpObject
  try {
    try { $hwp.XHwpWindows.Item(0).Visible = $false } catch {}
    $ok = $hwp.Open($file, '', 'forceopen:true;versionwarning:false;suspendpassword:true')
    if (-not $ok) { throw 'Hangul could not open the file' }
    $txt = $hwp.GetTextFile('TEXT', '')
    $hwp.Clear(1)
    return [ordered]@{ pages = @([ordered]@{ n = 1; text = "$txt" }); via = 'hangul' }
  } finally {
    try { $hwp.Quit() } catch {}; [void][Runtime.InteropServices.Marshal]::ReleaseComObject($hwp)
  }
}

if ($Kind -eq 'xlsx') { $out = Read-Excel $Path }
elseif ($Kind -eq 'hwp') { $out = Read-Hangul $Path }
else { $out = Read-Word $Path ($Kind -eq 'pdf') }
$out | ConvertTo-Json -Depth 12 -Compress
