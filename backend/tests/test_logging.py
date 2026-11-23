import io
import json
import logging
from collections.abc import Iterator
from typing import Any

import pytest

from app.core.logging import REDACTED, JsonFormatter, configure_logging, redact


@pytest.fixture
def log_stream() -> Iterator[tuple[logging.Logger, io.StringIO]]:
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    logger = logging.getLogger("test.redaction")
    logger.handlers = [handler]
    logger.propagate = False
    logger.setLevel(logging.DEBUG)
    yield logger, stream
    logger.handlers = []


def last_line(stream: io.StringIO) -> dict[str, Any]:
    return json.loads(stream.getvalue().strip().splitlines()[-1])


def test_output_is_one_json_object_per_record(
    log_stream: tuple[logging.Logger, io.StringIO],
) -> None:
    logger, stream = log_stream
    logger.info("hello %s", "world", extra={"request_id": "abc"})

    entry = last_line(stream)
    assert entry["message"] == "hello world"
    assert entry["level"] == "INFO"
    assert entry["logger"] == "test.redaction"
    assert entry["request_id"] == "abc"


def test_authorization_header_in_message_is_redacted(
    log_stream: tuple[logging.Logger, io.StringIO],
) -> None:
    logger, stream = log_stream
    logger.info("incoming Authorization: Bearer abc123.def456-secret")

    assert "abc123.def456-secret" not in stream.getvalue()
    assert REDACTED in last_line(stream)["message"]


def test_bare_bearer_value_is_redacted(log_stream: tuple[logging.Logger, io.StringIO]) -> None:
    logger, stream = log_stream
    logger.warning("token was Bearer eyJhbGciOi.payload.sig rejected")

    assert "eyJhbGciOi" not in stream.getvalue()
    assert "rejected" in last_line(stream)["message"]


def test_basic_authorization_value_is_redacted(
    log_stream: tuple[logging.Logger, io.StringIO],
) -> None:
    logger, stream = log_stream
    logger.info("authorization=Basic dXNlcjpwYXNz")

    assert "dXNlcjpwYXNz" not in stream.getvalue()


def test_password_in_url_is_redacted(log_stream: tuple[logging.Logger, io.StringIO]) -> None:
    logger, stream = log_stream
    logger.error("cannot connect to postgresql+psycopg://admin:hunter2@db.internal:5432/app")

    output = stream.getvalue()
    assert "hunter2" not in output
    assert "admin" in output
    assert "db.internal" in output


def test_password_in_url_passed_as_log_argument_is_redacted(
    log_stream: tuple[logging.Logger, io.StringIO],
) -> None:
    logger, stream = log_stream
    logger.info("fetching %s", "https://user:p4ssw0rd@example.com/x")

    assert "p4ssw0rd" not in stream.getvalue()


def test_sensitive_query_parameters_are_redacted(
    log_stream: tuple[logging.Logger, io.StringIO],
) -> None:
    logger, stream = log_stream
    logger.info("GET /cb?code=1&access_token=tok-9999&api_key=key-8888 done")

    output = stream.getvalue()
    assert "tok-9999" not in output
    assert "key-8888" not in output
    assert "code=1" in output


def test_sensitive_extra_keys_are_redacted_whatever_the_value(
    log_stream: tuple[logging.Logger, io.StringIO],
) -> None:
    logger, stream = log_stream
    logger.info("login", extra={"password": "plain-pw-1", "auth_token": "tk-2", "user": "bob"})

    entry = last_line(stream)
    assert entry["password"] == REDACTED
    assert entry["auth_token"] == REDACTED
    assert entry["user"] == "bob"
    assert "plain-pw-1" not in stream.getvalue()


def test_secrets_inside_extra_string_values_are_redacted(
    log_stream: tuple[logging.Logger, io.StringIO],
) -> None:
    logger, stream = log_stream
    logger.info("call", extra={"target": "https://u:pw-xyz@host/path"})

    assert "pw-xyz" not in stream.getvalue()


def test_secrets_inside_non_string_extra_values_are_redacted(
    log_stream: tuple[logging.Logger, io.StringIO],
) -> None:
    logger, stream = log_stream
    logger.info("call", extra={"headers": {"note": "Authorization: Bearer leak-me-123"}})

    assert "leak-me-123" not in stream.getvalue()


def test_exception_traceback_is_redacted(log_stream: tuple[logging.Logger, io.StringIO]) -> None:
    logger, stream = log_stream
    try:
        raise RuntimeError("failed with Authorization: Bearer tb-secret-777")
    except RuntimeError:
        logger.exception("oops")

    output = stream.getvalue()
    assert "tb-secret-777" not in output
    assert "exc_info" in last_line(stream)


def test_redact_leaves_ordinary_text_alone() -> None:
    text = "GET /api/health 200 in 3ms from http://localhost:3000/path"

    assert redact(text) == text


def test_configure_logging_installs_a_single_redacting_handler(
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = logging.getLogger()
    saved_handlers, saved_level = list(root.handlers), root.level
    try:
        configure_logging("INFO")
        configure_logging("INFO")
        named = [h for h in root.handlers if h.get_name() == "launchaudit"]
        assert len(named) == 1

        logging.getLogger("test.configured").info("Authorization: Bearer end-to-end-secret")

        err = capsys.readouterr().err
        assert "end-to-end-secret" not in err
        assert REDACTED in err
    finally:
        root.handlers = saved_handlers
        root.setLevel(saved_level)


def test_configure_logging_keeps_sql_statements_quiet() -> None:
    root = logging.getLogger()
    saved_handlers, saved_level = list(root.handlers), root.level
    try:
        configure_logging("DEBUG")
        assert logging.getLogger("sqlalchemy.engine").getEffectiveLevel() >= logging.WARNING
    finally:
        root.handlers = saved_handlers
        root.setLevel(saved_level)
