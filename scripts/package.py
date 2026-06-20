import json
import os
import zipfile
import subprocess

ITEMS_TO_PACKAGE = [
    "properties.config",
    "requirements.txt",
    "CMakeLists.txt",
    "ui",
    "server",
    "scripts",
    "public",
    "private",
    "engine",
    "documentation"
]

# Files to exclude from the packaged zip (relative paths, normalized)
EXCLUDED_FILES = [
    os.path.normpath("scripts/package.py"),
]

REPO = "ecxogames/esdk"


def fetch_tags() -> bool:
    """Refresh tags from origin so recently created GitHub tags are visible."""
    result = subprocess.run(
        ["git", "fetch", "--tags", "--quiet", "origin"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print("[Warning] Could not refresh tags from 'origin'.")
        if result.stderr.strip():
            print(f"  {result.stderr.strip()}")
        print("  Continuing with the tags currently available locally.")
        return False
    return True


def tag_exists(tag: str) -> bool:
    result = subprocess.run(
        ["git", "show-ref", "--verify", "--quiet", f"refs/tags/{tag}"]
    )
    return result.returncode == 0


def resolve_tag(version: str) -> str | None:
    """Resolve either 0.0.1 or v0.0.1 input to an existing local tag."""
    bare_version = version[1:] if version.lower().startswith("v") else version
    for candidate in (f"v{bare_version}", bare_version):
        if tag_exists(candidate):
            return candidate
    return None


def get_tag_message(tag: str) -> str:
    """Returns the annotated tag message body, or falls back to commit message."""
    result = subprocess.run(
        ["git", "tag", "-l", "--format=%(contents)", tag],
        capture_output=True, text=True
    )
    msg = result.stdout.strip()
    if msg:
        return msg
    # Fall back to the commit message pointed to by the tag
    result = subprocess.run(
        ["git", "log", "-1", "--pretty=%B", tag],
        capture_output=True, text=True
    )
    return result.stdout.strip()


def create_zip(zip_filename: str) -> bool:
    try:
        with zipfile.ZipFile(zip_filename, "w", zipfile.ZIP_DEFLATED) as zipf:
            for item in ITEMS_TO_PACKAGE:
                if not os.path.exists(item):
                    print(f"  [Warning] Missing '{item}', skipping.")
                    continue

                if os.path.isfile(item):
                    print(f"  Adding file: {item}")
                    zipf.write(item)
                elif os.path.isdir(item):
                    print(f"  Adding directory: {item}/")
                    for root, dirs, files in os.walk(item):
                        if "__pycache__" in dirs:
                            dirs.remove("__pycache__")
                        for file in files:
                            file_path = os.path.join(root, file)
                            if os.path.normpath(file_path) in EXCLUDED_FILES:
                                print(f"    [Skip] {file_path}")
                                continue
                            zipf.write(file_path, file_path)
        return True
    except Exception as e:
        print(f"\n[Error] Failed to create zip: {e}")
        return False


def publish_github_release(tag: str, version: str, zip_filename: str, notes: str) -> bool:
    """Create a release, or update its metadata and replace its ZIP asset."""
    title = f"Ecxo Software Development Engine - Version {version}"
    try:
        existing_release = subprocess.run(
            ["gh", "release", "view", tag, "--json", "assets", "--repo", REPO],
            capture_output=True, text=True
        )

        if existing_release.returncode == 0:
            print(f"[Info] Release '{tag}' already exists; updating it.")
            try:
                existing_assets = {
                    asset["name"] for asset in json.loads(existing_release.stdout)["assets"]
                }
            except (json.JSONDecodeError, KeyError, TypeError):
                existing_assets = set()

            edit_result = subprocess.run(
                [
                    "gh", "release", "edit", tag,
                    "--title", title,
                    "--notes", notes,
                    "--repo", REPO,
                ],
                capture_output=True, text=True
            )
            if edit_result.returncode != 0:
                print(f"[Error] Could not update the GitHub release:\n{edit_result.stderr.strip()}")
                return False

            upload_result = subprocess.run(
                [
                    "gh", "release", "upload", tag, zip_filename,
                    "--clobber",
                    "--repo", REPO,
                ],
                capture_output=True, text=True
            )
            if upload_result.returncode != 0:
                print(f"[Error] Could not replace the release archive:\n{upload_result.stderr.strip()}")
                return False

            legacy_zip = f"esd-engine-{version}.zip"
            if legacy_zip in existing_assets and legacy_zip != zip_filename:
                delete_result = subprocess.run(
                    [
                        "gh", "release", "delete-asset", tag, legacy_zip,
                        "--yes",
                        "--repo", REPO,
                    ],
                    capture_output=True, text=True
                )
                if delete_result.returncode != 0:
                    print(f"[Error] Could not remove legacy archive '{legacy_zip}':\n{delete_result.stderr.strip()}")
                    return False

            print(f"[Success] GitHub release '{tag}' updated and archive replaced.")
            return True

        result = subprocess.run(
            [
                "gh", "release", "create", tag, zip_filename,
                "--title", title,
                "--notes", notes,
                "--repo", REPO,
            ],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            print(f"[Success] GitHub release created: {result.stdout.strip()}")
            return True
        else:
            print(f"[Error] GitHub CLI failed:\n{result.stderr.strip()}")
            return False
    except FileNotFoundError:
        print("[Error] 'gh' CLI not found. Install GitHub CLI and authenticate first.")
        print("  https://cli.github.com/")
        return False


def choose_package_mode() -> str:
    print("\nSelect package mode:")
    print("  1. Official release (requires a git tag and publishes to GitHub Releases)")
    print("  2. Test archive    (builds locally without a git tag or GitHub upload)")

    while True:
        choice = input("\nChoose mode (1/2): ").strip()
        if choice == "1":
            return "official"
        if choice == "2":
            return "test"
        print("Invalid selection. Please enter 1 or 2.")


def build_test_archive() -> bool:
    zip_filename = "esd-engine-test.zip"
    if os.path.exists(zip_filename):
        print(f"[Warning] '{zip_filename}' already exists and will be overwritten.")

    print(f"\nPackaging local test archive into '{zip_filename}'...")
    if not create_zip(zip_filename):
        return False

    print(f"[Success] Test archive created: {os.path.abspath(zip_filename)}")
    print("[Info] No git tag was checked and nothing was uploaded to GitHub Releases.")
    return True


def main():
    print("=" * 50)
    print("  ESD Suite Framework Packager")
    print("=" * 50)

    if not os.path.exists("engine") or not os.path.exists("scripts"):
        print("[Error] Please run this script from the project root directory.")
        return

    mode = choose_package_mode()
    if mode == "test":
        build_test_archive()
        return

    version = input("\nEnter the version number for this release (e.g., 0.0.15): ").strip()
    if not version:
        print("[Error] Version cannot be empty.")
        return

    # Tags created on GitHub after this repository was cloned may not exist locally yet.
    fetch_tags()
    tag = resolve_tag(version)
    if tag is None:
        bare_version = version[1:] if version.lower().startswith("v") else version
        print(f"[Error] Git tag 'v{bare_version}' or '{bare_version}' does not exist.")
        print(f"  Create and push it first:")
        print(f"    git tag -a v{bare_version} -m \"Your release notes here\"")
        print(f"    git push origin v{bare_version}")
        return

    tag_message = get_tag_message(tag)
    if not tag_message:
        print(f"[Error] Could not read a message from tag '{tag}'. Aborting.")
        return

    zip_filename = f"esdk-{version}.zip"
    if os.path.exists(zip_filename):
        print(f"[Warning] '{zip_filename}' already exists and will be overwritten.")

    # Step 1 – Build zip
    print(f"\nPackaging into '{zip_filename}'...")
    if not create_zip(zip_filename):
        return
    print(f"[Success] '{zip_filename}' created.")

    # Step 2 – GitHub release
    print(f"\nCreating GitHub release for tag '{tag}'...")
    publish_github_release(tag, version, zip_filename, tag_message)


if __name__ == "__main__":
    main()
