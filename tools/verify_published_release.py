#!/usr/bin/env python3
"""Verify *published* release asset checksums, portability and SCADA UI.
Only local simulator traffic (127.0.0.1). No PLC, LAN, writes or credentials.
The public v0.1.0 release is audited as immutable, not silently rebuilt.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import zipfile

SHA = re.compile(r"^([a-fA-F0-9]{64})\s+\*?(\S+)$")
URL = re.compile(r"^http://127\.0\.0\.1:(\d{1,5})/#token=([a-zA-Z0-9_-]+)$")
TAG = "v0.1.0"


def check_checksums(folder: Path) -> dict[str, str]:
    manifest = folder / "SHA256SUMS.txt"
    if not manifest.is_file():
        raise RuntimeError("Release BLOCKED: falta el manifiesto oficial SHA256SUMS.txt")
    lines = manifest.read_text(encoding="utf-8").splitlines()
    hashes = {}
    for line in lines:
        if not line.strip():
            continue
        parsed = SHA.fullmatch(line.strip())
        if parsed is None:
            raise RuntimeError("Manifiesto SHA256 inválido")
        digest, filename = parsed.groups()
        if Path(filename).name != filename:
            raise RuntimeError("Nombre inseguro en manifiesto")
        zip_path = folder / filename
        if not zip_path.is_file():
            raise RuntimeError("Falta artefacto de Release: " + filename)
        with zip_path.open("rb") as handle:
            actual = hashlib.file_digest(handle, "sha256").hexdigest()
        if actual.lower() != digest.lower():
            raise RuntimeError("HASH MISMATCH: " + filename)
        hashes[filename] = actual
    expected = {"AB-Modbus-Studio-Windows.zip", "AB-Modbus-Studio-Linux.zip"}
    if set(hashes) != expected:
        raise RuntimeError("Lista de activos inesperada: " + repr(sorted(hashes)))
    return hashes


def unpack_safe(archive: Path, target: Path) -> None:
    with zipfile.ZipFile(archive) as z:
        members = z.infolist()
        if not members:
            raise RuntimeError("ZIP vacío")
        for member in members:
            path = Path(member.filename)
            if path.is_absolute() or ".." in path.parts:
                raise RuntimeError("ZIP con ruta no segura: " + member.filename)
            if (member.external_attr >> 16) & 0o170000 == 0o120000:
                raise RuntimeError("Enlace simbólico en ZIP no verificado")
        z.extractall(target)


def run_binary(binary: Path, *args: str, timeout: int = 45) -> str:
    result = subprocess.run([str(binary), *args], text=True, capture_output=True,
                            timeout=timeout, check=False)
    if result.returncode:
        raise RuntimeError(f"Portable salió con código {result.returncode}: " +
                           result.stderr[:500])
    return result.stdout.strip()


def smoke_hmi(binary: Path, directory: Path) -> dict:
    output_file = directory / "service-output.txt"
    data_dir = directory / "profiles"
    data_dir.mkdir()
    with output_file.open("w+", encoding="utf-8") as output:
        process = subprocess.Popen([str(binary), "--no-browser", "--port", "0",
                                    "--data-dir", str(data_dir)],
                                   stdout=output, stderr=subprocess.STDOUT,
                                   cwd=directory)
        try:
            url = None
            limit = time.monotonic() + 45
            while time.monotonic() < limit:
                if process.poll() is not None:
                    raise RuntimeError("La HMI del portable terminó antes de arrancar")
                output.seek(0)
                lines = output.read().splitlines()
                for line in lines:
                    found = URL.fullmatch(line.strip())
                    if found:
                        url = found
                        break
                if url:
                    break
                time.sleep(0.2)
            if url is None:
                raise RuntimeError("No llegó URL de HMI local tras iniciar el portable")
            port, session = url.groups()
            origin = "http://127.0.0.1:" + port
            def request(path: str, headers=None):
                with urlopen(Request(origin + path, headers=headers or {}), timeout=6) as response:
                    return response.status, response.read().decode("utf-8", errors="replace")
            status, home = request("/")
            if status != 200 or "AB-Modbus" not in home:
                raise RuntimeError("La interfaz principal no funciona")
            state_status, state = request("/api/state", {"Authorization":"Bearer " + session})
            if state_status != 200 or not json.loads(state):
                raise RuntimeError("API local de estado no funciona")
            try:
                request("/api/state")
                raise RuntimeError("API privada accesible sin token")
            except HTTPError as err:
                if err.code not in (401,403):
                    raise
            scada = {}
            for path in ("/scada.html", "/scada.js", "/scada.css"):
                try:
                    st, data = request(path)
                    scada[path] = st == 200 and len(data) > 50 and (
                        "scada" in data.lower() if path.endswith(".html") else True)
                except HTTPError as err:
                    scada[path] = False if err.code == 404 else "HTTP_" + str(err.code)
            if not all(value is True for value in scada.values()):
                raise RuntimeError("RELEASE_GAP: el portable publicado no contiene SCADA completo: " +
                                   json.dumps(scada, ensure_ascii=False))
            return {"hmi":"PASS", "loopback_only":True, "authenticated_state":"PASS",
                    "scada_ui":scada}
        finally:
            process.terminate()
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=8)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--assets-dir", required=True, type=Path)
    parser.add_argument("--platform", required=True, choices=("Linux","Windows"))
    args = parser.parse_args()
    hashes = check_checksums(args.assets_dir)
    asset_name = "AB-Modbus-Studio-" + args.platform + ".zip"
    with tempfile.TemporaryDirectory(prefix="abmodbus-release-qa-") as tmp:
        root = Path(tmp)
        unpack_safe(args.assets_dir / asset_name, root)
        binary = root / ("AB-Modbus-Studio.exe" if args.platform == "Windows"
                         else "AB-Modbus-Studio")
        if not binary.is_file():
            raise RuntimeError("Falta el ejecutable esperado en el ZIP de " + args.platform)
        if args.platform=="Linux":
            binary.chmod(binary.stat().st_mode | 0o111)
        if not (root / "LICENSE").is_file():
            raise RuntimeError("Falta LICENSE en la distribución")
        result = json.loads(run_binary(binary, "--self-test").splitlines()[-1])
        if result != {"ok":True,"version":"0.1.0","functions":[1,2,3,4]}:
            raise RuntimeError("Autoprueba FC01-04 / versión inesperada: "+repr(result))
        hmi = smoke_hmi(binary, root)
    print(json.dumps({"release":TAG,"platform":args.platform,"sha256":hashes[asset_name],
      "self_test":"PASS",**hmi}, ensure_ascii=False))
    print("PASS: Release oficial; SHA256, ejecución, FC01-04, HMI autenticada, SCADA")


if __name__=="__main__":
    main()
