import pytest
from pydantic import SecretStr

from app.core.security import MASK, mask_secret, verify_bearer_token


def test_long_value_keeps_a_short_prefix_only() -> None:
    masked = mask_secret("sk_live_abcdef123456")  # gitleaks:allow

    assert masked == "sk_l" + MASK
    assert "abcdef123456" not in masked


def test_visible_prefix_is_configurable() -> None:
    assert mask_secret("sk_live_abcdef123456", visible=6) == "sk_liv" + MASK  # gitleaks:allow


def test_short_value_is_fully_masked() -> None:
    assert mask_secret("abc") == MASK
    assert mask_secret("abcdefghijk") == MASK  # 11 chars, under 3 x 4


def test_boundary_length_keeps_prefix() -> None:
    assert mask_secret("abcdefghijkl") == "abcd" + MASK  # exactly 12 chars


@pytest.mark.parametrize("value", ["", None])
def test_empty_or_missing_value_is_fully_masked(value: str | None) -> None:
    assert mask_secret(value) == MASK


def test_zero_visible_never_reveals_anything() -> None:
    assert mask_secret("sk_live_abcdef123456", visible=0) == MASK  # gitleaks:allow


def test_negative_visible_never_reveals_anything() -> None:
    assert mask_secret("sk_live_abcdef123456", visible=-5) == MASK  # gitleaks:allow


def test_masked_output_never_contains_the_full_secret() -> None:
    secret = "ghp_" + "a1b2c3d4e5f6" * 3
    assert secret not in mask_secret(secret)


def test_verify_bearer_token_accepts_exact_match() -> None:
    assert verify_bearer_token("token-123", SecretStr("token-123")) is True


@pytest.mark.parametrize(
    ("provided", "expected"),
    [
        ("wrong", SecretStr("token-123")),
        (None, SecretStr("token-123")),
        ("", SecretStr("token-123")),
        ("token-123", None),
        ("", SecretStr("")),
        ("anything", SecretStr("")),
    ],
)
def test_verify_bearer_token_rejects(provided: str | None, expected: SecretStr | None) -> None:
    assert verify_bearer_token(provided, expected) is False


def test_verify_bearer_token_handles_non_ascii() -> None:
    assert verify_bearer_token("tökén", SecretStr("tökén")) is True
    assert verify_bearer_token("tokén", SecretStr("tökén")) is False


# ------------------------------------------------------- snippet masking


def test_mask_text_masks_connection_string_userinfo() -> None:
    from app.services.scan.masking import mask_text

    masked = mask_text(
        "DATABASE_URL=postgres://app_user:hunter2secret@db.internal:5432/shop"  # gitleaks:allow
    )

    assert masked == "DATABASE_URL=postgres://****@db.internal:5432/shop"


def test_mask_text_masks_bare_long_token() -> None:
    from app.services.scan.masking import mask_text

    token = "ab12" * 16  # 64 hex chars, fake value
    masked = mask_text(f"Authorization: Bearer {token}")

    assert token not in masked
    assert masked == "Authorization: Bearer ab12****"


def test_mask_text_leaves_plain_urls_and_paths_alone() -> None:
    from app.services.scan.masking import mask_text

    text = "see https://example.com/docs/getting-started for the guide"
    assert mask_text(text) == text
