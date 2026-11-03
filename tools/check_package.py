"""Check the install ZIP against its allowed source and public documentation."""
from pathlib import Path, PurePosixPath
import json
import re
import zipfile


def main():
    root = Path(__file__).resolve().parents[1]
    component = root / "custom_components/hive_ev"
    version = json.loads((component / "manifest.json").read_text(encoding="utf-8"))["version"]
    package = root / "dist" / f"hive-ev-{version}.zip"
    component_names = {
        "__init__.py", "api.py", "auth.py", "binary_sensor.py", "button.py",
        "config_flow.py", "const.py", "controls.py", "coordinator.py",
        "diagnostics.py", "diagnostic_shapes.py", "energy_helper.py", "manifest.json", "sensor.py",
        "strings.json", "translations/en.json", "brand/icon.png",
    }
    expected = {"custom_components/hive_ev/" + name for name in component_names}
    expected.update({"README.md", "CHANGELOG.md", "CONTRIBUTING.md", "PUBLISHING.md",
                     "LICENSE", "THIRD_PARTY_NOTICES.md", "licenses/Pyhive-MIT.txt",
                     "examples/energy_cost.yaml"})
    expected.update(path.relative_to(root).as_posix() for path in (root / "docs").glob("*.md"))
    with zipfile.ZipFile(package) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or set(names) != expected or archive.testzip() is not None:
            raise SystemExit("Installation archive file scope or integrity failed")
        for name in names:
            parts = PurePosixPath(name).parts
            if name.startswith("/") or ".." in parts:
                raise SystemExit("Unsafe installation archive path")
            data = archive.read(name)
            if data != (root / name).read_bytes():
                raise SystemExit("Installation archive differs from source: " + name)
            if name == "custom_components/hive_ev/brand/icon.png":
                if not data.startswith(b"\x89PNG\r\n\x1a\n"):
                    raise SystemExit("Integration brand icon is not a PNG")
                continue
            text = data.decode("utf-8")
            if re.search(r"-----BEGIN [A-Z ]*PRIVATE KEY-----", text):
                raise SystemExit("Private-key marker in package: " + name)
            if re.search(r"eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.", text):
                raise SystemExit("JWT-shaped value in package: " + name)
    print(f"Verified {len(names)} allowed installation files; source, privacy markers and ZIP integrity match.")


if __name__ == "__main__":
    main()
