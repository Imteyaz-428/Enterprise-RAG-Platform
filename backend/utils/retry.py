from tenacity import (
    stop_after_attempt,
    wait_exponential,
    retry_if_exception,
    Retrying,
)
from services.ai.config import (
    AI_MAX_RETRIES,
    AI_RETRY_MIN_WAIT,
    AI_RETRY_MAX_WAIT,
)
import services.ai.config as ai_config


def is_transient_error(exc: BaseException) -> bool:
    """
    Determines if an exception is transient (temporary network issue, rate limit, or 5xx server error)
    and should be retried before failing over, versus permanent (auth failure, invalid key, 4xx)
    which should fail immediately to the next provider.
    """
    # 1. Status code checks (from SDK exceptions or HTTP responses)
    status_code = getattr(exc, "status_code", getattr(exc, "code", None))
    if status_code is not None:
        try:
            code = int(status_code)
            # 400 (Bad Request), 401 (Auth), 402 (Billing/Insufficient Balance), 403 (Forbidden), 404 (Not Found), 422 (Unprocessable)
            if code in (400, 401, 402, 403, 404, 422):
                return False
            if code == 429 or 500 <= code <= 599:
                return True
        except (ValueError, TypeError):
            pass

    # 2. Check exception class names
    class_name = exc.__class__.__name__
    if any(auth_word in class_name for auth_word in ("Authentication", "Permission", "BadRequest", "NotFound", "InsufficientBalance")):
        return False
    if any(transient_word in class_name for transient_word in ("RateLimit", "Timeout", "Connection", "InternalServer", "ServerError", "Network")):
        return True

    # 3. Message heuristics
    msg = str(exc).lower()
    if any(w in msg for w in ("401", "402", "403", "unauthorized", "api key", "forbidden", "not found", "insufficient balance", "insufficient_balance", "balance", "credit", "billing", "payment required")):
        return False
    if any(w in msg for w in ("429", "rate limit", "quota", "resource exhausted", "timeout", "timed out", "connection reset", "503", "502")):
        return True

    # 4. Standard library network exception checks
    if isinstance(exc, (TimeoutError, ConnectionError)):
        return True
    if isinstance(exc, (ValueError, KeyError, TypeError)):
        return False

    return False


def retry_request(func, *args, max_attempts: int | None = None, **kwargs):
    attempts = max_attempts if max_attempts is not None else ai_config.AI_MAX_RETRIES
    if attempts <= 1:
        return func(*args, **kwargs)

    for attempt in Retrying(
        stop=stop_after_attempt(attempts),
        wait=wait_exponential(
            multiplier=1,
            min=ai_config.AI_RETRY_MIN_WAIT,
            max=ai_config.AI_RETRY_MAX_WAIT,
        ),
        retry=retry_if_exception(is_transient_error),
        reraise=True,
    ):
        with attempt:
            return func(*args, **kwargs)
