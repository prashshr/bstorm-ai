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


_SHARED_CREDS: tuple[str, str] | None = None


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
    expect(page.get_by_role("button", name="User settings")).to_be_visible(timeout=10000)
    return email, password


def _get_or_create_user(page: Page) -> tuple[str, str]:
    """Reuse existing user session or credentials to avoid hitting rate limits."""
    global _SHARED_CREDS
    if _SHARED_CREDS:
        email, password = _SHARED_CREDS
        page.goto(FRONTEND_URL)
        try:
            if page.locator("button[aria-label='User settings']").is_visible():
                return email, password
        except Exception:
            pass
        # If not authenticated, log in
        if page.locator("#auth-id").is_visible():
            page.locator("#auth-id").fill(email)
            page.locator("#auth-pw").fill(password)
            page.get_by_role("button", name="Log in").click()
            expect(page.get_by_role("button", name="User settings")).to_be_visible(timeout=10000)
            return email, password
    _SHARED_CREDS = _register(page)
    return _SHARED_CREDS


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
        _register(page)
        expect(page.get_by_role("button", name="User settings")).to_be_visible()

    def test_login_after_register(self, page: Page):
        email, password = _register(page)
        # Open user settings and log out
        page.get_by_role("button", name="User settings").click()
        page.get_by_role("button", name="Data & Privacy").click()
        page.get_by_role("button", name="Sign Out").click()
        expect(page.get_by_test_id("login-page")).to_be_visible()
        page.locator("#auth-id").fill(email)
        page.locator("#auth-pw").fill(password)
        page.get_by_role("button", name="Log in").click()
        expect(page.get_by_role("button", name="User settings")).to_be_visible(timeout=10000)


# ============================================================
# Navigation & Layout Elements
# ============================================================

class TestNavigation:
    def test_main_elements_visible(self, page: Page):
        _get_or_create_user(page)
        expect(page.get_by_role("button", name="New chat")).to_be_visible()
        expect(page.get_by_role("button", name="Toggle providers panel")).to_be_visible()
        # Chat box is expandable
        expand_btn = page.get_by_role("button", name="Expand chat box")
        expect(expand_btn).to_be_visible()
        expand_btn.click()
        expect(page.get_by_test_id("chat-input")).to_be_visible()


# ============================================================
# Provider & Subscriptions Management
# ============================================================

class TestProviderUI:
    def test_provider_panel_opens_and_shows_subscriptions(self, page: Page):
        _get_or_create_user(page)
        panel_btn = page.get_by_role("button", name="Toggle providers panel")
        expect(panel_btn).to_be_visible()
        panel_btn.click()
        # Verify Subscriptions and API Providers sections exist
        expect(page.get_by_role("heading", name="Subscriptions")).to_be_visible(timeout=5000)
        expect(page.get_by_role("heading", name="API Providers")).to_be_visible(timeout=5000)


# ============================================================
# Discussion Creation & Chat Input
# ============================================================

class TestDiscussionUI:
    def test_chat_input_accepts_text(self, page: Page):
        _get_or_create_user(page)
        page.get_by_role("button", name="Expand chat box").click()
        inp = page.get_by_test_id("chat-input")
        expect(inp).to_be_visible()
        inp.click()
        inp.fill("What is the best smartphone under 300 euros?")
        expect(inp).to_contain_text("What is the best smartphone")

    def test_send_button_disabled_without_models(self, page: Page):
        _get_or_create_user(page)
        page.get_by_role("button", name="Expand chat box").click()
        send_btn = page.get_by_test_id("chat-send")
        expect(send_btn).to_be_visible()
        # With 0 models selected, send button should be disabled
        expect(send_btn).to_be_disabled()


# ============================================================
# Progress Stepper
# ============================================================

class TestProgressStepper:
    def test_stepper_absent_before_discussion(self, page: Page):
        _get_or_create_user(page)
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
        _get_or_create_user(page)
        toggle = page.get_by_role("button", name="Toggle theme")
        expect(toggle).to_be_visible()
        before = page.locator("html").get_attribute("data-theme")
        toggle.click()
        page.wait_for_timeout(300)
        after = page.locator("html").get_attribute("data-theme")
        assert before != after
