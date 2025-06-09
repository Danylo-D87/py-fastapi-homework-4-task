from datetime import date
from typing import Literal

from fastapi import UploadFile, Form, File, HTTPException
from pydantic import BaseModel, field_validator, HttpUrl

from validation import (
    validate_name,
    validate_image,
    validate_gender,
    validate_birth_date
)

GENDER_OPTIONS = Literal["man", "woman"]


class ProfileRequestSchema(BaseModel):
    """
    Схема запиту для створення профілю користувача.

    Ця схема описує очікувані дані для запиту на створення профілю.
    Передбачається, що запит буде надсилатися у форматі `multipart/form-data`,
    оскільки він включає файл (`UploadFile`) для аватара.

    Поля:
    - `first_name` (str): Ім'я користувача.
    - `last_name` (str): Прізвище користувача.
    - `gender` (GENDER_OPTIONS): Стать користувача.
    - `date_of_birth` (date): Дата народження користувача.
    - `info` (str): Додаткова інформація про користувача.
    - `avatar` (UploadFile): Файл зображення аватара.
    """
    first_name: str
    last_name: str
    gender: GENDER_OPTIONS
    date_of_birth: date
    info: str
    avatar: UploadFile


    @field_validator('first_name')
    @classmethod
    def validate_first_name_field(cls, v: str) -> str:
        """
        Валідує ім'я користувача.
        Використовує зовнішню функцію `validate_name` для перевірки.
        """
        try:
            validate_name(v)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=f"Invalid first_name: {e}")
        return v.lower()

    @field_validator('last_name')
    @classmethod
    def validate_last_name_field(cls, v: str) -> str:
        """
        Валідує прізвище користувача.
        Використовує зовнішню функцію `validate_name` для перевірки.
        """
        try:
            validate_name(v)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=f"Invalid last_name: {e}")
        return v.lower()

    @field_validator('gender')
    @classmethod
    def validate_gender_field(cls, v: str) -> str:
        """
        Валідує стать користувача.
        Використовує зовнішню функцію `validate_gender` для перевірки.
        """
        try:
            validate_gender(v)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=f"Invalid gender: {e}")
        return v

    @field_validator('date_of_birth')
    @classmethod
    def validate_birth_date_field(cls, v: date) -> date:
        """
        Валідує дату народження користувача.
        Використовує зовнішню функцію `validate_birth_date` для перевірки,
        включаючи перевірку віку (щонайменше 18 років).
        """
        try:
            validate_birth_date(v)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=f"Invalid date_of_birth: {e}")
        return v

    @field_validator('info')
    @classmethod
    def validate_info_field(cls, v: str) -> str:
        """
        Валідує поле "інформація".
        Перевіряє, що поле не є порожнім і не складається лише з пробілів.
        """
        if not v or v.strip() == "":
            raise HTTPException(status_code=422, detail="Info field cannot be empty or contain only spaces.")
        return v

    @field_validator('avatar')
    @classmethod
    def validate_avatar_field(cls, v: UploadFile) -> UploadFile:
        """
        Валідує файл аватара.
        Використовує зовнішню функцію `validate_image` для перевірки типу
        файлу (JPG, JPEG, PNG) та його розміру (не більше 1 МБ).
        """
        try:
            validate_image(v)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=f"Invalid avatar: {e}")
        return v


class ProfileResponseSchema(BaseModel):
    """
    Схема відповіді після успішного створення або отримання профілю користувача.

    Поля:
    - `id` (int): Унікальний ідентифікатор профілю.
    - `user_id` (int): Ідентифікатор користувача, якому належить профіль.
    - `first_name` (str): Ім'я користувача.
    - `last_name` (str): Прізвище користувача.
    - `gender` (str): Стать користувача.
    - `date_of_birth` (date): Дата народження користувача.
    - `info` (str): Додаткова інформація про користувача.
    - `avatar` (HttpUrl): URL до завантаженого аватара.
    """
    id: int
    user_id: int
    first_name: str
    last_name: str
    gender: str
    date_of_birth: date
    info: str
    avatar: HttpUrl
