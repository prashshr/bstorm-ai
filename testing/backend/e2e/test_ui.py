"""
End-to-End UI Tests for AI Ensemble Frontend
==============================================
Tests actual browser interactions: page loads, clicks, form fills, navigation.
Requires:
  - kubectl port-forward svc/ai-ensemble-web 8888:80
  - kubectl port-forward svc/ai-ensemble     8889:8080
  - playwright (pip install pytest-playwright && playwright install chromium)

Run: pytest tests/test_e2e_ui.py -v --tb=short
"""

import os
import pytest
from playwright.sync_api import Page, expect


FRONTEND_URL = os.getenv("E2E_FRONTEND_URL", "http://localhost:8888")
API_URL = os.getenv("E2E_API_URL", "http://localhost:8889")


@pytest.fixture(scope="function")
def page(page: Page):
    """Playwright page fixture with viewport and timeout settings."""
    page.set_viewport_size({"width": 1280, "height": 900})
    page.set_default_timeout(15000)
    yield page


# ============================================================
# Page Load & Render
# ============================================================

class TestPageLoad:
    def test_page_loads_successfully(self, page: Page):
        page.goto(FRONTEND_URL)
        title = page.title()
        assert "AI Ensemble" in title or "ai" in title.lower()

    def test_login_form_visible(self, page: Page):
        page.goto(FRONTEND_URL)
        login_page = page.locator("#loginPage")
        expect(login_page).to_be_visible()


# ============================================================
# Auth Flow (Register → Login)
# ============================================================

class TestAuthFlow:
    def test_register_new_user(self, page: Page, api_cleanup):
        page.goto(FRONTEND_URL)
        email_field = page.locator("#authIdentifier")
        pw_field = page.locator("#authPassword")
        register_btn = page.locator("button:has-text('Register')")

        expect(email_field).to_be_visible()
        expect(pw_field).to_be_visible()
        expect(register_btn).to_be_visible()

        ts = str(int(__import__("time").time()))
        email = f"e2e_{ts}@test.com"
        email_field.fill(email)
        pw_field.fill("E2ETest123!")
        register_btn.click()

        header = page.locator("#userDisplayHeader")
        expect(header).to_be_visible(timeout=10000)

    def test_login_after_register(self, page: Page, registered_user):
        email, password = registered_user
        page.goto(FRONTEND_URL)
        page.locator("#authIdentifier").fill(email)
        page.locator("#authPassword").fill(password)
        page.locator("button:has-text('Login')").click()
        header = page.locator("#userDisplayHeader")
        expect(header).to_be_visible(timeout=10000)


# ============================================================
# Provider Management
# ============================================================

class TestProviderUI:
    def test_add_provider_button_triggers_modal(self, page: Page, logged_in_user):
        page.goto(FRONTEND_URL)
        add_btn = page.locator("#addProviderBtn")
        expect(add_btn).to_be_visible()
        add_btn.click()
        modal = page.locator("#addProviderModal")
        expect(modal).to_be_visible(timeout=5000)

    def test_save_provider_credential(self, page: Page, logged_in_user):
        page.goto(FRONTEND_URL)
        page.locator("#addProviderBtn").click()
        page.wait_for_selector("#addProviderModal", state="visible")

        page.locator("#modalProviderSelect").select_option("openai")
        page.wait_for_selector("#modalApiKey", state="visible")
        page.locator("#modalApiKey").fill("sk-e2e-test-key-12345")
        page.locator("#modalSaveProviderBtn").click()

        msg = page.locator("#statusMsg")
        expect(msg).to_be_visible(timeout=10000)

    def test_provider_shows_in_list(self, page: Page, saved_provider):
        page.goto(FRONTEND_URL)
        provider_list = page.locator("#providerList")
        expect(provider_list).to_be_visible(timeout=5000)
        items = provider_list.locator(".provider-item, .provider-card, .provider-entry")
        count = items.count()
        assert count >= 1


# ============================================================
# Discussion Creation
# ============================================================

class TestDiscussionUI:
    def test_discussion_setup_form_visible(self, page: Page, logged_in_user):
        page.goto(FRONTEND_URL)
        setup = page.locator("#setupSection")
        expect(setup).to_be_visible(timeout=5000)
        models_panel = page.locator("#modelsPanel")
        expect(models_panel).to_be_visible()

    def test_question_input_accepts_text(self, page: Page, logged_in_user):
        page.goto(FRONTEND_URL)
        question_input = page.locator("#questionInput")
        expect(question_input).to_be_visible()
        question_input.fill("What is the best smartphone under 300 euros?")
        value = question_input.input_value()
        assert len(value) > 10

    def test_rag_checkbox_toggle(self, page: Page, logged_in_user):
        page.goto(FRONTEND_URL)
        rag_checkbox = page.locator("#useRagCheckbox")
        expect(rag_checkbox).to_be_visible()
        was_checked = rag_checkbox.is_checked()
        rag_checkbox.click()
        assert rag_checkbox.is_checked() != was_checked

    def test_start_discussion_no_models_warning(self, page: Page, logged_in_user):
        page.goto(FRONTEND_URL)
        page.locator("#questionInput").fill("Test question?")
        start_btn = page.locator("#startDiscussionBtn")
        expect(start_btn).to_be_visible()
        start_btn.click()
        status_msg = page.locator("#statusMsg")
        expect(status_msg).to_be_visible(timeout=5000)

    def test_discussion_history_list(self, page: Page, created_discussion):
        page.goto(FRONTEND_URL)
        history_tab = page.locator("#tab-history")
        expect(history_tab).to_be_visible()
        history_tab.click()
        history_list = page.locator("#historyList")
        expect(history_list).to_be_visible(timeout=5000)

    def test_discussion_displays_in_history(self, page: Page, created_discussion):
        page.goto(FRONTEND_URL)
        page.locator("#tab-history").click()
        page.wait_for_selector("#historyList", timeout=5000)
        hist_items = page.locator("#historyList .discussion-item, #historyList li, #historyList > div")
        hist_items.first.wait_for(state="visible", timeout=10000)
        assert hist_items.count() >= 1


# ============================================================
# RAG Status Indicator
# ============================================================

class TestRagUI:
    def test_rag_status_green_when_retrieved(self, page: Page, discussion_with_rag):
        page.goto(FRONTEND_URL)
        page.locator("#tab-history").click()
        page.wait_for_selector("#historyList", timeout=5000)
        first_item = page.locator("#historyList > div, #historyList li").first
        first_item.click()
        page.wait_for_timeout(2000)

        rag_dot = page.locator("#ragStatusDot")
        expect(rag_dot).to_be_visible(timeout=10000)
        dot_color = rag_dot.evaluate("el => getComputedStyle(el).backgroundColor")
        is_green = "22, 197" in dot_color or "green" in dot_color.lower() or "#22c55e" in dot_color
        assert is_green

    def test_rag_status_shows_context_size(self, page: Page, discussion_with_rag):
        page.goto(FRONTEND_URL)
        page.locator("#tab-history").click()
        page.wait_for_selector("#historyList", timeout=5000)
        page.locator("#historyList > div, #historyList li").first.click()
        page.wait_for_timeout(2000)

        rag_text = page.locator("#ragStatusText")
        expect(rag_text).to_be_visible(timeout=10000)
        text = rag_text.text_content() or ""
        assert "KB" in text or "context" in text or "RAG" in text


# ============================================================
# Responsive / Layout
# ============================================================

class TestLayout:
    def test_mobile_viewport_no_crash(self, page: Page):
        page.set_viewport_size({"width": 375, "height": 667})
        page.goto(FRONTEND_URL)
        login_page = page.locator("#loginPage")
        expect(login_page).to_be_visible()
        assert page.title() is not None

    def test_tablet_viewport_no_crash(self, page: Page):
        page.set_viewport_size({"width": 768, "height": 1024})
        page.goto(FRONTEND_URL)
        page.locator("#authIdentifier").fill("tablet@test.com")
        page.locator("#authPassword").fill("test123")
        assert page.locator("#authSubmitBtn").is_visible()
