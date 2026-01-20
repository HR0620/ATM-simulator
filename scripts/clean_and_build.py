import os
import shutil
import subprocess
import sys
from pathlib import Path


def print_step(step):
    print(f"\n{'='*40}")
    print(f"STEP: {step}")
    print(f"{'='*40}")


def main():
    print_step("Initializing Build Process")

    # Check if pyinstaller is installed
    try:
        import PyInstaller
        print("✓ PyInstaller is installed")
    except ImportError:
        print("Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    # Define paths using pathlib for robustness
    SCRIPT_DIR = Path(__file__).parent.resolve()
    PROJECT_ROOT = SCRIPT_DIR.parent
    SRC_DIR = PROJECT_ROOT / "src"
    RESOURCES_DIR = PROJECT_ROOT / "resources"
    DIST_DIR = PROJECT_ROOT / "dist"
    BUILD_DIR = PROJECT_ROOT / "build"
    EXE_NAME = "ATM_Simulator"
    MAIN_SCRIPT = SRC_DIR / "main.py"
    ICON_PATH = RESOURCES_DIR / "icon.ico"

    # 0. Check Icon
    print_step("Checking Icon")
    if not ICON_PATH.exists():
        print(f"⚠ Warning: Icon not found at {ICON_PATH}. Using default PyInstaller icon.")
    else:
        print(f"✓ Icon found at {ICON_PATH}")

    # 0.1 Ensure Haar Cascade XML is in resources
    print_step("Ensuring Haar Cascade XML")
    cascade_xml = "haarcascade_frontalface_default.xml"
    target_xml_path = RESOURCES_DIR / "config" / cascade_xml
    if not target_xml_path.exists():
        import cv2
        src_xml_path = Path(cv2.data.haarcascades) / cascade_xml
        if src_xml_path.exists():
            if not target_xml_path.parent.exists():
                target_xml_path.parent.mkdir(parents=True)
            shutil.copy(src_xml_path, target_xml_path)
            print(f"✓ Copied {cascade_xml} to resources/config/")
        else:
            print(f"⚠ Warning: Could not find {cascade_xml} in cv2 data path")
    else:
        print(f"✓ {cascade_xml} already in resources/config/")

    # 1. Clean previous builds
    print_step("Cleaning previous builds")
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
        print(f"Removed {DIST_DIR}")
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
        print(f"Removed {BUILD_DIR}")

    spec_file = PROJECT_ROOT / f"{EXE_NAME}.spec"
    if spec_file.exists():
        os.remove(spec_file)
        print(f"Removed {spec_file}")

    # 2. Run PyInstaller
    print_step("Running PyInstaller")
    print("Building EXE... This may take a few minutes.")

    pyinstaller_cmd = [
        "pyinstaller",
        str(MAIN_SCRIPT),
        "--noconsole",          # GUI app, no terminal
        "--onedir",             # Folder based output (faster startup)
        "--name", EXE_NAME,
        "--clean",
        "--icon", str(ICON_PATH),
        "--distpath", str(DIST_DIR),
        "--workpath", str(BUILD_DIR),
        "--specpath", str(PROJECT_ROOT),

        # Hidden imports often needed for these libraries
        "--hidden-import", "tensorflow",
        "--hidden-import", "PIL",
        "--hidden-import", "cv2",
        "--hidden-import", "yaml",
        "--hidden-import", "src.paths"  # Ensure our path module is included
    ]

    try:
        subprocess.check_call(pyinstaller_cmd)
        print("✓ PyInstaller build completed successfully")
    except subprocess.CalledProcessError as e:
        print(f"❌ PyInstaller failed with error code {e.returncode}")
        sys.exit(1)

    # 3. Copy External Resources
    print_step("Copying External Resources")

    target_app_dir = DIST_DIR / EXE_NAME
    target_resources = target_app_dir / "resources"

    # Create the resources directory in the dist folder
    if not target_resources.exists():
        os.makedirs(target_resources)

    # Copy subfolders (assets, config, model)
    subfolders_to_copy = ["assets", "config", "model"]

    for folder_name in subfolders_to_copy:
        src = RESOURCES_DIR / folder_name
        dst = target_resources / folder_name

        if src.exists():
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
            print(f"✓ Copied resources/{folder_name}/")
        else:
            print(f"⚠ Warning: Resource folder {folder_name} not found at {src}")

    # Copy README.md to root of dist app
    readme_src = PROJECT_ROOT / "README.md"
    if readme_src.exists():
        shutil.copy(readme_src, target_app_dir / "README.md")
        print("✓ Copied README.md")

    print_step("Build Complete")
    print(f"Your application is ready at:\n{target_app_dir}")
    print("\n[Folder Structure]")
    print(f"{EXE_NAME}/")
    print(f"  ├── {EXE_NAME}.exe")
    print(f"  ├── resources/")
    print(f"  │     ├── assets/")
    print(f"  │     ├── config/")
    print(f"  │     └── model/")
    print(f"  └── README.md")

    # Open the folder
    os.startfile(target_app_dir)


if __name__ == "__main__":
    main()
