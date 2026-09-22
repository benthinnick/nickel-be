from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.security import OAuth2PasswordRequestForm

from app.api.dependencies import get_cart_service, get_user_service
from app.api.session import peek_session_id
from app.domain.schemas.user import TokenResponse
from app.infrastructure.auth.tokens import create_access_token
from app.services.cart_service import CartService
from app.services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/token", response_model=TokenResponse)
async def issue_token(
    request: Request,
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    users: Annotated[UserService, Depends(get_user_service)],
    carts: Annotated[CartService, Depends(get_cart_service)],
) -> TokenResponse:
    user = await users.authenticate(email=form.username, password=form.password)
    session_id = peek_session_id(request)
    if session_id is not None:
        await carts.merge_session_into_user(session_id=session_id, user_id=user.id)
    token = create_access_token(user_id=user.id, email=user.email)
    return TokenResponse(access_token=token)
