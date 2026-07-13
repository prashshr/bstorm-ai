"""
Frontend Button & Function Regression Tests
=============================================
Verifies that all onclick handlers in index.html reference defined functions,
and that critical UI functions (copy, delete, filter, tab switching) work correctly.

These tests parse the HTML file directly and validate the JavaScript content,
simulating what a browser would check when a button is clicked.
"""

import re
import os
import json
import pytest


FRONTEND_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "frontend", "index.html"
)


def read_frontend():
    with open(FRONTEND_PATH, "r") as f:
        return f.read()


# ============================================================
# Test: All onclick handlers reference defined functions
# ============================================================

class TestOnclickHandlersExist:
    """Every onclick handler in the HTML must reference a function that exists in the JS."""

    def test_all_onclick_functions_defined(self):
        content = read_frontend()
        onclick_handlers = re.findall(r'onclick="([^"]+)"', content)
        
        missing = []
        for handler in onclick_handlers:
            for fn_match in re.finditer(r'(\w+)\s*\(', handler):
                fn_name = fn_match.group(1)
                if fn_name in ('event', 'if', 'stopPropagation', 'preventDefault'):
                    continue
                pattern = rf'function\s+{re.escape(fn_name)}\s*\('
                if not re.search(pattern, content):
                    missing.append(fn_name)
        
        assert not missing, f"Functions referenced in onclick but not defined: {sorted(set(missing))}"

    def test_all_onkeydown_functions_defined(self):
        content = read_frontend()
        onkeydown_handlers = re.findall(r'onkeydown="([^"]+)"', content)
        
        missing = []
        for handler in onkeydown_handlers:
            for fn_match in re.finditer(r'(\w+)\s*\(', handler):
                fn_name = fn_match.group(1)
                if fn_name in ('event', 'if', 'stopPropagation', 'preventDefault'):
                    continue
                pattern = rf'function\s+{re.escape(fn_name)}\s*\('
                if not re.search(pattern, content):
                    missing.append(fn_name)
        
        assert not missing, f"Functions referenced in onkeydown but not defined: {sorted(set(missing))}"


# ============================================================
# Test: Critical functions have proper error handling
# ============================================================

def extract_function(content, fn_sig):
    """Extract a function body from the content, handling nested braces."""
    idx = content.find(fn_sig)
    if idx == -1:
        return None
    brace_start = content.find('{', idx)
    if brace_start == -1:
        return None
    depth = 0
    for i in range(brace_start, len(content)):
        if content[i] == '{':
            depth += 1
        elif content[i] == '}':
            depth -= 1
            if depth == 0:
                return content[idx:i+1]
    return None


class TestClipboardFunctions:
    """All clipboard functions must use .then()/.catch() for async feedback."""

    def test_copy_question_has_error_handling(self):
        content = read_frontend()
        fn_body = extract_function(content, 'function copyQuestion()')
        assert fn_body, "copyQuestion function not found"
        assert '.catch' in fn_body, "copyQuestion missing .catch() error handling"
        assert '.then' in fn_body or 'await' in fn_body, "copyQuestion missing promise handling"

    def test_copy_history_query_has_error_handling(self):
        content = read_frontend()
        fn_body = extract_function(content, 'function copyHistoryQuery(id)')
        assert fn_body, "copyHistoryQuery function not found"
        assert '.catch' in fn_body, "copyHistoryQuery missing .catch() error handling"

    def test_copy_history_summary_has_error_handling(self):
        content = read_frontend()
        fn_body = extract_function(content, 'function copyHistorySummary(id)')
        assert fn_body, "copyHistorySummary function not found"
        assert '.catch' in fn_body, "copyHistorySummary missing .catch() error handling"

    def test_copy_to_clipboard_has_error_handling(self):
        content = read_frontend()
        fn_body = extract_function(content, 'function copyToClipboard()')
        assert fn_body, "copyToClipboard function not found"
        assert '.catch' in fn_body, "copyToClipboard missing .catch() error handling"

    def test_copy_functions_have_visual_feedback(self):
        content = read_frontend()
        for fn_name in ['copyQuestion', 'copyHistoryQuery', 'copyHistorySummary']:
            fn_body = extract_function(content, f'function {fn_name}(')
            assert fn_body, f"{fn_name} not found"
            assert 'Copied' in fn_body or '✅' in fn_body, f"{fn_name} missing visual feedback"


# ============================================================
# Test: No hardcoded colors remain
# ============================================================

class TestNoHardcodedColors:
    """All colors should use CSS variables, not hardcoded hex values."""

    HARDCODED_COLORS = ['#ff453a', '#6c757d', '#e06c75', '#1c1c1e', '#2c2c2e', '#3a3a3c', '#3a1a1a']

    def test_no_hardcoded_colors_in_styles(self):
        content = read_frontend()
        found = []
        for color in self.HARDCODED_COLORS:
            if color in content:
                found.append(color)
        assert not found, f"Hardcoded colors still present: {found}"


# ============================================================
# Test: Border-radius consistency
# ============================================================

class TestBorderRadiusConsistency:
    """Inline border-radius should be 6px (matching .form-section), not 8px or 12px."""

    def test_no_8px_border_radius_inline(self):
        content = read_frontend()
        matches = re.findall(r'border-radius:\s*8px', content)
        assert not matches, f"Found {len(matches)} inline border-radius:8px (should be 6px)"

    def test_no_12px_border_radius_inline(self):
        content = read_frontend()
        # Only check in <style> section and inline styles, not in CSS comments
        matches = re.findall(r'border-radius:\s*12px', content)
        # Login card is the only exception, but we fixed it to 6px
        assert not matches, f"Found {len(matches)} inline border-radius:12px (should be 6px)"


# ============================================================
# Test: History functions
# ============================================================

class TestHistoryFunctions:
    """History-related functions must be properly defined."""

    def test_delete_history_item_exists(self):
        content = read_frontend()
        assert 'function deleteHistoryItem' in content, "deleteHistoryItem function not found"
        fn_match = re.search(r'function deleteHistoryItem\(id\)[^}]*\}', content, re.DOTALL)
        assert fn_match, "deleteHistoryItem function body not found"
        fn_body = fn_match.group(0)
        assert 'confirm' in fn_body, "deleteHistoryItem missing confirmation dialog"
        assert 'filter' in fn_body, "deleteHistoryItem missing filter to remove item"

    def test_render_history_exists(self):
        content = read_frontend()
        assert 'function renderHistory' in content, "renderHistory function not found"

    def test_filter_history_exists(self):
        content = read_frontend()
        assert 'function filterHistory' in content, "filterHistory function not found"

    def test_running_filter_checks_active_session(self):
        content = read_frontend()
        fn_match = re.search(r"window\._historyFilter === 'running'[^;]*;", content, re.DOTALL)
        assert fn_match, "Running filter not found"
        filter_body = fn_match.group(0)
        assert 'discussionRunning' in filter_body or 'discussionData' in filter_body, \
            "Running filter doesn't check for active session"

    def test_status_dots_use_css_colors(self):
        content = read_frontend()
        # Check renderHistory function body for status dot colors
        fn_body = extract_function(content, 'function renderHistory()')
        assert fn_body, "renderHistory function not found"
        assert '22c55e' in fn_body, "Green status dot not using #22c55e"
        assert 'f59e0b' in fn_body, "Amber status dot not using #f59e0b"
        assert '8e8e93' in fn_body, "Gray status dot not using #8e8e93"

    def test_history_has_delete_button(self):
        content = read_frontend()
        render_match = re.search(r'function renderHistory\(\).*?\.join\(\'\'\)', content, re.DOTALL)
        assert render_match, "renderHistory not found"
        body = render_match.group(0)
        assert 'deleteHistoryItem' in body, "Delete button not in history render"
        assert '🗑️' in body, "Delete icon not in history render"


# ============================================================
# Test: safeRenderMarkdown
# ============================================================

class TestSafeRenderMarkdown:
    """safeRenderMarkdown must handle missing marked/DOMPurify gracefully."""

    def test_function_exists(self):
        content = read_frontend()
        assert 'function safeRenderMarkdown' in content, "safeRenderMarkdown not found"

    def test_checks_marked_defined(self):
        content = read_frontend()
        fn_match = re.search(r'function safeRenderMarkdown\(text\)[^}]*\}', content, re.DOTALL)
        assert fn_match, "safeRenderMarkdown body not found"
        body = fn_match.group(0)
        assert "typeof marked" in body, "safeRenderMarkdown doesn't check typeof marked"
        assert "typeof marked !== 'undefined'" in body, "safeRenderMarkdown doesn't guard marked"

    def test_checks_dompurify_defined(self):
        content = read_frontend()
        fn_match = re.search(r'function safeRenderMarkdown\(text\)[^}]*\}', content, re.DOTALL)
        assert fn_match, "safeRenderMarkdown body not found"
        body = fn_match.group(0)
        assert "typeof DOMPurify" in body, "safeRenderMarkdown doesn't check typeof DOMPurify"

    def test_has_html_escape_fallback(self):
        content = read_frontend()
        fn_body = extract_function(content, 'function safeRenderMarkdown(text)')
        assert fn_body, "safeRenderMarkdown body not found"
        assert '&amp;' in fn_body, "safeRenderMarkdown missing &amp; escape"
        assert '&lt;' in fn_body, "safeRenderMarkdown missing &lt; escape"
        assert '&gt;' in fn_body, "safeRenderMarkdown missing &gt; escape"

    def test_no_bare_marked_parse_calls(self):
        content = read_frontend()
        # marked.parse should only appear inside safeRenderMarkdown function
        safe_fn = extract_function(content, 'function safeRenderMarkdown(text)')
        assert safe_fn, "safeRenderMarkdown function not found"
        # Count all marked.parse occurrences
        all_calls = re.findall(r'marked\.parse\(', content)
        # Count those inside safeRenderMarkdown
        safe_calls = re.findall(r'marked\.parse\(', safe_fn)
        bare_calls = len(all_calls) - len(safe_calls)
        assert bare_calls == 0, f"Found {bare_calls} bare marked.parse() calls outside safeRenderMarkdown"


# ============================================================
# Test: SRI integrity hashes
# ============================================================

class TestSRIIntegrity:
    """CDN scripts must have correct SRI integrity hashes."""

    def test_marked_has_integrity(self):
        content = read_frontend()
        match = re.search(r'marked@[\d.]+/marked\.min\.js"\s+integrity="sha384-([^"]+)"', content)
        assert match, "marked CDN missing SRI integrity"
        hash_val = match.group(1)
        assert len(hash_val) >= 50, f"marked SRI hash too short: {hash_val}"
        assert hash_val.startswith('/'), f"marked SRI hash should start with /: {hash_val[:10]}"

    def test_dompurify_has_integrity(self):
        content = read_frontend()
        match = re.search(r'purify\.min\.js"[^>]*integrity="sha384-([A-Za-z0-9+/]+)"', content)
        assert match, "DOMPurify CDN missing SRI integrity"
        hash_val = match.group(1)
        assert len(hash_val) >= 50, f"DOMPurify SRI hash too short: {hash_val}"

    def test_scripts_have_crossorigin(self):
        content = read_frontend()
        scripts = re.findall(r'<script src="https://cdn[^"]*"[^>]*>', content)
        for s in scripts:
            assert 'crossorigin' in s, f"CDN script missing crossorigin: {s[:60]}"


# ============================================================
# Test: Header & title
# ============================================================

class TestHeader:
    """Header must show 'AI-Ensemble' (no spaces around hyphen)."""

    def test_title_is_ai_ensemble(self):
        content = read_frontend()
        assert '<title>AI-Ensemble</title>' in content, "Page title is not 'AI-Ensemble'"

    def test_no_old_title_format(self):
        content = read_frontend()
        assert 'AI - Ensemble' not in content, "Old 'AI - Ensemble' title still present"

    def test_header_h1_has_keyboard_access(self):
        content = read_frontend()
        h1_match = re.search(r'<h1[^>]*AI-Ensemble[^>]*>', content)
        assert h1_match, "Header h1 not found"
        h1_tag = h1_match.group(0)
        assert 'tabindex="0"' in h1_tag, "Header h1 missing tabindex"
        assert 'role="button"' in h1_tag, "Header h1 missing role"
        assert 'aria-label' in h1_tag, "Header h1 missing aria-label"
        assert 'onkeydown' in h1_tag, "Header h1 missing onkeydown"

    def test_header_user_display_is_vertical(self):
        content = read_frontend()
        match = re.search(r'id="userDisplayHeader"[^>]*style="([^"]*)"', content)
        assert match, "userDisplayHeader not found"
        style = match.group(1)
        assert 'flex-direction: column' in style, "userDisplayHeader not vertical (flex-direction: column)"
        assert 'align-items: flex-start' in style, "userDisplayHeader not left-aligned (align-items: flex-start)"

    def test_header_says_user_not_logged_in(self):
        content = read_frontend()
        assert 'User:' in content, "Header should say 'User:' not 'Logged in as:'"
        assert 'Logged in as' not in content, "Header still says 'Logged in as'"


# ============================================================
# Test: Sidebar provider management
# ============================================================

class TestSidebarProviders:
    """Provider management must be in the left sidebar, not a centered modal."""

    def test_no_add_provider_modal(self):
        content = read_frontend()
        assert 'id="addProviderModal"' not in content, "Centered modal #addProviderModal still present"

    def test_sidebar_provider_list_exists(self):
        content = read_frontend()
        assert 'id="sidebarProviderList"' in content, "Sidebar provider list not found"

    def test_sidebar_provider_form_exists(self):
        content = read_frontend()
        assert 'id="sidebarProviderForm"' in content, "Sidebar provider form not found"

    def test_sidebar_add_provider_function_exists(self):
        content = read_frontend()
        assert 'function sidebarAddProvider' in content, "sidebarAddProvider function not found"
        assert 'function closeSidebarProviderForm' in content, "closeSidebarProviderForm function not found"
        assert 'function saveSidebarProvider' in content, "saveSidebarProvider function not found"

    def test_no_provider_grid_in_main_content(self):
        content = read_frontend()
        assert 'id="providerGridList"' not in content, "Duplicate provider grid still in main content"

    def test_provider_tab_exists(self):
        content = read_frontend()
        assert 'id="tab-provider"' in content, "Provider tab not found"
        assert 'id="providerMainTab"' in content, "Provider main tab button not found"

    def test_provider_tab_keeps_sidebar(self):
        content = read_frontend()
        fn_body = extract_function(content, 'function switchTab(tab)')
        assert fn_body, "switchTab function not found"
        assert 'provider' in fn_body, "switchTab doesn't handle 'provider' tab"
        assert 'full-width' in fn_body, "switchTab doesn't handle full-width class"

    def test_render_sidebar_providers_exists(self):
        content = read_frontend()
        assert 'function renderSidebarProviders' in content, "renderSidebarProviders function not found"

    def test_show_provider_edit_tab_exists(self):
        content = read_frontend()
        assert 'function showProviderEditTab' in content, "showProviderEditTab function not found"


# ============================================================
# Test: RAG loading bar
# ============================================================

class TestRagLoadingBar:
    """RAG loading bar must be animated, not static."""

    def test_rag_shimmer_animation_exists(self):
        content = read_frontend()
        assert '@keyframes ragShimmer' in content, "ragShimmer animation not found"
        assert 'translateX' in content, "ragShimmer doesn't use translateX animation"

    def test_rag_loading_bar_has_pseudo_element(self):
        content = read_frontend()
        assert '.rag-loading-bar::after' in content, "rag-loading-bar::after not found"

    def test_rag_loading_bar_height_matches_progress(self):
        content = read_frontend()
        bar_match = re.search(r'\.rag-loading-bar\s*\{([^}]*)\}', content)
        assert bar_match, ".rag-loading-bar CSS not found"
        bar_css = bar_match.group(1)
        assert 'height: 4px' in bar_css, "rag-loading-bar height should be 4px"

    def test_rag_loading_bar_uses_accent_color(self):
        content = read_frontend()
        after_match = re.search(r'\.rag-loading-bar::after\s*\{([^}]*)\}', content)
        assert after_match, ".rag-loading-bar::after CSS not found"
        after_css = after_match.group(1)
        assert 'var(--accent)' in after_css, "rag-loading-bar::after should use var(--accent)"


# ============================================================
# Test: Streaming timeout guard
# ============================================================

class TestStreamingTimeout:
    """Streaming reader must have a timeout guard."""

    def test_streaming_has_read_timeout(self):
        content = read_frontend()
        assert 'readerTimeout' in content, "Streaming reader timeout not found"
        assert 'clearTimeout' in content, "clearTimeout not found in streaming code"

    def test_stream_error_propagation(self):
        content = read_frontend()
        assert 'streamError' in content, "streamError variable not found"
        assert 'streamFinished' in content, "streamFinished variable not found"


# ============================================================
# Test: Bounded concurrency
# ============================================================

class TestBoundedConcurrency:
    """Model execution must use bounded concurrency."""

    def test_semaphore_exists(self):
        content = read_frontend()
        assert 'MAX_CONCURRENT' in content, "MAX_CONCURRENT not found"
        assert 'semaphore' in content.lower(), "Semaphore pattern not found"

    def test_stagger_delay_exists(self):
        content = read_frontend()
        assert 'STAGGER_MS' in content, "STAGGER_MS not found"
