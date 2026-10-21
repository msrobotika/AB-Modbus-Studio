# SPDX-License-Identifier: MIT
"""Construir en el SO de destino. No admite compilación cruzada."""
import importlib.metadata
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    subprocess.run([sys.executable, "-m", "unittest", "discover", "-v"], cwd=ROOT, check=True)
    subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onefile",
                    "--name", "AB-Modbus-Studio", "--add-data", "ab_modbus/web:ab_modbus/web",
                    "--collect-data", "ab_modbus", "launch.py"], cwd=ROOT, check=True)
    suffix = ".exe" if sys.platform == "win32" else ""
    binary = ROOT / "dist" / ("AB-Modbus-Studio" + suffix)
    subprocess.run([str(binary), "--self-test"], check=True)
    notice_dir = ROOT / "dist" / "licenses"
    notice_dir.mkdir(exist_ok=True)
    # La licencia de Python está instalada junto al intérprete de construcción.
    python_license = Path(sys.base_prefix) / "LICENSE.txt"
    if not python_license.exists():
        import sysconfig
        candidates = [Path(sysconfig.get_path("stdlib")) / "LICENSE.txt",
                      Path("/usr/share/doc/python3/copyright")]
        python_license = next((p for p in candidates if p.exists()), python_license)
    if not python_license.exists():
        raise RuntimeError("Falta licencia del runtime Python; no se distribuye el binario sin ella")
    shutil.copyfile(python_license, notice_dir / "PYTHON-LICENSE.txt")
    distribution = importlib.metadata.distribution("pyinstaller")
    for name in distribution.files or []:
        if Path(str(name)).name.upper() == "COPYING.TXT":
            shutil.copyfile(distribution.locate_file(name), notice_dir / "PYINSTALLER-COPYING.txt")
            break
    else:
        raise RuntimeError("Falta licencia y excepción de PyInstaller")
    for filename in ("LICENSE", "NOTICE", "THIRD_PARTY_NOTICES.md", "DEPENDENCIES.md", "README.md", "ROADMAP.md", "SECURITY.md"):
        shutil.copyfile(ROOT / filename, ROOT / "dist" / filename)
    versions = {name: importlib.metadata.version(name) for name in
                ("pyinstaller", "pyinstaller-hooks-contrib", "altgraph", "packaging", "setuptools")}
    (ROOT / "dist" / "BUILD-INFO.json").write_text(json.dumps({
        "python": sys.version, "platform": platform.platform(), "tools": versions,
        "application": "0.1.0", "self_test": "passed"}, indent=2), encoding="utf-8")
    print(f"Portable disponible: {binary}")


if __name__ == "__main__":
    main()
