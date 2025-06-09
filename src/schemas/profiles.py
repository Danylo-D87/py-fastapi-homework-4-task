from datetime import date
from fastapi import UploadFile, Form, File, HTTPException
from pydantic import BaseModel, field_validator, HttpUrl

from validation import (
    validate_name,
    validate_image,
    validate_gender,
    validate_birth_date,
)
from database.models.accounts import GenderEnum


class ProfileRequestSchema(BaseModel):
    """
    Request schema for creating a user profile.

    This schema describes the expected data for a profile creation request.
    It is assumed that the request will be sent in `multipart/form-data` format,
    as it includes a file (`UploadFile`) for the avatar.

    Fields:
    - `first_name` (str): User's first name.
    - `last_name` (str): User's last name.
    - `gender` (GENDER_OPTIONS): User's gender.
    - `date_of_birth` (date): User's date of birth.
    - `info` (str): Additional information about the user.
    - `avatar` (UploadFile): Avatar image file.
    """

    first_name: str
    last_name: str
    gender: GenderEnum
    date_of_birth: date
    info: str
    avatar: UploadFile

    @field_validator("first_name")
    @classmethod
    def validate_first_name_field(cls, v: str) -> str:
        """
        Validates the user's first name.
        Uses the external `validate_name` function for validation.
        """
        try:
            validate_name(v)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=f"Invalid first_name: {e}")
        return v.lower()

    @field_validator("last_name")
    @classmethod
    def validate_last_name_field(cls, v: str) -> str:
        """
        Validates the user's last name.
        Uses the external `validate_name` function for validation.
        """
        try:
            validate_name(v)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=f"Invalid last_name: {e}")
        return v.lower()

    @field_validator("gender")
    @classmethod
    def validate_gender_field(cls, v: str) -> str:
        """
        Validates the user's gender.
        Uses the external `validate_gender` function for validation.
        """
        try:
            validate_gender(v)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=f"Invalid gender: {e}")
        return v

    @field_validator("date_of_birth")
    @classmethod
    def validate_birth_date_field(cls, v: date) -> date:
        """
        Validates the user's date of birth.
        Uses the external `validate_birth_date` function for validation,
        including age verification (at least 18 years old).
        """
        try:
            validate_birth_date(v)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=f"Invalid date_of_birth: {e}")
        return v

    @field_validator("info")
    @classmethod
    def validate_info_field(cls, v: str) -> str:
        """
        Validates the "info" field.
        Checks that the field is not empty and does not consist only of spaces.
        """
        if not v or v.strip() == "":
            raise HTTPException(
                status_code=422,
                detail="Info field cannot be empty or contain only spaces.",
            )
        return v

    @field_validator("avatar")
    @classmethod
    def validate_avatar_field(cls, v: UploadFile) -> UploadFile:
        """
        Validates the avatar file.
        Uses the external `validate_image` function to check the file type
        (JPG, JPEG, PNG) and its size (not exceeding 1 MB).
        """
        try:
            validate_image(v)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=f"Invalid avatar: {e}")
        return v


class ProfileResponseSchema(BaseModel):
    """
    Response schema after successful creation or retrieval of a user profile.

    Fields:
    - `id` (int): Unique profile identifier.
    - `user_id` (int): ID of the user to whom the profile belongs.
    - `first_name` (str): User's first name.
    - `last_name` (str): User's last name.
    - `gender` (str): User's gender.
    - `date_of_birth` (date): User's date of birth.
    - `info` (str): Additional information about the user.
    - `avatar` (HttpUrl): URL to the uploaded avatar.
    """

    id: int
    user_id: int
    first_name: str
    last_name: str
    gender: str
    date_of_birth: date
    info: str
    avatar: HttpUrl
