"""
End-to-End UI Tests for AI Ensemble Frontend (Svelte 5)
========================================================
Tests actual browser interactions: page loads, clicks, form fills, navigation.

Updated for the Svelte 5 + Vite frontend (v2.0.0). Selectors prefer
role/text based locators and stable data-testid hooks over legacy element IDs.

Requires:
  - kubectl port-forward svc/ai-ensemble-web 8888:80
  - kubectl port-forward svc/ai-ensemble     8889:8080
  - playwright (pip install pytest-playwright && playwright install chromium)

Run: pytest testing/backend/e2e/test_ui.py -v --tb=short
"""

import os
import time

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


def _register(page: Page) -> tuple[str, str]:
    """Register a fresh user through the Svelte auth card and return creds."""
    page.goto(FRONTEND_URL)
    page.get_by_role("button", name="Register").click()
    ts = str(int(time.time() * 1000))
    email = f"e2e_{ts}@test.com"
    password = "E2ETest123!"
    page.locator("#auth-id").fill(email)
    page.locator("#auth-pw").fill(password)
    page.get_by_role("button", name="Create account").click()
    expect(page.get_by_test_id("user-display")).to_be_visible(timeout=10000)
    return email, password


# ============================================================
# Page Load & Render
# ============================================================

class TestPageLoad:
    def test_page_loads_successfully(self, page: Page):
        page.goto(FRONTEND_URL)
        title = page.title()
        assert "AI" in title or "ensemble" in title.lower()

    def test_login_form_visible(self, page: Page):
        page.goto(FRONTEND_URL)
        expect(page.get_by_test_id("login-page")).to_be_visible()
        expect(page.locator("#auth-id")).to_be_visible()
        expect(page.locator("#auth-pw")).to_be_visible()


# ============================================================
# Auth Flow (Register -> Login)
# ============================================================

class TestAuthFlow:
    def test_register_new_user(self, page: Page):
        email, _ = _register(page)
        expect(page.get_by_test_id("user-display")).to_contain_text(
            email.split("@")[0][:3]
        )

    def test_login_after_register(self, page: Page):
        email, password = _register(page)
        # Log out, then log back in
        page.get_by_role("button", name="Logout").click()
        expect(page.get_by_test_id("login-page")).to_be_visible()
        page.locator("#auth-id").fill(email)
        page.locator("#auth-pw").fill(password)
        page.get_by_role("button", name="Log in").click()
        expect(page.get_by_test_id("user-display")).to_be_visible(timeout=10000)


# ============================================================
# Navigation / Tabs
# ============================================================

class TestNavigation:
    def test_main_tabs_visible(self, page: Page):
        _register(page)
        expect(page.get_by_role("button", name="Provider")).to_be_visible()
        expect(page.get_by_role("button", name="New Discussion")).to_be_visible()
        expect(page.get_by_role("button", name="History")).to_be_visible()

    def test_tab_switching_updates_hash(self, page: Page):
        _register(page)
        page.get_by_role("button", name="History").click()
        page.wait_for_function("() => location.hash === '#history'")
        page.get_by_role("button", name="Provider").click()
        page.wait_for_function("() => location.hash === '#provider'")


# ============================================================
# Provider Management
# ============================================================

class TestProviderUI:
    def test_add_provider_button_reveals_form(self, page: Page):
        _register(page)
        page.get_by_role("button", name="Provider").click()
        add_btn = page.get_by_test_id("add-provider-btn")
        expect(add_btn).to_be_visible()
        add_btn.click()
        # The inline provider form exposes an API Key field
        expect(page.locator("#pf-key")).to_be_visible(timeout=5000)

    def test_save_provider_credential(self, page: Page):
        _register(page)
        page.get_by_role("button", name="Provider").click()
        page.get_by_test_id("add-provider-btn").click()
        page.wait_for_selector("#pf-key", state="visible")
        page.locator("#pf-preset").select_option("openai")
        page.locator("#pf-key").fill("sk-e2e-test-key-12345")
        page.get_by_role("button", name="Save & Discover").click()
        # Either success or an actionable error message is shown
        expect(page.locator(".msg")).to_be_visible(timeout=10000)

    def test_provider_shows_in_list(self, page: Page):
        _register(page)
        page.get_by_role("button", name="Provider").click()
        page.get_by_test_id("add-provider-btn").click()
        page.wait_for_selector("#pf-key", state="visible")
        page.locator("#pf-preset").select_option("openrouter")
        page.locator("#pf-key").fill("sk-or-e2e-test-key")
        page.get_by_role("button", name="Save & Discover").click()
        provider_list = page.get_by_test_id("provider-list")
        expect(provider_list).to_be_visible(timeout=10000)
        assert provider_list.locator(".card").count() >= 1


# ============================================================
# Discussion Creation
# ============================================================

class TestDiscussionUI:
    def test_new_discussion_form_visible(self, page: Page):
        _register(page)
        page.get_by_role("button", name="New Discussion").click()
        expect(page.get_by_test_id("question-input")).to_be_visible(timeout=5000)

    def test_question_input_accepts_text(self, page: Page):
        _register(page)
        page.get_by_role("button", name="New Discussion").click()
        q = page.get_by_test_id("question-input")
        q.fill("What is the best smartphone under 300 euros?")
        assert len(q.input_value()) > 10

    def test_rag_checkbox_toggle(self, page: Page):
        _register(page)
        page.get_by_role("button", name="New Discussion").click()
        rag = page.get_by_test_id("rag-toggle")
        expect(rag).to_be_visible()
        was = rag.is_checked()
        rag.click()
        assert rag.is_checked() != was

    def test_start_discussion_no_models_warning(self, page: Page):
        _register(page)
        page.get_by_role("button", name="New Discussion").click()
        page.get_by_test_id("question-input").fill("Test question?")
        page.get_by_test_id("start-discussion-btn").click()
        # Validation error surfaces (no models selected)
        expect(page.locator('[role="alert"]')).to_be_visible(timeout=5000)

    def test_history_tab_shows_list(self, page: Page):
        _register(page)
        page.get_by_role("button", name="History").click()
        # Either a populated list or the empty-state hint renders
        list_or_hint = page.get_by_test_id("history-list").or_(
            page.locator(".hint")
        )
        expect(list_or_hint.first).to_be_visible(timeout=5000)


# ============================================================
# Progress Stepper (design council: Queued -> Searching -> Drafting -> Synthesizing)
# ============================================================

class TestProgressStepper:
    def test_stepper_absent_before_discussion(self, page: Page):
        _register(page)
        # The compact stepper only mounts while a discussion is running
        assert page.locator(".stepper").count() == 0


# ============================================================
# Responsive / Layout
# ============================================================

class TestLayout:
    def test_mobile_viewport_no_crash(self, page: Page):
        page.set_viewport_size({"width": 375, "height": 667})
        page.goto(FRONTEND_URL)
        expect(page.get_by_test_id("login-page")).to_be_visible()
        assert page.title() is not None

    def test_tablet_viewport_no_crash(self, page: Page):
        page.set_viewport_size({"width": 768, "height": 1024})
        page.goto(FRONTEND_URL)
        page.locator("#auth-id").fill("tablet@test.com")
        page.locator("#auth-pw").fill("test123")
        expect(page.get_by_role("button", name="Log in")).to_be_visible()

    def test_theme_toggle(self, page: Page):
        _register(page)
        toggle = page.get_by_role("button", name="Toggle theme")
        expect(toggle).to_be_visible()
        before = page.locator("html").get_attribute("data-theme")
        toggle.click()
        page.wait_for_timeout(300)
        after = page.locator("html").get_attribute("data-theme")
        assert before != after
