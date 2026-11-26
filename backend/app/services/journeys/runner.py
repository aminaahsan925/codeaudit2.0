"""Journey runner: drive a real browser through a shop's core flow.

Steps, in order: "Sign up", "Log in", "Add to cart", "Check out". A
screenshot is taken at every step that runs. The first failed step produces
exactly one High journey Finding; later steps are marked skipped and produce
no findings. A passed journey produces no findings.

The browser is launched with the proxy disabled so localhost targets work
on machines with a proxy configured. Credentials are never logged.

The target gets the same SSRF protection as the live checks: the base URL
is validated with the live client's DNS-resolving check before the browser
launches, and every request the browser makes (including redirects) is
checked again through request routing, so a page can never steer the
browser at a private or metadata address.
"""

from __future__ import annotations

import time
from contextlib import suppress
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

from playwright.sync_api import (
    Browser,
    Page,
    Playwright,
    Request,
    Route,
    sync_playwright,
)
from playwright.sync_api import (
    TimeoutError as PlaywrightTimeoutError,
)

from app.core.config import Settings
from app.schemas.finding import (
    Confidence,
    Evidence,
    Finding,
    FindingCategory,
    FindingEngine,
    Severity,
)
from app.services.live.ssrf_client import (
    SsrfBlockedError,
    assert_url_allowed,
    loopback_allowed,
)

from .models import (
    JourneyCredentials,
    JourneyResult,
    JourneyStep,
    JourneyStepStatus,
)

STEP_NAMES = ("Sign up", "Log in", "Add to cart", "Check out")
STEP_SCREENSHOTS = (
    "step-01-signup.png",
    "step-02-login.png",
    "step-03-cart.png",
    "step-04-checkout.png",
)
SIGNUP_NAME = "Test User"
STEP_TIMEOUT_MS = 15_000
TOTAL_TIMEOUT_MS = 120_000
RULE_ID = "JOURNEY_STEP_FAILED"
SKIPPED_DETAIL = "Skipped because an earlier step failed."


class JourneyTargetBlockedError(ValueError):
    """Raised when a journey target is not allowed (loopback/private)."""


class StepFailedError(Exception):
    """Raised when a journey step cannot complete."""


def _check_target_allowed(base_url: str, settings: Settings) -> None:
    """The journey target must pass the same SSRF check as live checks.

    The hostname is resolved and every address must be public, unless
    loopback targets are explicitly allowed outside production. Cloud
    metadata addresses are always blocked, even in loopback mode.
    """
    try:
        assert_url_allowed(base_url, allow_loopback=loopback_allowed(settings))
    except SsrfBlockedError as exc:
        raise JourneyTargetBlockedError(f"Journey target {base_url} is not allowed: {exc}") from exc


def _is_request_allowed(url: str, *, allow_loopback: bool, cache: dict[str, bool]) -> bool:
    """Whether the browser may fetch this URL (checked per host, cached).

    Only http(s) URLs whose host passes the SSRF check are allowed. The
    cache keeps one DNS lookup per host for the whole journey.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False
    host = (parsed.hostname or "").lower()
    if not host:
        return False
    if host not in cache:
        try:
            assert_url_allowed(url, allow_loopback=allow_loopback)
            cache[host] = True
        except SsrfBlockedError:
            cache[host] = False
    return cache[host]


def _guarded_page(browser: Browser, settings: Settings) -> Page:
    """A page whose every request is SSRF-checked before it is sent.

    Without this, a redirect or a form action on the target could steer
    the browser at a private or metadata address after the base URL
    itself passed validation. Blocked requests are aborted, which fails
    the current step (a finding) instead of fetching the address.
    """
    page = browser.new_page()
    allow_loopback = loopback_allowed(settings)
    cache: dict[str, bool] = {}

    def _on_route(route: Route, request: Request) -> None:
        if _is_request_allowed(request.url, allow_loopback=allow_loopback, cache=cache):
            route.continue_()
        else:
            route.abort()

    page.route("**/*", _on_route)
    return page


def _launch(p: Playwright):
    """Launch headless Chromium with the proxy disabled (localhost safe)."""
    return p.chromium.launch(
        headless=True,
        args=["--no-proxy-server", "--disable-dev-shm-usage"],
    )


def _wait_loaded(page: Page, timeout_ms: int) -> None:
    """Wait for the page to settle after a navigation or form submit."""
    try:
        page.wait_for_load_state("networkidle", timeout=timeout_ms)
    except PlaywrightTimeoutError:
        # Pages with polling or long-lived requests never go idle; the DOM
        # being loaded is enough for the checks that follow.
        page.wait_for_load_state("domcontentloaded", timeout=timeout_ms)


def _fill_field(
    page: Page,
    value: str,
    *,
    label: str | None = None,
    placeholder: str | None = None,
    name: str | None = None,
    input_type: str | None = None,
    field: str = "field",
) -> None:
    """Fill an input, trying accessible selectors first, then CSS fallbacks."""
    candidates = []
    if label:
        candidates.append(page.get_by_label(label, exact=False))
    if placeholder:
        candidates.append(page.get_by_placeholder(placeholder, exact=False))
    if name:
        candidates.append(page.locator(f'input[name="{name}"]'))
    if input_type:
        candidates.append(page.locator(f'input[type="{input_type}"]'))
    for locator in candidates:
        try:
            locator.first.fill(value, timeout=5000)
            return
        except Exception:  # noqa: S112 - try the next selector
            continue
    raise StepFailedError(f"Could not find the {field} field to fill in.")


def _click_submit(page: Page, names: list[str], what: str) -> None:
    """Click a form submit button. Never clicks links: nav links can share
    the same text as a submit button (e.g. a "Sign up" nav link next to a
    "Create account" submit button), and clicking one would just reload
    the page instead of submitting the form."""
    for button_name in names:
        for locator in (
            page.get_by_role("button", name=button_name, exact=False),
            page.locator(f'button:has-text("{button_name}")'),
            page.locator(f'input[type="submit"][value*="{button_name}"]'),
        ):
            try:
                locator.first.click(timeout=5000)
                return
            except Exception:  # noqa: S112 - try the next selector
                continue
    # Last resort: the form's own submit button, whatever it is called.
    with suppress(Exception):
        page.locator("form button[type='submit']").first.click(timeout=5000)
        return
    raise StepFailedError(f"Could not find the {what} button.")


def _click_button(page: Page, names: list[str], what: str) -> None:
    """Click a button or link (for navigation controls like Checkout)."""
    for button_name in names:
        for locator in (
            page.get_by_role("button", name=button_name, exact=False),
            page.get_by_role("link", name=button_name, exact=False),
            page.locator(f'button:has-text("{button_name}")'),
            page.locator(f'input[type="submit"][value*="{button_name}"]'),
            page.locator(f'a:has-text("{button_name}")'),
        ):
            try:
                locator.first.click(timeout=5000)
                return
            except Exception:  # noqa: S112 - try the next selector
                continue
    raise StepFailedError(f"Could not find the {what} button.")


def _page_text(page: Page) -> str:
    try:
        return page.locator("body").inner_text(timeout=5000)
    except Exception:  # a missing body means no readable text
        return ""


def _first_line(text: str, limit: int = 200) -> str:
    lines = text.strip().splitlines()
    return lines[0][:limit] if lines else "nothing"


def _step_signup(page: Page, base_url: str, email: str, password: str, timeout_ms: int) -> None:
    page.goto(f"{base_url}/signup", timeout=timeout_ms)
    _wait_loaded(page, timeout_ms)
    _fill_field(page, SIGNUP_NAME, label="Name", placeholder="Name", name="name", field="name")
    _fill_field(
        page,
        email,
        label="Email",
        placeholder="Email",
        name="email",
        input_type="email",
        field="email",
    )
    _fill_field(
        page,
        password,
        label="Password",
        placeholder="Password",
        name="password",
        input_type="password",
        field="password",
    )
    _click_submit(page, ["Sign up", "Create account", "Register"], "sign up")
    _wait_loaded(page, timeout_ms)
    text = _page_text(page).lower()
    if "already" in text and ("exist" in text or "registered" in text):
        # The account already exists from an earlier run, so the sign up
        # goal (an account for these credentials) is already met.
        return
    if "/login" in page.url:
        return
    if "success" in text or "created" in text or "welcome" in text:
        return
    if "error" in text or "invalid" in text or "too short" in text:
        detail = _first_line(_page_text(page))
        raise StepFailedError(f"Sign up was rejected by the site: {detail}")
    raise StepFailedError(
        f"Sign up did not reach the login page (ended on {page.url}). "
        f"Page showed: {_first_line(_page_text(page))}"
    )


def _step_login(page: Page, base_url: str, email: str, password: str, timeout_ms: int) -> None:
    page.goto(f"{base_url}/login", timeout=timeout_ms)
    _wait_loaded(page, timeout_ms)
    _fill_field(
        page,
        email,
        label="Email",
        placeholder="Email",
        name="email",
        input_type="email",
        field="email",
    )
    _fill_field(
        page,
        password,
        label="Password",
        placeholder="Password",
        name="password",
        input_type="password",
        field="password",
    )
    _click_submit(page, ["Log in", "Login", "Sign in"], "log in")
    _wait_loaded(page, timeout_ms)
    text = _page_text(page).lower()
    if "/login" in page.url:
        if "incorrect" in text or "invalid" in text or "not found" in text:
            raise StepFailedError("Log in failed: the site rejected the credentials.")
        raise StepFailedError("Log in did not leave the login page.")
    # A logged-in home page shows a logout control or the product list.
    logged_in = (
        page.get_by_role("link", name="Log out", exact=False).count() > 0
        or page.get_by_role("button", name="Log out", exact=False).count() > 0
        or "log out" in text
        or "add to cart" in text
    )
    if not logged_in:
        raise StepFailedError("Log in did not reach a logged-in page.")


def _step_add_to_cart(page: Page, base_url: str, timeout_ms: int) -> None:
    page.goto(f"{base_url}/", timeout=timeout_ms)
    _wait_loaded(page, timeout_ms)
    buttons = page.get_by_role("button", name="Add to cart", exact=False)
    if buttons.count() == 0:
        buttons = page.locator('button:has-text("Add to cart")')
    if buttons.count() == 0:
        buttons = page.locator('input[type="submit"][value*="Add to cart"]')
    if buttons.count() == 0:
        raise StepFailedError("No 'Add to cart' button found on the home page.")
    buttons.first.click(timeout=timeout_ms)
    _wait_loaded(page, timeout_ms)
    # Confirm the cart really holds something.
    page.goto(f"{base_url}/cart", timeout=timeout_ms)
    _wait_loaded(page, timeout_ms)
    text = _page_text(page).lower()
    if "empty" in text and "checkout" not in text:
        raise StepFailedError("The cart is still empty after adding a product.")


def _step_checkout(page: Page, base_url: str, timeout_ms: int) -> None:
    page.goto(f"{base_url}/cart", timeout=timeout_ms)
    _wait_loaded(page, timeout_ms)
    if "checkout" not in _page_text(page).lower():
        raise StepFailedError("The cart page has no checkout option.")
    _click_button(page, ["Checkout", "Check out", "Proceed to checkout"], "checkout")
    _wait_loaded(page, timeout_ms)
    if "/checkout" not in page.url:
        raise StepFailedError(f"Checkout did not open (ended on {page.url}).")
    if "pay" not in _page_text(page).lower():
        raise StepFailedError("The checkout page has no Pay button.")

    # Capture the payment response status while clicking Pay.
    pay_status: list[int] = []

    def _on_response(response) -> None:
        if "/checkout/pay" in response.url:
            pay_status.append(response.status)

    page.on("response", _on_response)
    try:
        _click_submit(page, ["Pay", "Pay now", "Place order"], "Pay")
        _wait_loaded(page, timeout_ms)
    finally:
        page.remove_listener("response", _on_response)

    text = _page_text(page)
    lowered = text.lower()
    if "order placed" in lowered:
        return
    status = pay_status[-1] if pay_status else None
    if status is not None and status >= 400:
        raise StepFailedError(
            f"Payment failed: the checkout returned HTTP {status} and the order was not placed."
        )
    if "payment failed" in lowered:
        raise StepFailedError(
            "Payment failed: the checkout showed a payment error page and the order was not placed."
        )
    if "error" in lowered or "something went wrong" in lowered:
        raise StepFailedError(
            "Payment failed: the checkout ended on an error page and the order was not placed."
        )
    raise StepFailedError(
        f"Payment failed: checkout did not reach an order confirmation (ended on {page.url})."
    )


_FIX_GUIDANCE = {
    "Sign up": (
        "## Why it matters\n\n"
        "A visitor who cannot create an account can never become a customer. "
        "Sign up is the first step of every purchase, so a broken sign up "
        "blocks all new sales from the site.\n\n"
        "## How to fix\n\n"
        "Open the sign up page in a browser and try to register with a fresh "
        "email address. Check the form fields, the submit button, and the "
        "server response. Fix the first error you see, then run the journey "
        "again to confirm sign up reaches the login page."
    ),
    "Log in": (
        "## Why it matters\n\n"
        "Returning customers must be able to log in to reach their cart and "
        "past orders. A broken log in locks out everyone who already has an "
        "account.\n\n"
        "## How to fix\n\n"
        "Try logging in with a known good account. Check that the email and "
        "password fields submit, the credentials are checked correctly, and a "
        "successful login redirects to the shop home page. Fix the first error "
        "you see, then run the journey again."
    ),
    "Add to cart": (
        "## Why it matters\n\n"
        "If shoppers cannot add a product to the cart, they cannot buy "
        "anything. The cart is the step between browsing and paying.\n\n"
        "## How to fix\n\n"
        "Open the home page and click Add to cart on the first product, then "
        "open the cart page and confirm the product is listed. Check the add "
        "to cart button, the cart session, and the cart page. Fix the first "
        "error you see, then run the journey again."
    ),
    "Check out": (
        "## Why it matters\n\n"
        "Checkout is where money changes hands. A shopper who reaches checkout "
        "and cannot pay leaves without buying, and most will not come back to "
        "try again.\n\n"
        "## How to fix\n\n"
        "Walk through checkout yourself with the test account: open the cart, "
        "press Checkout, and press Pay. Check the payment endpoint and the "
        "server logs for the error behind the failed payment, fix it, then run "
        "the journey again to confirm the order is placed."
    ),
}


def _failure_title(step_name: str, error: str) -> str:
    if step_name == "Check out":
        if "payment failed" in error.lower():
            return "Checkout failed at the payment step"
        return "Checkout failed"
    return f"{step_name} failed"


def _finding_for_failure(step_name: str, screenshot: str | None, error: str) -> Finding:
    """The single Finding for the first failed step of a journey."""
    return Finding(
        id=uuid4(),
        rule_id=RULE_ID,
        engine=FindingEngine.JOURNEY,
        category=FindingCategory.OTHER,
        severity=Severity.HIGH,
        confidence=Confidence.HIGH,
        title=_failure_title(step_name, error),
        evidence=Evidence(
            # Relative artifact name; the run orchestrator prefixes it with
            # the run's artifact URL (/api/runs/{run_id}/artifacts/{name}).
            screenshot_url=screenshot,
            notes=f"Step: {step_name}. {error}",
        ),
        fix_guidance=_FIX_GUIDANCE[step_name],
    )


def _screenshot(page: Page, path: Path) -> str | None:
    """Screenshot the current page; None if the browser cannot capture one."""
    try:
        page.screenshot(path=str(path))
    except Exception:  # a failed capture must not fail the run
        return None
    return path.name


def run_journey(
    base_url: str,
    credentials: JourneyCredentials,
    artifact_dir: str | Path,
    settings: Settings,
) -> JourneyResult:
    """Run the sign up, log in, add to cart, check out flow in Chromium.

    Screenshots land in artifact_dir as step-01-signup.png ..
    step-04-checkout.png. Each step gets at most 15s and the whole run at
    most 120s. On a failed step the journey stops, later steps are marked
    skipped, and exactly one High Finding is produced for the failed step.
    """
    _check_target_allowed(base_url, settings)
    out_path = Path(artifact_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    base_url = base_url.rstrip("/")
    email = credentials.email
    password = credentials.password.get_secret_value()

    steps: list[JourneyStep] = []
    findings: list[Finding] = []
    started = time.monotonic()

    step_fns = [
        lambda page, timeout_ms: _step_signup(page, base_url, email, password, timeout_ms),
        lambda page, timeout_ms: _step_login(page, base_url, email, password, timeout_ms),
        lambda page, timeout_ms: _step_add_to_cart(page, base_url, timeout_ms),
        lambda page, timeout_ms: _step_checkout(page, base_url, timeout_ms),
    ]

    with sync_playwright() as p:
        browser = _launch(p)
        try:
            page = _guarded_page(browser, settings)
            for index, (name, filename, fn) in enumerate(
                zip(STEP_NAMES, STEP_SCREENSHOTS, step_fns, strict=True)
            ):
                remaining_ms = TOTAL_TIMEOUT_MS - (time.monotonic() - started) * 1000
                if remaining_ms <= 0:
                    error = "Journey exceeded the 120s total timeout before this step ran."
                    screenshot = _screenshot(page, out_path / filename)
                    steps.append(
                        JourneyStep(
                            name=name,
                            status=JourneyStepStatus.FAILED,
                            screenshot=screenshot,
                            error=error,
                        )
                    )
                    findings.append(_finding_for_failure(name, screenshot, error))
                else:
                    step_timeout_ms = min(STEP_TIMEOUT_MS, int(remaining_ms))
                    page.set_default_timeout(step_timeout_ms)
                    try:
                        fn(page, step_timeout_ms)
                        status = JourneyStepStatus.PASSED
                        error = None
                    except StepFailedError as exc:
                        status = JourneyStepStatus.FAILED
                        error = str(exc)
                    except PlaywrightTimeoutError as exc:
                        status = JourneyStepStatus.FAILED
                        error = (
                            f"Timed out during {name.lower()}: {_first_line(str(exc), limit=300)}"
                        )
                    except Exception as exc:  # record, do not crash
                        status = JourneyStepStatus.FAILED
                        error = f"{name} failed: {_first_line(str(exc), limit=300)}"
                    screenshot = _screenshot(page, out_path / filename)
                    steps.append(
                        JourneyStep(
                            name=name,
                            status=status,
                            screenshot=screenshot,
                            error=error,
                        )
                    )
                    if status == JourneyStepStatus.FAILED and error is not None:
                        findings.append(_finding_for_failure(name, screenshot, error))
                if steps[-1].status == JourneyStepStatus.FAILED:
                    for later_name in STEP_NAMES[index + 1 :]:
                        steps.append(
                            JourneyStep(
                                name=later_name,
                                status=JourneyStepStatus.SKIPPED,
                                error=SKIPPED_DETAIL,
                            )
                        )
                    break
        finally:
            browser.close()

    return JourneyResult(steps=steps, findings=findings)
