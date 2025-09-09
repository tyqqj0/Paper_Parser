

from typing import Optional as _Optional


class S2ApiException(Exception):
    """
    统一的上游 S2 API 异常封装

    Attributes:
        message: 人类可读的错误信息
        error_code: 业务错误码，参考 `app.core.config.ErrorCodes`
        original_exception: 原始异常（可选）
    """

    def __init__(
        self,
        message: str,
        error_code: str,
        original_exception: _Optional[Exception] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.original_exception = original_exception