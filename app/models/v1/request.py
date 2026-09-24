from pydantic import BaseModel, ConfigDict, Field

class APIModel(BaseModel):
    model_config = ConfigDict(extra='forbid')

class UploadInit(APIModel):
    filename: str = Field(min_length=1, max_length=255)
    total_size: int = Field(gt=0)
    mimetype: str = Field(min_length=1, max_length=100)
    chunk_size: int = Field(gt=0)
