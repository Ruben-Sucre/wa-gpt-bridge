from pydantic import BaseModel, Field


class IncomingWhatsApp(BaseModel):
    from_number: str = Field(..., alias="from")
    text: str

    model_config = {"populate_by_name": True}
