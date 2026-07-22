$files = Get-ChildItem "A:\Packages\Transcript2MDSlides\Output\*SLIDES*.html" |
  Where-Object { $_.LastWriteTime -ge [datetime]"2/12/2026 10:30 AM" }

Write-Host "Found $($files.Count) matching file(s):"
$files | ForEach-Object { Write-Host "  $($_.Name)  ($($_.LastWriteTime))" }

$files | ForEach-Object { Start-Process chrome $_.FullName }