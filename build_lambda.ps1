# Usage: .\build_lambda.ps1 create_case
# Produces build\<LambdaName>.zip - upload this directly to your Lambda function.
# Available: create_case get_case confirm_case timeline advance_time daily_check

param(
    [Parameter(Mandatory=$true)]
    [string]$LambdaName
)

python scripts/package_lambda.py $LambdaName
