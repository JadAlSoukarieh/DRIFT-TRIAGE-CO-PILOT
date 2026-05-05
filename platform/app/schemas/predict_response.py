"""POST /predict response — final prediction after thresholding."""

from pydantic import BaseModel


class PredictResponse(BaseModel):
    prediction: int
    probability: float
