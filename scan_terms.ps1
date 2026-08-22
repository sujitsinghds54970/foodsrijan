# Final comprehensive scan for old diagnostic terms
$root = "c:\Users\Sujit Rajput\Food startup Management ERP"
$oldTerms = @('Patient','patients','Doctor','doctors','Test','tests','Report','reports')
$extensions = @('*.py','*.tsx','*.ts')

Write-Host "Scanning for old diagnostic terms..."
$found = $false

foreach ($ext in $extensions) {
    foreach ($term in $oldTerms) {
        $hits = Get-ChildItem -Path $root -Recurse -Include $ext |
                Where-Object { $_.FullName -notmatch '\\node_modules\\' -and $_.FullName -notmatch '\\__pycache__\\' } |
                Select-String -Pattern $term -CaseSensitive -List |
                Select-Object -ExpandProperty Path
        if ($hits.Count -gt 0) {
            Write-Host "[$ext] '$term' found in $($hits.Count) file(s):"
            $hits | Select-Object -First 3 | ForEach-Object { Write-Host "  $_" }
            $found = $true
        }
    }
}

if (-not $found) {
    Write-Host "All old terms successfully replaced. No remaining occurrences found."
}
