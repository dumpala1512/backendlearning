from pydantic import BaseModel, ConfigDict


class AppBaseModel(BaseModel):
    """
    Shared base model with unified Pydantic v2 configuration:
    - strict: Enforces strict type validation (e.g. rejects rating="10")
    - from_attributes: Enables model_validate(obj) from ORM/dataclass objects
    - populate_by_name: Allows both field name and alias population
    - str_strip_whitespace: Automatically strips leading/trailing whitespace
    """

    model_config = ConfigDict(
        strict=True,
        from_attributes=True,
        populate_by_name=True,
        str_strip_whitespace=True,
    )
