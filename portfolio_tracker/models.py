import enum
from datetime import date # Added for Index
from decimal import Decimal # Added for Index, though already present via InvalidOperation
from sqlalchemy import Column, Integer, String, DateTime, Numeric, Text, ForeignKey, Date, Enum as DBEnum, Index, func # Added Index, func
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.schema import UniqueConstraint

class AssetTypeEnum(enum.Enum):
    STOCK = "STOCK"
    OPTION = "OPTION"
    ETF = "ETF"
    MUTUAL_FUND = "MUTUAL_FUND"
    CASH = "CASH"

class ActionTypeEnum(enum.Enum):
    BUY = "BUY"
    SELL = "SELL"
    BUY_TO_OPEN = "BUY_TO_OPEN"
    SELL_TO_OPEN = "SELL_TO_OPEN"
    BUY_TO_CLOSE = "BUY_TO_CLOSE"
    SELL_TO_CLOSE = "SELL_TO_CLOSE"
    DIVIDEND = "DIVIDEND" # Cash received
    FEE = "FEE" # A specific fee transaction
    INTEREST = "INTEREST" # Interest received or paid
    EXERCISE = "EXERCISE" # Option exercised
    ASSIGNMENT = "ASSIGNMENT" # Option assignment
    EXPIRATION = "EXPIRATION" # Option expired worthless
    # Consider also: STOCK_DIVIDEND, SPLIT, MERGER, etc. for corporate actions later

Base = declarative_base()

class Account(Base):
    __tablename__ = 'accounts'

    id = Column(Integer, primary_key=True)
    user_friendly_name = Column(String)
    account_number = Column(String, unique=True, nullable=False)
    broker_name = Column(String)

    transactions = relationship("Transaction", back_populates="account", order_by="Transaction.transaction_date", cascade="all, delete-orphan")
    daily_position_snapshots = relationship("DailyPositionSnapshot", back_populates="account", order_by="DailyPositionSnapshot.snapshot_date", cascade="all, delete-orphan")
    live_positions = relationship("LivePosition", back_populates="account", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Account(user_friendly_name='{self.user_friendly_name}', account_number='{self.account_number}')>"

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey('accounts.id'), nullable=False)
    transaction_date = Column(DateTime, nullable=False)
    ticker = Column(String, nullable=False, index=True)
    asset_type = Column(DBEnum(AssetTypeEnum), nullable=False)
    action = Column(DBEnum(ActionTypeEnum), nullable=False)
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
        return f"<Transaction(id={self.id}, ticker='{self.ticker}', action='{self.action.value if self.action else None}', quantity={self.quantity}, price={self.price})>"

class DailyPositionSnapshot(Base):
    __tablename__ = "daily_position_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey('accounts.id'), nullable=False)
    snapshot_date = Column(Date, nullable=False, index=True)

    ticker = Column(String, nullable=False, index=True) # Underlying ticker
    asset_type = Column(DBEnum(AssetTypeEnum), nullable=False) # Using the Enum defined earlier

    quantity = Column(Numeric(19, 4), nullable=False)

    # Option-specific details (nullable if not an option position)
    # For options, 'ticker' is the underlying. These fields specify the contract.
    option_type = Column(String, nullable=True)  # 'CALL' or 'PUT'
    strike_price = Column(Numeric(19, 4), nullable=True)
    expiry_date = Column(Date, nullable=True)

    market_price = Column(Numeric(19, 4), nullable=True) # Price per unit on snapshot_date
    market_value = Column(Numeric(19, 2), nullable=True) # Total value of this position on snapshot_date

    # Relationship (will be completed on Account model later)
    account = relationship("Account", back_populates="daily_position_snapshots")

    # Unique constraint: one entry per asset per account per day
    # For options, the combination of ticker, option_type, strike_price, and expiry_date defines the specific contract
    # __table_args__ = (
    #     UniqueConstraint('account_id', 'snapshot_date', 'ticker', 
    #                      name='uq_position_snapshot_simplified'),
    # )

    def __repr__(self):
        return (f"<DailyPositionSnapshot(date='{self.snapshot_date}', ticker='{self.ticker}', "
                f"asset_type='{self.asset_type.value if self.asset_type else None}', quantity={self.quantity}, " # Access .value for Enum
                f"market_value={self.market_value})>")

Index('uq_daily_snapshot_idx', 
      DailyPositionSnapshot.account_id, 
      DailyPositionSnapshot.snapshot_date,
      DailyPositionSnapshot.ticker,
      DailyPositionSnapshot.asset_type,
      func.coalesce(DailyPositionSnapshot.option_type, ''), 
      func.coalesce(DailyPositionSnapshot.strike_price, Decimal('0.0')), 
      func.coalesce(DailyPositionSnapshot.expiry_date, date(1900, 1, 1)),
      unique=True)

class LivePosition(Base):
    __tablename__ = "live_positions" # This is for the live view of current holdings

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey('accounts.id'), nullable=False)
    
    ticker = Column(String, nullable=False, index=True) # Underlying ticker
    asset_type = Column(DBEnum(AssetTypeEnum), nullable=False)
    quantity = Column(Numeric(19, 4), nullable=False) # Current held quantity

    # Option-specific details (nullable if not an option position)
    option_type = Column(String, nullable=True)  # 'CALL' or 'PUT'
    strike_price = Column(Numeric(19, 4), nullable=True)
    expiry_date = Column(Date, nullable=True)

    avg_cost_basis = Column(Numeric(19, 4), nullable=True) # Average cost per unit
    
    # No snapshot_date or market_value fields in this live position table

    # Relationship to Account (back_populates will be set on Account model later)
    account = relationship("Account", back_populates="live_positions")

    # Unique constraint: one entry per unique currently held asset per account
    # __table_args__ = (
    #     UniqueConstraint('account_id', 'ticker', 'asset_type', 
    #                      'option_type', 'strike_price', 'expiry_date', 
    #                      name='uq_live_position'),
    # )

    def __repr__(self):
        return (f"<LivePosition(ticker='{self.ticker}', "
                f"asset_type='{self.asset_type.value if self.asset_type else None}', quantity={self.quantity}, "
                f"avg_cost_basis={self.avg_cost_basis})>")

Index('uq_live_pos_idx', 
      LivePosition.account_id, 
      LivePosition.ticker,
      LivePosition.asset_type,
      func.coalesce(LivePosition.option_type, ''), 
      func.coalesce(LivePosition.strike_price, Decimal('0.0')), 
      func.coalesce(LivePosition.expiry_date, date(1900, 1, 1)),
      unique=True)
