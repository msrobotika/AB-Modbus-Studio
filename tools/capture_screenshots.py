# SPDX-License-Identifier: MIT
# Copyright (c) 2026 MS ROBOTIKA
"""Capturas reales de AB-Modbus Studio con navegador y simulador locales.

No se usan mocks HTML ni imágenes generadas: se arranca la aplicación,
se realizan intercambios Modbus TCP reales contra su simulador y se captura
el DOM renderizado por Chromium. Se ejecuta en CI; Playwright es una
dependencia de desarrollo opcional, no del producto.
"""
from __future__ import annotations

import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from contextlib import suppress

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
SCREENSHOTS = ROOT / "docs" / "screenshots"


def capture() -> None:
    SCREENSHOTS.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="abmodbus-capturas-") as workdir:
        process = subprocess.Popen(
            [sys.executable, "-u", "-m", "ab_modbus", "--no-browser",
             "--port", "0", "--data-dir", workdir],
            cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1, env={**os.environ, "PYTHONUNBUFFERED": "1"},
        )
        try:
            assert process.stdout is not None
            banner = process.stdout.readline().strip()
            url = process.stdout.readline().strip()
            if not re.fullmatch(r"http://127\.0\.0\.1:\d+/#token=[A-Za-z0-9_\-]+", url):
                raise RuntimeError(f"La aplicación no proporcionó su URL local: {banner!r} / {url!r}")
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 1440, "height": 940}, device_scale_factor=1)
                js_errors: list[str] = []
                page.on("pageerror", lambda error: js_errors.append(str(error)))
                page.goto(url, wait_until="domcontentloaded", timeout=20_000)
                page.locator("#sim-toggle").wait_for(state="visible", timeout=12_000)
                # Comprobación real de lectura FC03, no datos falsos en el HTML.
                page.locator("#quick-demo").click(timeout=15_000)
                page.wait_for_function(
                    "() => document.querySelectorAll('#values tr').length === 8 "
                    "&& document.querySelector('#read-meta').textContent.includes('8 valores')",
                    timeout=20_000,
                )
                page.wait_for_function(
                    "() => document.querySelector('#primera-prueba').dataset.quickStage === '3' "
                    "&& !document.querySelector('#quick-results-link').hidden",
                    timeout=10_000,
                )
                actual = [int(cell.inner_text()) for cell in page.locator("#values tr td:nth-child(3)").all()]
                expected = [230, 1500, 42, 2026, 100, 0, 65535, 1234]
                if actual != expected:
                    raise AssertionError(f"FC03 devolvió {actual}, esperaba {expected}")
                page.wait_for_function(
                    "() => Number(document.querySelector('#frame-count').textContent) >= 4",
                    timeout=10_000,
                )
                if js_errors:
                    raise AssertionError("Errores JS: " + "; ".join(js_errors))
                page.screenshot(
                    path=str(SCREENSHOTS / "escritorio.png"),
                    full_page=True, animations="disabled",
                )
                page.locator("#monitor").screenshot(
                    path=str(SCREENSHOTS / "monitor-tramas.png"),
                    animations="disabled",
                )
                page.set_viewport_size({"width": 390, "height": 844})
                page.wait_for_timeout(350)
                width_ok = page.evaluate(
                    "document.documentElement.scrollWidth <= window.innerWidth + 2"
                )
                if not width_ok:
                    raise AssertionError("Interfaz con desplazamiento horizontal en 390 px")
                decimal = page.locator("#values tr td:nth-child(3)").first
                if decimal.inner_text() != "230":
                    raise AssertionError("El primer registro no muestra el valor FC03 correcto")
                box = decimal.bounding_box()
                if not box or box["x"] < 0 or box["x"] + box["width"] > 390:
                    raise AssertionError("El valor decimal está recortado en móvil")
                frame_cell = page.locator("#frames tr td:nth-child(4)").first
                frame_box = frame_cell.bounding_box()
                if not frame_box or frame_box["x"] + frame_box["width"] > 390:
                    raise AssertionError("La trama TX/RX no es visible en móvil")
                page.screenshot(
                    path=str(SCREENSHOTS / "movil.png"),
                    full_page=True, animations="disabled",
                )
                browser.close()
            for filename in ("escritorio.png", "monitor-tramas.png", "movil.png"):
                png = SCREENSHOTS / filename
                if not png.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"):
                    raise AssertionError(f"No se ha generado un PNG válido: {filename}")
                print(f"Captura real verificada: {png.relative_to(ROOT)} ({png.stat().st_size} bytes)")
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


if __name__ == "__main__":
    capture()
