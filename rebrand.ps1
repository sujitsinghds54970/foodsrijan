$ErrorActionPreference = "Continue"

$backend = "c:\Users\Sujit Rajput\Food startup Management ERP\backend"
$frontendSrc = "c:\Users\Sujit Rajput\Food startup Management ERP\frontend\vaidya-vihar-frontend\src"

$replacements = @(
    @('Patient', 'Customer'),
    @('patients', 'customers'),
    @('Doctor', 'Staff'),
    @('doctors', 'staff'),
    @('Test', 'MenuItem'),
    @('tests', 'menu_items'),
    @('Report', 'Order'),
    @('reports', 'orders')
)

function Apply-Replacements {
    param([string]$rootPath, [string]$extension)
    
    $files = Get-ChildItem -Path $rootPath -Recurse -Include $extension
    Write-Host "Found $($files.Count) $extension files in $rootPath"
    $count = 0
    
    foreach ($f in $files) {
        try {
            $bytes = [System.IO.File]::ReadAllBytes($f.FullName)
            $enc = New-Object System.Text.UTF8Encoding($false)
            $content = $enc.GetString($bytes)
            $modified = $content
            
            foreach ($pair in $replacements) {
                $from = $pair[0]
                $to = $pair[1]
                $modified = $modified -creplace [regex]::Escape($from), $to
            }
            
            if ($content -ne $modified) {
                $newBytes = $enc.GetBytes($modified)
                [System.IO.File]::WriteAllBytes($f.FullName, $newBytes)
                $count++
                Write-Host "  Modified: $($f.Name)"
            }
        } catch {
            Write-Host "  ERROR on $($f.Name): $_"
        }
    }
    return $count
}

Write-Host "=== Processing Backend Python files ==="
$bc = Apply-Replacements $backend "*.py"
Write-Host "Backend total: $bc files modified`n"

Write-Host "=== Processing Frontend TSX/TS files ==="
$fc1 = Apply-Replacements $frontendSrc "*.tsx"
Write-Host "Frontend TSX total: $fc1 files modified`n"

$fc2 = Apply-Replacements $frontendSrc "*.ts"
Write-Host "Frontend TS total: $fc2 files modified"

Write-Host "`nDone! Restart the backend server to apply changes."
