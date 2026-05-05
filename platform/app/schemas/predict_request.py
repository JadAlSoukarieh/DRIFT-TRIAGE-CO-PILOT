"""POST /predict request body — one field per Bank Marketing feature.

Duration intentionally absent — leaks the target.
Unknown values kept as real categories — they are informative.
"""

from pydantic import BaseModel


class PredictRequest(BaseModel):
    age: float
    job: str
    marital: str
    education: str
    default: str
    housing: str
    loan: str
    contact: str
    month: str
    day_of_week: str
    campaign: float
    pdays: float
    previous: float
    poutcome: str
    emp_var_rate: float
    cons_price_idx: float
    cons_conf_idx: float
    euribor3m: float
    nr_employed: float
