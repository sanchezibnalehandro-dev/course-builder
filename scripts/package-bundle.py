#!/usr/bin/env python3
"""Create course/build/bundle.zip without requiring a system zip binary."""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path


def should_include(relative: Path) -> bool:
    parts = relative.parts
    if not parts:
        return False
    if parts[0] in {"build", "_workspace"}:
        return False
    if relative.name == ".DS_Store":
        return False
    return not any(part.startswith(".") for part in parts)


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: package-bundle.py <course_root>")

    root = Path(sys.argv[1]).resolve()
    if not root.is_dir():
        raise SystemExit(f"ERROR: course root not found: {root}")

    output = root / "build" / "bundle.zip"
    output.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(root.rglob("*")):
            relative = path.relative_to(root)
            if path.is_file() and should_include(relative):
                archive.write(path, relative.as_posix())

    print(f"Created {output}")


if __name__ == "__main__":
    main()
