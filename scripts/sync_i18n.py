import os
import json
import codecs

# Base paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
I18N_DIR = os.path.join(PROJECT_ROOT, "resources", "i18n")

# Translations map for new keys (English)
# We can use this to populate non-JP languages with English defaults instead of JP
ENGLISH_DEFAULTS = {
    "loading": {
        "init": "Initializing system...",
        "deps": "Checking dependencies...",
        "ai": "Starting AI Engine (this may take a moment)...",
        "core": "Loading core components...",
        "done": "Ready!"
    },
    "error_hints": {
        "avx": "This CPU may not support AVX instructions. Please try a newer PC.",
        "dll": "Missing system components (DLL). Please install MSVC Redistributable.",
        "model": "AI model file not found. Check resources/model folder.",
        "generic": "An unknown error occurred. Check logs or contact developer."
    }
}


def load_json(path):
    with codecs.open(path, 'r', 'utf-8') as f:
        return json.load(f)


def save_json(path, data):
    with codecs.open(path, 'w', 'utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def recursive_update(target, source, defaults=None):
    updated = False
    for key, val in source.items():
        if key not in target:
            # New key missing in target
            if defaults and key in defaults:
                # Use default translation if available
                target[key] = defaults[key]
            else:
                # Fallback to source value (e.g. JP)
                target[key] = val
            updated = True
        elif isinstance(val, dict):
            if not isinstance(target[key], dict):
                # Structure mismatch, overwrite
                target[key] = val
                updated = True
            else:
                # Recurse
                default_sub = defaults[key] if (defaults and key in defaults) else None
                if recursive_update(target[key], val, default_sub):
                    updated = True
    return updated


def main():
    jp_path = os.path.join(I18N_DIR, "JP", "text", "JP.json")
    if not os.path.exists(jp_path):
        print("JP.json not found!")
        return

    jp_data = load_json(jp_path)

    # Iterate all languages
    for lang in os.listdir(I18N_DIR):
        if lang == "JP":
            continue

        lang_dir = os.path.join(I18N_DIR, lang, "text")
        json_path = os.path.join(lang_dir, f"{lang}.json")

        if not os.path.exists(json_path):
            print(f"Skipping {lang}, JSON not found.")
            continue

        print(f"Syncing {lang}...")
        try:
            target_data = load_json(json_path)
            # Use English defaults for everyone else
            if recursive_update(target_data, jp_data, ENGLISH_DEFAULTS):
                save_json(json_path, target_data)
                print(f"  Updated {lang}.json")
            else:
                print(f"  {lang}.json is up to date.")
        except Exception as e:
            print(f"  Failed to update {lang}: {e}")


if __name__ == "__main__":
    main()
