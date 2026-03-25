import os
import zipfile

ITEMS_TO_PACKAGE = [
    "properties.config",
    "CMakeLists.txt",
    "ui",
    "server",
    "scripts",
    "public",
    "private",
    "engine",
    "documentation"
]

def main():
    print("=" * 50)
    print("  ESD Suite Framework Packager")
    print("=" * 50)

    # Ensure we are running from the project root
    if not os.path.exists("engine") or not os.path.exists("scripts"):
        print("[Error] Please run this script from the project root directory (e.g., 'python scripts/package.py').")
        return

    version = input("Enter the version number for this release (e.g., 1.0.0): ").strip()
    if not version:
        print("[Error] Version cannot be empty.")
        return

    zip_filename = f"esd-engine-{version}.zip"

    if os.path.exists(zip_filename):
        print(f"[Warning] {zip_filename} already exists. It will be overwritten.")

    print(f"\nPackaging into {zip_filename}...")

    try:
        # Create a zip file
        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for item in ITEMS_TO_PACKAGE:
                if not os.path.exists(item):
                    print(f"  [Warning] Missing {item}, skipping.")
                    continue

                if os.path.isfile(item):
                    print(f"  Adding file: {item}")
                    # Write the file to the zip file using its relative path
                    zipf.write(item)
                elif os.path.isdir(item):
                    print(f"  Adding directory: {item}/")
                    # Walk the directory
                    for root, dirs, files in os.walk(item):
                        # Exclude compiled python cache directories
                        if '__pycache__' in dirs:
                            dirs.remove('__pycache__')
                        
                        for file in files:
                            file_path = os.path.join(root, file)
                            # Write each file in the directory to the zip archive
                            zipf.write(file_path, file_path)

        print(f"\n[Success] Framework packaged successfully into {zip_filename}!")
        print(f"You can now attach this zip file to your GitHub Release.")

    except Exception as e:
        print(f"\n[Error] Failed to package framework: {e}")

if __name__ == "__main__":
    main()
