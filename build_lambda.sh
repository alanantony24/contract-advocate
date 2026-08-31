#!/bin/bash
# Usage: ./build_lambda.sh <lambda_name>
# Example: ./build_lambda.sh create_case
# Produces build/<lambda_name>.zip - upload this directly to your Lambda function.

set -e
LAMBDA_NAME=$1
if [ -z "$LAMBDA_NAME" ]; then
  echo "Usage: ./build_lambda.sh <lambda_name>"
  echo "Available: create_case get_case confirm_case timeline advance_time daily_check"
  exit 1
fi

BUILD_DIR="build/$LAMBDA_NAME"
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

echo "Installing dependencies..."
pip install -r requirements.txt -t "$BUILD_DIR" --quiet

echo "Copying shared code and handler..."
cp -r common "$BUILD_DIR/"
cp "lambdas/$LAMBDA_NAME/handler.py" "$BUILD_DIR/"

echo "Zipping..."
cd "$BUILD_DIR"
zip -r "../${LAMBDA_NAME}.zip" . -x "*.pyc" > /dev/null
cd ../..

echo "Built build/${LAMBDA_NAME}.zip"
echo "Upload this file to your Lambda function (or drag-drop it in the console)."
echo "In the Lambda console, set the handler to: handler.lambda_handler"
