import os
import json
import sys
from glob import glob


def validate_i18n(base_lang="JP"):
    """
    Validate that all language files match the keys present in the base language.
    """
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    i18n_dir = os.path.join(root_dir, "resources", "i18n")

    print(f"Searching for i18n files in: {i18n_dir}")

    # Find base language file
    base_file = os.path.join(i18n_dir, base_lang, "text", f"{base_lang}.json")
    if not os.path.exists(base_file):
        print(f"ERROR: Base language file not found: {base_file}")
        return False

    try:
        with open(base_file, "r", encoding="utf-8") as f:
            base_data = json.load(f)
    except Exception as e:
        print(f"ERROR: Failed to load base language file: {e}")
        return False

    base_keys = set(get_all_keys(base_data))
    print(f"Base Language ({base_lang}) has {len(base_keys)} keys.")

    all_valid = True

    # Find all other language files
    # Structure: resources/i18n/{LANG}/text/{LANG}.json
    lang_dirs = glob(os.path.join(i18n_dir, "*"))

    for d in lang_dirs:
        if not os.path.isdir(d):
            continue

        lang_code = os.path.basename(d)
        if lang_code == base_lang:
            continue

        target_file = os.path.join(d, "text", f"{lang_code}.json")
        if not os.path.exists(target_file):
            print(f"WARNING: No text file found for {lang_code} at {target_file}")
            continue

        try:
            with open(target_file, "r", encoding="utf-8") as f:
                target_data = json.load(f)
        except Exception as e:
            print(f"ERROR: Failed to load {lang_code}: {e}")
            all_valid = False
            continue

        target_keys = set(get_all_keys(target_data))

        # Check for missing keys
        missing = base_keys - target_keys
        if missing:
            print(f"ERROR: {lang_code} is missing {len(missing)} keys:")
            for k in sorted(missing)[:5]:
                print(f"  - {k}")
            if len(missing) > 5:
                print("  ... and more")
            all_valid = False
        else:
            print(f"OK: {lang_code}")

    return all_valid


def get_all_keys(data, parent_key=""):
    """Recursively get all keys from a nested dictionary."""
    keys = []
    for k, v in data.items():
        full_key = f"{parent_key}.{k}" if parent_key else k
        if isinstance(v, dict):
            keys.extend(get_all_keys(v, full_key))
        else:
            keys.append(full_key)
    return keys


if __name__ == "__main__":
    if validate_i18n():
        print("\nSUCCESS: All I18n files are valid.")
        sys.exit(0)
    else:
        print("\nFAILURE: Missing keys detected.")
        sys.exit(1)
