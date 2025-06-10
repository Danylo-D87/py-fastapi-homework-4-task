from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Form, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from exceptions import InvalidTokenError, TokenExpiredError
from security.http import get_token
from security.interfaces import JWTAuthManagerInterface
from schemas.profiles import ProfileRequestSchema, ProfileResponseSchema
from database import get_db

from database.models.accounts import (
    UserModel,
    UserGroupEnum,
    UserProfileModel,
    GenderEnum,
)
from storages import S3StorageInterface
from config import (
    BaseAppSettings,
    get_settings,
    get_s3_storage_client,
    get_jwt_auth_manager,
)


router = APIRouter(prefix="/users", tags=["profiles"])


async def get_current_user(
    token: Annotated[str, Depends(get_token)],
    db_session: Annotated[AsyncSession, Depends(get_db)],
    jwt_manager: Annotated[JWTAuthManagerInterface, Depends(get_jwt_auth_manager)],
) -> UserModel:
    """
    Retrieves the current user based on the provided JWT token.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt_manager.decode_access_token(token)

        user_id_from_token: int = payload.get("user_id")

        if user_id_from_token is None:
            raise credentials_exception

    except TokenExpiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired."
        )
    except InvalidTokenError:
        raise credentials_exception
    except Exception as e:
        print(f"Error during JWT decoding in get_current_user: {e}")
        raise credentials_exception

    user_result = await db_session.execute(
        select(UserModel)
        .options(selectinload(UserModel.group))
        .filter(UserModel.id == user_id_from_token)
    )
    user = user_result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found."
        )
    return user


async def get_current_active_user(
    current_user: Annotated[UserModel, Depends(get_current_user)],
) -> UserModel:
    """
    Ensures the retrieved user is active.
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or not active.",
        )
    return current_user


async def get_profile_request_payload(
        first_name: Annotated[str, Form()],
        last_name: Annotated[str, Form()],
        gender: Annotated[str, Form()],
        date_of_birth: Annotated[date, Form()],
        info: Annotated[str, Form()],
        avatar: Annotated[UploadFile, File()],
) -> ProfileRequestSchema:
    """
    Залежність для збору та валідації даних профілю з multipart/form-data.
    """
    try:
        # Валідація gender
        try:
            gender_enum = GenderEnum(gender)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Gender must be one of: {[e.value for e in GenderEnum]}"
            )
        # Валідація date_of_birth
        if isinstance(date_of_birth, str):
            try:
                date_of_birth = date.fromisoformat(date_of_birth)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Invalid date format. Use YYYY-MM-DD"
                )
        # Валідація avatar
        if not avatar.content_type.startswith('image/'):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="File must be an image"
            )
        return ProfileRequestSchema(
            first_name=first_name,
            last_name=last_name,
            gender=gender_enum,
            date_of_birth=date_of_birth,
            info=info,
            avatar=avatar,
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Validation error: {str(e)}"
        )



@router.post(
    "/{user_id}/profile/",
    response_model=ProfileResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create a user profile",
    description="Creates a new user profile for the specified user ID, including avatar upload to S3.",
)
async def create_user_profile(
    user_id: int,
    profile_data: ProfileRequestSchema = Depends(get_profile_request_payload),
    db_session: AsyncSession = Depends(get_db),
    s3_client: S3StorageInterface = Depends(get_s3_storage_client),
    current_user: UserModel = Depends(get_current_active_user),
    settings: BaseAppSettings = Depends(get_settings),
):
    """
    Ендпоінт для створення нового профілю користувача.
    """

    if current_user.id != user_id and not current_user.has_group(UserGroupEnum.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to edit this profile.",
        )

    user_to_create_profile_for = await db_session.execute(
        select(UserModel).filter(UserModel.id == user_id)
    )
    target_user: UserModel = user_to_create_profile_for.scalar_one_or_none()

    if not target_user or not target_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or not active.",
        )

    existing_profile = await db_session.execute(
        select(UserProfileModel).filter(UserProfileModel.user_id == user_id)
    )
    if existing_profile.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already has a profile.",
        )

    avatar_file: UploadFile = profile_data.avatar
    file_extension = (
        avatar_file.filename.split(".")[-1] if "." in avatar_file.filename else "jpg"
    )
    avatar_filename = f"{user_id}_avatar.{file_extension}"
    avatar_path = f"avatars/{avatar_filename}"

    try:
        file_content = await avatar_file.read()
        await s3_client.upload_file(avatar_path, file_content)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload avatar. Please try again later.",
        )

    new_profile = UserProfileModel(
        user_id=user_id,
        first_name=profile_data.first_name,
        last_name=profile_data.last_name,
        gender=profile_data.gender,
        date_of_birth=profile_data.date_of_birth,
        info=profile_data.info,
        avatar=avatar_path,
    )

    try:
        db_session.add(new_profile)
        await db_session.commit()
        await db_session.refresh(new_profile)
    except Exception as e:
        await db_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create profile. Please try again later.",
        )

    response_avatar_url = await s3_client.get_file_url(new_profile.avatar)

    return ProfileResponseSchema(
        id=new_profile.id,
        user_id=new_profile.user_id,
        first_name=new_profile.first_name,
        last_name=new_profile.last_name,
        gender=new_profile.gender,
        date_of_birth=new_profile.date_of_birth,
        info=new_profile.info,
        avatar=response_avatar_url,
    )
