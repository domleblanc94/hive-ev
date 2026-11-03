"""Build a clean installation ZIP without account data, captured diagnostics, or private tools."""
from pathlib import Path
import json
import zipfile


def main():
    root = Path(__file__).resolve().parents[1]
    component = root / "custom_components" / "hive_ev"
    manifest = json.loads((component / "manifest.json").read_text(encoding="utf-8"))
    required = {
        "__init__.py", "api.py", "auth.py", "config_flow.py", "const.py", "coordinator.py",
        "manifest.json", "sensor.py", "binary_sensor.py", "button.py", "controls.py",
        "diagnostics.py", "diagnostic_shapes.py", "strings.json",
        "translations/en.json",
    }
    missing = sorted(name for name in required if not (component / name).is_file())
    if missing:
        raise SystemExit("Missing integration files: " + ", ".join(missing))
    files = [component / name for name in sorted(required)]
    docs = [root / name for name in ("README.md", "CONTRIBUTING.md", "PUBLISHING.md", "CHANGELOG.md")]
    docs.extend(sorted((root / "docs").glob("*.md")))
    if any(not path.is_file() for path in docs):
        raise SystemExit("Installation instructions are missing")
    notices = [root / name for name in ("LICENSE", "THIRD_PARTY_NOTICES.md", "licenses/Pyhive-MIT.txt")]
    if any(not path.is_file() for path in notices):
        raise SystemExit("License notices are missing")
    output = root / "dist" / f"hive-ev-{manifest['version']}.zip"
    output.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, path.relative_to(root).as_posix())
        for path in docs:
            archive.write(path, path.relative_to(root).as_posix())
        for path in notices:
            archive.write(path, path.relative_to(root).as_posix())
    with zipfile.ZipFile(output) as archive:
        if archive.testzip() is not None:
            raise SystemExit("Archive integrity check failed")
        print(f"Packaged {len(files)} integration files and installation instructions.")
        print(output)


if __name__ == "__main__":
    main()
