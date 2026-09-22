from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_current_user, get_user_service
from app.domain.models.user import User
from app.domain.schemas.user import RegisterUserRequest, UserResponse, user_to_response
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    body: RegisterUserRequest,
    users: Annotated[UserService, Depends(get_user_service)],
) -> UserResponse:
    user = await users.register(email=str(body.email), password=body.password)
    return user_to_response(user)


@router.get("/me", response_model=UserResponse)
async def get_me(
    user: Annotated[User, Depends(get_current_user)],
) -> UserResponse:
    return user_to_response(user)
