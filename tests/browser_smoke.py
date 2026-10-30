"""Optional browser acceptance; uses a running local server and synthetic inputs.

Run with a Python environment containing playwright and system Chromium.
This creates a synthetic case and job in the server's configured database.
"""

import json
import os
import uuid
from pathlib import Path

from playwright.sync_api import sync_playwright, expect


def main():
    base = os.environ.get("TOOLBOX_TEST_URL", "http://127.0.0.1:8000")
    output = Path("test-results")
    output.mkdir(exist_ok=True)
    errors = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path=os.environ.get("CHROMIUM_PATH", "/usr/bin/chromium"),
            headless=True,
            args=["--no-sandbox"],
        )
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(base)
        expect(page.get_by_role("heading", name="Arbeit, die leichter")).to_be_visible()
        page.screenshot(path=str(output / "desktop.png"), full_page=True)
        page.locator('[data-action="navigate"][data-view="tools"]').first.click()
        expect(page.locator(".tool-card")).to_have_count(81)
        page.locator("#global-search").fill("M07")
        expect(page.locator(".tool-card")).to_have_count(1)
        page.locator('[data-action="open-tool"][data-id="M07"]').click()
        sample = json.loads(page.locator("#payload").input_value())
        sample["facts"]["name"]["value"] = "Browser Testperson"
        page.locator("#payload").fill(json.dumps(sample, ensure_ascii=False))
        page.get_by_role("tab", name="So funktioniert’s").click()
        expect(
            page.get_by_role("heading", name="Was tut es?", exact=True)
        ).to_be_visible()
        page.get_by_role("tab", name="Anwenden & testen").click()
        assert json.loads(page.locator("#payload").input_value()) == sample
        page.locator('[data-action="run-test"]').click()
        expect(
            page.get_by_role("heading", name="Ergebnis der lokalen Prüfung")
        ).to_be_visible()
        expect(page.locator("a[download]")).to_have_count(1)
        page.screenshot(path=str(output / "tool.png"), full_page=True)
        page.locator("#payload").fill("{broken")
        page.locator('[data-action="run-test"]').click()
        expect(page.locator(".feedback.error")).to_be_visible()
        page.locator("#payload").fill(json.dumps(sample))
        unique = uuid.uuid4().hex[:10]
        title = "Browser-Test " + unique
        page.locator("#case-title").fill(title)
        page.locator("#source-ref").fill("synthetic:browser:" + unique)
        page.locator('[data-action="create-case"]').click()
        expect(page.get_by_role("heading", name=title, exact=True)).to_be_visible()
        page.locator('[data-action="complete"]').click()
        expect(page.locator(".feedback.error")).to_be_visible()
        page.locator('[data-action="approve"]').click()
        expect(page.locator('[role="status"]').first).to_contain_text("Freigabe")
        page.locator("#evidence-ref").fill("synthetic:manueller-vergleich")
        page.locator("#evidence-observed").fill(
            json.dumps({"draft": "Guten Tag Browser Testperson"})
        )
        page.locator('[data-action="evidence"]').click()
        expect(page.locator('[role="status"]').first).to_contain_text(
            "Nachweis gespeichert"
        )
        page.locator('[data-action="complete"]').click()
        expect(page.locator(".page-head .tag")).to_have_text("Abgeschlossen")
        sample["facts"]["name"]["value"] = "Neue Testrevision"
        page.locator("#edit-payload").fill(json.dumps(sample))
        page.locator('[data-action="save-case"]').click()
        expect(page.locator(".page-head .tag")).to_have_text("Offen")
        page.locator('[data-action="navigate"][data-view="tools"]').first.click()
        page.locator("#global-search").fill("M07")
        page.locator('[data-action="open-tool"][data-id="M07"]').click()
        page.locator("#import-file").set_input_files(
            {
                "name": "synthetisch.json",
                "mimeType": "application/json",
                "buffer": json.dumps(sample).encode(),
            }
        )
        page.locator('[data-action="import-file"]').click()
        expect(page.get_by_role("heading", name="Importvorschau")).to_be_visible()
        page.locator('[data-action="apply-import"]').click()
        assert json.loads(page.locator("#payload").input_value()) == sample
        assert page.locator("#source-ref").input_value().startswith("sha256:")
        page.locator('[data-action="schedule-job"]').click()
        expect(page.locator('[role="status"]').first).to_contain_text(
            "Prüfauftrag angelegt"
        )
        page.locator('[data-action="navigate"][data-view="jobs"]').click()
        expect(page.get_by_role("heading", name="Prüfaufträge.")).to_be_visible()
        expect(page.locator(".case-row").first).to_be_visible()
        page.set_viewport_size({"width": 390, "height": 844})
        page.locator('[data-action="navigate"][data-view="tools"]').first.click()
        page.locator("#global-search").fill("")
        expect(page.locator(".tool-card")).to_have_count(81)
        assert page.evaluate(
            "document.documentElement.scrollWidth <= window.innerWidth"
        ), "Mobile horizontal overflow"
        page.screenshot(path=str(output / "mobile.png"), full_page=True)
        assert not errors, errors
        browser.close()
    print(
        "Browser: catalog, search, how-to, test, artifact, malformed JSON, case lifecycle, revision invalidation, import, queue, mobile: passed."
    )


if __name__ == "__main__":
    main()
