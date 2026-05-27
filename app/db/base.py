from sqlalchemy.orm import declarative_base

from app.models.db_models import Transaction, User, UserBalance  # noqa

Base = declarative_base()
