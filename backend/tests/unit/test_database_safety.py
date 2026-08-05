import pytest

from app.core.database import UnsafeTestDatabaseError, validate_test_database_isolation


def test_test_database_cannot_use_business_database_name() -> None:
    with pytest.raises(UnsafeTestDatabaseError, match="must differ"):
        validate_test_database_isolation(
            database_url="mysql+asyncmy://app:secret@localhost/homepilot",
            test_database_url="mysql+asyncmy://tester:secret@localhost/homepilot",
        )


def test_test_database_name_must_be_explicitly_marked_as_test() -> None:
    with pytest.raises(UnsafeTestDatabaseError, match="contain 'test'"):
        validate_test_database_isolation(
            database_url="mysql+asyncmy://app:secret@localhost/homepilot",
            test_database_url="mysql+asyncmy://tester:secret@localhost/homepilot_shadow",
        )


def test_configurable_test_database_name_is_allowed() -> None:
    validate_test_database_isolation(
        database_url="mysql+asyncmy://app:secret@localhost/homepilot",
        test_database_url="mysql+asyncmy://tester:secret@localhost/homepilot_ci_test",
    )
