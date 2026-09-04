import os
import sys
import shutil
import zipfile
import subprocess

def package_lambda(lambda_name):
    workspace = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    build_dir = os.path.join(workspace, "build", lambda_name)
    zip_path = os.path.join(workspace, "build", f"{lambda_name}.zip")
    
    print(f"--- Packaging Lambda: {lambda_name} ---")
    
    # Clean old build dir
    if os.path.exists(build_dir):
        shutil.rmtree(build_dir, ignore_errors=True)
    os.makedirs(build_dir, exist_ok=True)
    
    # If create_case, install external requirements
    if lambda_name == "create_case":
        print("Installing dependencies for create_case...")
        req_file = os.path.join(workspace, "requirements.txt")
        cmd = [
            sys.executable, "-m", "pip", "install", "-r", req_file,
            "-t", build_dir,
            "--platform", "manylinux2014_x86_64",
            "--implementation", "cp",
            "--python-version", "3.12",
            "--only-binary=:all:",
            "--quiet"
        ]
        subprocess.check_call(cmd)
    else:
        print(f"Lambda {lambda_name} uses AWS built-in boto3 runtime (clean lightweight package)")
        
    # Copy common
    common_src = os.path.join(workspace, "common")
    common_dest = os.path.join(build_dir, "common")
    shutil.copytree(common_src, common_dest, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    
    # Copy handler
    handler_src = os.path.join(workspace, "lambdas", lambda_name, "handler.py")
    handler_dest = os.path.join(build_dir, "handler.py")
    shutil.copy2(handler_src, handler_dest)
    
    # Delete old zip if exists
    if os.path.exists(zip_path):
        os.remove(zip_path)
        
    # Zip using standard python zipfile (rock-solid, no Windows PowerShell file locks)
    print("Creating zip archive...")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(build_dir):
            for file in files:
                if file.endswith(".pyc") or "__pycache__" in root:
                    continue
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, build_dir)
                zf.write(file_path, arcname)
                
    size_kb = os.path.getsize(zip_path) / 1024
    print(f"SUCCESS: Built {zip_path} ({size_kb:.2f} KB)")
    print("Handler: handler.lambda_handler")

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "advance_time"
    package_lambda(target)
