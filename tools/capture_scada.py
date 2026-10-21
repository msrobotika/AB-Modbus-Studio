# SPDX-License-Identifier: MIT
# Copyright (c) 2026 MS ROBOTIKA
"""Prueba de extremo a extremo y capturas REALES de AB-Modbus SCADA.

Ejecuta nuestro servidor en loopback, lee registros mediante el simulador
Modbus TCP real y captura el navegador Chromium. No usa imágenes generadas,
HTML falseado ni conexiones a equipos industriales externos.
"""
from pathlib import Path
import os
import re
import subprocess
import sys
import tempfile

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "docs" / "screenshots"


def run():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="abscada-captures-") as temp:
        proc = subprocess.Popen(
            [sys.executable, "-u", "-m", "ab_modbus", "--no-browser", "--data-dir", temp],
            cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1, env={**os.environ, "PYTHONUNBUFFERED": "1"},
        )
        try:
            assert proc.stdout
            banner = proc.stdout.readline().strip()
            url = proc.stdout.readline().strip()
            if not re.fullmatch(r"http://127\.0\.0\.1:\d+/#token=[A-Za-z0-9_\-]+", url):
                raise RuntimeError("No llegó URL de la aplicación: " + repr((banner, url)))
            target = url.replace("/#token=", "/scada.html#token=")
            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=1)
                errors = []
                page.on("pageerror", lambda e: errors.append(str(e)))
                page.goto(target, wait_until="domcontentloaded", timeout=25_000)
                page.locator("#demo").click(timeout=15_000)
                page.wait_for_function(
                    "() => document.querySelector('#kpi-reads').textContent === '1' && "
                    "document.querySelectorAll('.sc-point').length === 8",
                    timeout=25_000,
                )
                displayed = [n.inner_text() for n in page.locator(".sc-point strong").all()]
                expected = ["230", "1500", "42", "2026", "100", "0", "65535", "1234"]
                if displayed != expected:
                    raise AssertionError(f"Datos FC03 inesperados: {displayed}")
                page.locator("#high").fill("220")
                page.locator("#apply-alarm").click()
                page.wait_for_function(
                    "() => document.querySelector('#kpi-alarms').textContent === '1'",
                    timeout=12_000,
                )
                page.screenshot(path=str(OUTPUT / "scada-escritorio.png"),full_page=True,animations="disabled")
                page.locator("#tendencias").screenshot(path=str(OUTPUT / "scada-tendencias.png"),animations="disabled")
                page.set_viewport_size({"width": 390, "height": 844})
                page.wait_for_timeout(300)
                page.screenshot(path=str(OUTPUT / "scada-movil.png"),full_page=True,animations="disabled")
                if errors:
                    raise AssertionError("Errores JavaScript: " + "; ".join(errors))
                browser.close()
            for name in ("scada-escritorio.png", "scada-tendencias.png", "scada-movil.png"):
                path = OUTPUT / name
                if not path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"):
                    raise AssertionError("PNG inválido: " + name)
                print(f"Captura real: {path.relative_to(ROOT)} / {path.stat().st_size} bytes")
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=6)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=6)


if __name__ == "__main__":
    run()
