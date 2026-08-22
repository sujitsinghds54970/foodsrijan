$f = "c:\Users\Sujit Rajput\Food startup Management ERP\backend\app\models\patient.py"
$c = Get-Content $f -Raw
Write-Host "Length: $($c.Length)"
Write-Host "Has Patient: $($c -cmatch 'Patient')"
$n = $c -creplace 'Patient','Customer'
Write-Host "Changed: $($c -ne $n)"
Write-Host "First 100 chars:"
Write-Host $c.Substring(0,[Math]::Min(100,$c.Length))
