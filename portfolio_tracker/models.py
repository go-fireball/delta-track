from sqlalchemy import Column, Integer, String, DateTime, Numeric, Text, ForeignKey, Date
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class Account(Base):
    __tablename__ = 'accounts'

    id = Column(Integer, primary_key=True)
    user_friendly_name = Column(String)
    account_number = Column(String, unique=True, nullable=False)
    broker_name = Column(String)

    transactions = relationship("Transaction", back_populates="account", order_by="Transaction.transaction_date", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Account(user_friendly_name='{self.user_friendly_name}', account_number='{self.account_number}')>"

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey('accounts.id'), nullable=False)
    transaction_date = Column(DateTime, nullable=False)
    ticker = Column(String, nullable=False, index=True)
    asset_type = Column(String, nullable=False)  # E.g., 'STOCK', 'OPTION', 'ETF', 'MUTUAL_FUND'
    action = Column(String, nullable=False)  # E.g., 'BUY', 'SELL', 'SELL_TO_OPEN', 'BUY_TO_OPEN'
    quantity = Column(Numeric(19, 4), nullable=False)
    price = Column(Numeric(19, 4), nullable=False)
    fees = Column(Numeric(10, 2), nullable=False, default=0.0)
    total_amount = Column(Numeric(19, 2), nullable=False) # Should typically be (quantity * price) +/- fees depending on action
    notes = Column(Text, nullable=True)

    # Option-specific fields
    option_type = Column(String, nullable=True)  # 'CALL' or 'PUT'
    strike_price = Column(Numeric(19, 4), nullable=True)
    expiry_date = Column(Date, nullable=True) # Changed to Date as time component is usually not needed for expiry

    account = relationship("Account", back_populates="transactions")

    def __repr__(self):
        return f"<Transaction(id={self.id}, ticker='{self.ticker}', action='{self.action}', quantity={self.quantity}, price={self.price})>"
