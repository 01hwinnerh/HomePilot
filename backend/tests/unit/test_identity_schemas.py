import pytest
from pydantic import ValidationError

from app.modules.identity.demo_seed import DEMO_PLATFORM_ADMIN_EMAIL
from app.modules.identity.schemas import CurrentUserResponse, LoginRequest


def test_login_request_accepts_the_fixed_demo_admin_email() -> None:
    request = LoginRequest(email=DEMO_PLATFORM_ADMIN_EMAIL, password="111")

    assert request.email == DEMO_PLATFORM_ADMIN_EMAIL


def test_login_request_still_rejects_arbitrary_local_domain_email() -> None:
    with pytest.raises(ValidationError):
        LoginRequest(email="someone@local", password="valid-password")


def test_current_user_response_accepts_the_fixed_demo_admin_email() -> None:
    response = CurrentUserResponse(
        id=1,
        email=DEMO_PLATFORM_ADMIN_EMAIL,
        is_platform_admin=True,
    )

    assert response.email == DEMO_PLATFORM_ADMIN_EMAIL
