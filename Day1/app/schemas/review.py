from datetime import datetime
from pydantic import BaseModel, Field


class ReviewCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5, examples=[5], description="Rating from 1 to 5")    #... means required field
    comment: str = Field(..., min_length=1, examples=["Masterpiece storytelling and visual effects."])
    user_id: int = Field(default=1, examples=[1])   #default value is 1 here


class ReviewUpdate(BaseModel):   
    rating: int | None = Field(None, ge=1, le=5, examples=[4])                 #default value is None here
    comment: str | None = Field(None, examples=["Updated review comments."])


class ReviewResponse(BaseModel):
    id: int
    film_id: int
    user_id: int
    rating: int
    comment: str
    created_at: datetime
