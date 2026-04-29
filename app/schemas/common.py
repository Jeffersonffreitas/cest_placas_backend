from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)


class ORMBaseSchema(BaseSchema):
    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)

