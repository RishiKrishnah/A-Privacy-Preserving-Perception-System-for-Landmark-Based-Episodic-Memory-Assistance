from pathlib import Path

# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent
OUTPUT_FILE = PROJECT_ROOT / "project_context.txt"

# Directories that should NOT be included
EXCLUDED_DIRS = {
    ".venv",
    ".git",
    ".pytest_cache",
    "__pycache__",
    "node_modules",
    ".mypy_cache",
    ".ruff_cache",
}

# Files that should NOT be included
EXCLUDED_FILES = {
    OUTPUT_FILE.name,
    "project.zip",
}

# Text/code/config files worth including
INCLUDED_EXTENSIONS = {
    ".py",
    ".yaml",
    ".yml",
    ".json",
    ".toml",
    ".ini",
    ".cfg",
    ".txt",
    ".md",
    ".rst",
    ".html",
    ".css",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".xml",
    ".sql",
    ".env",
    ".gitignore",
    ".dockerfile",
}

# Files with these extensions are explicitly ignored
BINARY_EXTENSIONS = {
    ".pt",
    ".pth",
    ".onnx",
    ".task",
    ".db",
    ".sqlite",
    ".sqlite3",
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
    ".mp4",
    ".avi",
    ".mov",
    ".wav",
    ".mp3",
    ".zip",
    ".7z",
    ".rar",
    ".pdf",
    ".exe",
    ".dll",
    ".so",
}


# ============================================================
# HELPERS
# ============================================================


def should_exclude_directory(path: Path) -> bool:
    return path.name in EXCLUDED_DIRS


def should_include_file(path: Path) -> bool:
    if path.name in EXCLUDED_FILES:
        return False

    if path.suffix.lower() in BINARY_EXTENSIONS:
        return False

    # Files such as .gitignore have no useful suffix
    if path.name in {".gitignore", ".dockerignore"}:
        return True

    return path.suffix.lower() in INCLUDED_EXTENSIONS


def safe_read_text(path: Path) -> str:
    """
    Read a text file safely.
    Tries UTF-8 first, then falls back to replacement characters.
    """
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        return f"[ERROR READING FILE: {exc}]"


def get_relative_path(path: Path) -> str:
    return str(path.relative_to(PROJECT_ROOT)).replace("\\", "/")


# ============================================================
# DIRECTORY TREE
# ============================================================


def build_tree():
    lines = []

    lines.append("PROJECT DIRECTORY STRUCTURE")
    lines.append("=" * 80)
    lines.append("")

    def walk(directory: Path, prefix=""):
        try:
            entries = sorted(
                directory.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())
            )
        except PermissionError:
            lines.append(prefix + "[Permission Denied]")
            return

        visible_entries = []

        for entry in entries:
            if entry.is_dir():
                if should_exclude_directory(entry):
                    continue
                visible_entries.append(entry)

            elif entry.is_file():
                if should_include_file(entry):
                    visible_entries.append(entry)

        for index, entry in enumerate(visible_entries):
            is_last = index == len(visible_entries) - 1
            branch = "└── " if is_last else "├── "

            if entry.is_dir():
                lines.append(prefix + branch + entry.name + "/")

                extension = "    " if is_last else "│   "
                walk(entry, prefix + extension)

            else:
                lines.append(prefix + branch + entry.name)

    lines.append(PROJECT_ROOT.name + "/")
    walk(PROJECT_ROOT)

    lines.append("")
    lines.append("=" * 80)
    lines.append("")

    return lines


# ============================================================
# FILE CONTENTS
# ============================================================


def collect_files():
    files = []

    for path in PROJECT_ROOT.rglob("*"):
        if not path.is_file():
            continue

        # Check whether any parent directory is excluded
        relative_parts = path.relative_to(PROJECT_ROOT).parts

        if any(part in EXCLUDED_DIRS for part in relative_parts):
            continue

        if should_include_file(path):
            files.append(path)

    return sorted(files, key=lambda p: get_relative_path(p).lower())


def build_file_contents(files):
    output = []

    output.append("PROJECT FILE CONTENTS")
    output.append("=" * 80)
    output.append("")

    for path in files:
        relative_path = get_relative_path(path)

        output.append("")
        output.append("#" * 80)
        output.append(f"# FILE: {relative_path}")
        output.append("#" * 80)
        output.append("")

        content = safe_read_text(path)

        output.append(content.rstrip())
        output.append("")
        output.append("")

    return output


# ============================================================
# MAIN
# ============================================================


def main():

    print("=" * 60)
    print("PROJECT EXPORT TOOL")
    print("=" * 60)

    print(f"\nProject root:")
    print(PROJECT_ROOT)

    print("\nBuilding directory structure...")

    tree = build_tree()

    print("Collecting source/config/documentation files...")

    files = collect_files()

    print(f"Found {len(files)} text/code/config files.")

    print("Extracting file contents...")

    contents = build_file_contents(files)

    final_output = []

    # Header for ChatGPT
    final_output.append(
        """
PROJECT CONTEXT EXPORT
======================

This file contains the directory structure and text/code/configuration
contents of a software project.

IMPORTANT:
- The directory structure is listed first.
- Each included file is identified using:
    # FILE: relative/path/to/file
- Binary files, model weights, databases, virtual environments,
  caches, and archives are intentionally excluded.
- Treat the contents below as the source of truth for understanding
  the current implementation.
- Do not assume that excluded binary/database files contain information
  that is not represented in the extracted source/configuration.

The purpose of this export is to allow an AI assistant to inspect
the complete source-level project without requiring the original ZIP.
""".strip()
    )

    final_output.append("")
    final_output.append("")
    final_output.extend(tree)
    final_output.extend(contents)

    OUTPUT_FILE.write_text("\n".join(final_output), encoding="utf-8")

    print("\n" + "=" * 60)
    print("DONE")
    print("=" * 60)

    print(f"\nOutput file:")
    print(OUTPUT_FILE)

    print(f"\nFiles included: {len(files)}")

    print("\nExcluded:")
    print("  - .venv/")
    print("  - .git/")
    print("  - __pycache__/")
    print("  - .pytest_cache/")
    print("  - model weights")
    print("  - SQLite/database files")
    print("  - images/videos")
    print("  - ZIP/archive files")

    print("\nYou can now upload:")
    print("  project_context.txt")


if __name__ == "__main__":
    main()
