"""Browser acceptance against a running server with synthetic data.

TOOLBOX_TEST_URL=http://127.0.0.1:8000 python tests/browser_optimizations.py
"""

import json
import os
from playwright.sync_api import sync_playwright, expect


def main():
    base = os.environ.get("TOOLBOX_TEST_URL", "http://127.0.0.1:8000")
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=os.environ.get("CHROMIUM_PATH", "/usr/bin/chromium"),
            headless=True,
            args=["--no-sandbox"],
        )
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(base)
        page.locator('[data-action="navigate"][data-view="tools"]').first.click()
        for tool, path in [
            ("P03", ["people", 0, "old"]),
            ("A06", ["invoice_lines", 0, "amount"]),
            ("R10", ["recipients", 0, "address"]),
        ]:
            page.locator("#global-search").fill(tool)
            page.locator(f'[data-action="open-tool"][data-id="{tool}"]').click()
            expect(page.locator("#payload")).to_be_visible()
            expect(page.locator(".detail-title .eyebrow")).to_contain_text(tool)
            with page.expect_response(
                lambda r: (
                    r.url.endswith("/api/tools/" + tool + "/test")
                    and r.request.method == "POST"
                )
            ) as response:
                page.locator('[data-action="run-test"]').click()
            assert response.value.status == 200, response.value.text()
            if tool == "P03":
                assert response.value.json()["status"] == "NEEDS_DECISION"
            target = page.locator(
                "[data-schema-path="
                + json.dumps(json.dumps(path, separators=(",", ": ")))
                + "]"
            )
            target.fill("changed")
            assert (
                json.loads(page.locator("#payload").input_value())[path[0]][0][path[-1]]
                == "changed"
            )
            page.locator('[data-action="load-sample"]').click()
            if tool == "P03":
                number = page.locator(
                    "[data-schema-path=" + json.dumps(json.dumps(["revision"])) + "]"
                )
                number.fill("")
                assert (
                    json.loads(page.locator("#payload").input_value())["revision"]
                    is None
                )
                page.locator('[data-action="run-test"]').click()
                expect(page.locator(".feedback.error")).to_be_visible()
                expect(page.locator(".field-error").first).to_be_visible()
                page.locator('[data-action="load-sample"]').click()
                tabs = page.get_by_role("tab")
                tabs.nth(0).focus()
                page.keyboard.press("ArrowRight")
                expect(tabs.nth(1)).to_be_focused()
                expect(tabs.nth(1)).to_have_attribute("aria-selected", "true")
                assert (
                    page.locator("#panel-how").get_attribute("aria-labelledby")
                    == "tab-how"
                )
                page.keyboard.press("End")
                expect(tabs.nth(2)).to_be_focused()
                page.keyboard.press("Home")
                expect(tabs.nth(0)).to_be_focused()
                page.locator("#job-due").fill("2026-10-25T02:30:00")
                page.locator('[data-action="schedule-job"]').click()
                expect(page.locator(".feedback.error")).to_be_visible()
                page.locator("#job-due").fill("2026-10-25T02:30:00+02:00")
                with page.expect_response(
                    lambda r: r.url.endswith("/api/jobs") and r.request.method == "POST"
                ) as queued:
                    page.locator('[data-action="schedule-job"]').click()
                assert queued.value.status == 200
                assert queued.value.json()["due_at"] == "2026-10-25T00:30:00+00:00"
            if tool == "A06":
                page.locator("#import-file").set_input_files(
                    {
                        "name": "test.csv",
                        "mimeType": "text/csv",
                        "buffer": b"line,hours,rate,amount\nL1,8,35.50,284.00\n",
                    }
                )
                page.locator('[data-action="import-file"]').click()
                page.locator('[data-action="apply-csv"]').click()
                expect(page.locator("#csv-errors")).to_contain_text("Zeile 1")
                for key, col in [
                    ("id", "line"),
                    ("hours", "hours"),
                    ("rate", "rate"),
                    ("amount", "amount"),
                ]:
                    page.locator(f'[data-csv-field="{key}"]').select_option(col)
                page.locator('[data-action="apply-csv"]').click()
                assert (
                    json.loads(page.locator("#payload").input_value())["invoice_lines"][
                        0
                    ]["id"]
                    == "L1"
                )
            page.locator('[data-action="navigate"][data-view="tools"]').first.click()
        page.locator("#global-search").fill("P05")
        page.locator('[data-action="open-tool"][data-id="P05"]').click()
        expect(page.locator("#payload")).to_be_visible()
        expect(page.locator(".detail-title .eyebrow")).to_contain_text("P05")
        dynamic = page.locator(
            "[data-schema-path="
            + json.dumps(json.dumps(["fields", "name"], separators=(",", ":")))
            + "]"
        )
        dynamic.fill("Beispiel")
        assert (
            json.loads(page.locator("#payload").input_value())["fields"]["name"]
            == "Beispiel"
        )
        group = dynamic.locator("xpath=ancestor::fieldset[1]")
        group.locator("[data-map-key]").fill("extra")
        group.locator('[data-action="add-map-key"]').click()
        page.locator(
            "[data-schema-path="
            + json.dumps(json.dumps(["fields", "extra"], separators=(",", ":")))
            + "]"
        ).fill("Wert")
        assert (
            json.loads(page.locator("#payload").input_value())["fields"]["extra"]
            == "Wert"
        )
        page.locator('[data-action="navigate"][data-view="workflows"]').first.click()
        page.locator("#workflow-title").fill("Synthetic workflow")
        page.locator('[data-action="create-workflow"]').click()
        expect(page.get_by_role("heading", name="Synthetic workflow")).to_be_visible()
        expect(
            page.get_by_role("heading", name="Schritte und Abhängigkeiten")
        ).to_be_visible()
        assert page.evaluate(
            "document.documentElement.scrollWidth <= window.innerWidth"
        )
        dialogs = []

        def confirm_leave(dialog):
            dialogs.append(dialog.type)
            dialog.accept()

        page.on("dialog", confirm_leave)
        page.locator("#workflow-edit-title").fill("Ungespeicherter Entwurf")
        # Saving this workflow must not discard the dirty P05 draft in another
        # workspace or silence its unload warning.
        page.locator('[data-action="save-workflow"]').click()
        expect(page.locator('[role="status"]').first).to_contain_text(
            "Fallkette aktualisiert"
        )
        page.reload()
        expect(page.get_by_role("heading", name="Arbeit, die leichter")).to_be_visible()
        assert "beforeunload" in dialogs
        assert not errors, errors
        browser.close()
    print("Browser optimizations passed")


if __name__ == "__main__":
    main()
