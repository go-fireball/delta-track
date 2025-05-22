from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Account(Base):
    __tablename__ = 'accounts'

    id = Column(Integer, primary_key=True)
    user_friendly_name = Column(String)
    account_number = Column(String, unique=True, nullable=False)
    broker_name = Column(String)

    def __repr__(self):
        return f"<Account(user_friendly_name='{self.user_friendly_name}', account_number='{self.account_number}')>"
