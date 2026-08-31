# Usage: .\build_lambda.ps1 create_case
# Produces build\<LambdaName>.zip - upload this directly to your Lambda function.
# Available: create_case get_case confirm_case timeline advance_time daily_check

param(
    [Parameter(Mandatory=$true)]
    [string]$LambdaName
)

$BuildDir = "build/$LambdaName"
if (Test-Path $BuildDir) { Remove-Item -Recurse -Force $BuildDir }
New-Item -ItemType Directory -Force -Path $BuildDir | Out-Null

Write-Host "Installing dependencies..."
pip install -r requirements.txt -t $BuildDir --quiet

Write-Host "Copying shared code and handler..."
Copy-Item -Recurse -Force "common" "$BuildDir/common"
Copy-Item -Force "lambdas/$LambdaName/handler.py" "$BuildDir/handler.py"

$ZipPath = "build/$LambdaName.zip"
if (Test-Path $ZipPath) { Remove-Item $ZipPath }

Write-Host "Zipping..."
Compress-Archive -Path "$BuildDir/*" -DestinationPath $ZipPath

Write-Host "Built $ZipPath"
Write-Host "Upload this file to your Lambda function (or drag-drop it in the console)."
Write-Host "In the Lambda console, set the handler to: handler.lambda_handler"
