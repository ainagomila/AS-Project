import hmac
import dotenv
from typing import Annotated

from fastapi import FastAPI
from pydantic import BeforeValidator, BaseModel

from app.config import settings
from app.field_validators import is_valid_PAN, is_valid_CVV, is_valid_date

class Card(BaseModel):
    PAN: Annotated[str, BeforeValidator(is_valid_PAN)]
    CVV: Annotated[str, BeforeValidator(is_valid_CVV)]
    expiration_date: Annotated[str, BeforeValidator(is_valid_date)]

app = FastAPI()

@app.post("/verify")
def verify_card(card: Card):
    msg = f"{card.PAN}E{card.expiration_date}".encode()
    key = dotenv.get_key(".env", "KEY")
    if key is None:
        raise FileNotFoundError("No key found")
    key = settings.secret_key.get_secret_value().encode()
    tag = hmac.new(key, msg, "sha256").digest()
    cvv = f"{int.from_bytes(tag, 'big') % 1000:03d}"
    return hmac.compare_digest(cvv, card.CVV)
