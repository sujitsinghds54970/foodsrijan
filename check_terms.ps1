# Verify current state of a sample TSX file and a sample Python file
$fe = Get-ChildItem "c:\Users\Sujit Rajput\Food startup Management ERP\frontend\vaidya-vihar-frontend\src" -Recurse -Include "*.tsx" | Select-Object -First 3
foreach ($f in $fe) {
    $c = Get-Content $f.FullName -Raw
    $cust = [regex]::Matches($c, 'Customer').Count
    $pat  = [regex]::Matches($c, 'Patient').Count
    $doc  = [regex]::Matches($c, 'Doctor').Count
    $stf  = [regex]::Matches($c, 'Staff').Count
    Write-Host "$($f.Name): Customer=$cust Patient=$pat Doctor=$doc Staff=$stf"
}

Write-Host ""
$be = Get-ChildItem "c:\Users\Sujit Rajput\Food startup Management ERP\backend\app" -Recurse -Include "*.py" | Select-Object -First 3
foreach ($f in $be) {
    $c = Get-Content $f.FullName -Raw
    $cust = [regex]::Matches($c, 'Customer').Count
    $pat  = [regex]::Matches($c, 'Patient').Count
    $doc  = [regex]::Matches($c, 'Doctor').Count
    $stf  = [regex]::Matches($c, 'Staff').Count
    Write-Host "$($f.Name): Customer=$cust Patient=$pat Doctor=$doc Staff=$stf"
}
