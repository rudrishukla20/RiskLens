from enum import Enum


class ValidationStatusEnum(str, Enum):
    PENDING = "PENDING"
    VALIDATING = "VALIDATING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    WARNING = "WARNING"
