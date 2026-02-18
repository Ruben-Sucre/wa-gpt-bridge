from pydantic import BaseModel, Field


class IncomingWhatsApp(BaseModel):
    from_number: str = Field(..., alias="from")
    text: str

    class Config:
        allow_population_by_field_name = True
