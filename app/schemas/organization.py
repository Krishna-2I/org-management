from pydantic import BaseModel, ConfigDict, EmailStr, Field


class OrganizationRegister(BaseModel):
    org_name: str = Field(min_length=1, max_length=120)
    owner_name: str = Field(min_length=1, max_length=120)
    owner_email: EmailStr
    password: str = Field(min_length=8, max_length=72)


class OrganizationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
