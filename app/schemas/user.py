from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import Role


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=8, max_length=72)
    role: Role = Role.EMPLOYEE
    department_id: int | None = None
    manager_id: int | None = None


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=120)
    department_id: int | None = None
    manager_id: int | None = None
    phone: str | None = Field(default=None, max_length=30)
    address: str | None = Field(default=None, max_length=200)


class RoleUpdate(BaseModel):
    role: Role


class PasswordChange(BaseModel):
    old_password: str
    new_password: str = Field(min_length=8, max_length=72)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str
    role: Role
    department_id: int | None
    manager_id: int | None
    is_active: bool


class UserDetailRead(UserRead):
    phone: str | None
    address: str | None


class UserWithRelations(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    role: Role
    is_active: bool
    department_name: str | None
    manager_name: str | None
