# portfolio_tracker/importing/services/transaction_import_service.py

from sqlalchemy.orm import Session
from decimal import Decimal

# Assuming models are in portfolio_tracker/models.py
# and this file is in portfolio_tracker/importing/services/
from ....models import Transaction, Account, ActionTypeEnum, AssetTypeEnum

class TransactionImportService:
    def __init__(self, session: Session):
        if session is None:
            raise ValueError("SQLAlchemy session cannot be None")
        self.session = session

    def import_transactions(self, account_id: int, parsed_transactions_data: list[dict]):
        if not account_id:
            raise ValueError("Account ID must be provided.")
        
        account = self.session.query(Account).filter(Account.id == account_id).first()
        if not account:
            raise ValueError(f"Account with ID {account_id} not found.")

        if not parsed_transactions_data:
            # print("No transactions to import.")
            return []

        created_transactions = []
        skipped_count = 0

        for tx_data in parsed_transactions_data:
            try:
                # Ensure all required Decimal fields are present and valid, or default to 0
                quantity = tx_data.get('quantity')
                price = tx_data.get('price')
                fees = tx_data.get('fees')
                total_amount = tx_data.get('total_amount')
                option_strike = tx_data.get('option_strike')

                # Create the Transaction object
                new_transaction = Transaction(
                    account_id=account_id,
                    transaction_date=tx_data['transaction_date'], # Assuming this is already a date/datetime object
                    ticker=tx_data['ticker'],
                    asset_type=tx_data['asset_type'], # Assuming this is already an Enum member
                    action=tx_data['action'],         # Assuming this is already an Enum member
                    quantity=quantity if isinstance(quantity, Decimal) else Decimal(0),
                    price=price if isinstance(price, Decimal) else Decimal(0),
                    fees=fees if isinstance(fees, Decimal) else Decimal(0),
                    total_amount=total_amount if isinstance(total_amount, Decimal) else Decimal(0),
                    notes=tx_data.get('raw_description'), # Optional: or any other notes field
                    option_type=tx_data.get('option_type'), # String, nullable
                    strike_price=option_strike if isinstance(option_strike, Decimal) else None, # Decimal, nullable
                    expiry_date=tx_data.get('option_expiry') # Date object, nullable
                )
                
                # Basic validation for key fields for certain actions
                if new_transaction.action in [ActionTypeEnum.BUY, ActionTypeEnum.SELL, ActionTypeEnum.BUY_TO_OPEN, ActionTypeEnum.SELL_TO_OPEN, ActionTypeEnum.BUY_TO_CLOSE, ActionTypeEnum.SELL_TO_CLOSE]:
                    if new_transaction.quantity == Decimal(0) and new_transaction.asset_type != AssetTypeEnum.CASH: # Allow 0 quantity for cash dividends/interest for now
                        # print(f"Skipping transaction due to zero quantity for action {new_transaction.action}: {tx_data}")
                        skipped_count += 1
                        continue
                
                # For options, ensure key fields are present
                if new_transaction.asset_type == AssetTypeEnum.OPTION:
                    if not new_transaction.option_type or not new_transaction.strike_price or not new_transaction.expiry_date:
                        # print(f"Skipping option transaction due to missing option details: {tx_data}")
                        skipped_count += 1
                        continue
                
                self.session.add(new_transaction)
                created_transactions.append(new_transaction)

            except KeyError as e:
                # print(f"Skipping transaction due to missing key: {e}. Data: {tx_data}")
                skipped_count += 1
                continue
            except Exception as e:
                # print(f"Error creating transaction object: {e}. Data: {tx_data}")
                skipped_count += 1
                continue
        
        if skipped_count > 0:
            # print(f"Skipped {skipped_count} transactions due to missing data or errors.")
            pass

        if not created_transactions:
            # print("No valid transactions were created from the provided data.")
            return []

        try:
            self.session.commit()
            # print(f"Successfully committed {len(created_transactions)} transactions.")
            return created_transactions
        except Exception as e:
            self.session.rollback()
            # print(f"Error committing transactions to the database: {e}")
            # Consider how to handle partial commits or already existing transactions if needed
            # For now, we rollback all if any single commit fails.
            raise # Re-raise the exception to signal failure

if __name__ == '__main__':
    # This is a placeholder for potential direct testing of the service.
    # In a real scenario, you'd mock the SQLAlchemy session and models.
    print("TransactionImportService defined. To test, instantiate with a SQLAlchemy session and call import_transactions.")

    # Example (conceptual - requires a live or mocked session and account):
    # from sqlalchemy import create_engine
    # from sqlalchemy.orm import sessionmaker
    # from portfolio_tracker.models import Base # Assuming Base is accessible
    #
    # # Setup a dummy in-memory database for example
    # engine = create_engine("sqlite:///:memory:")
    # Base.metadata.create_all(engine) # Create tables
    # SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    # db_session = SessionLocal()
    #
    # # Create a dummy account for testing
    # test_account = Account(user_friendly_name="Test Import Account", account_number="IMPORT123", broker_name="TestBroker")
    # db_session.add(test_account)
    # db_session.commit()
    # db_session.refresh(test_account)
    #
    # service = TransactionImportService(session=db_session)
    #
    # sample_parsed_data = [
    #     {
    #         "transaction_date": datetime(2023, 1, 15).date(),
    #         "action": ActionTypeEnum.BUY,
    #         "asset_type": AssetTypeEnum.STOCK,
    #         "ticker": "AAPL",
    #         "quantity": Decimal("10"),
    #         "price": Decimal("150.00"),
    #         "fees": Decimal("1.00"),
    #         "total_amount": Decimal("-1501.00"),
    #         "raw_description": "Bought AAPL shares",
    #         "option_type": None, "option_strike": None, "option_expiry": None
    #     },
    #     {
    #         "transaction_date": datetime(2023, 1, 16).date(),
    #         "action": ActionTypeEnum.SELL_TO_OPEN,
    #         "asset_type": AssetTypeEnum.OPTION,
    #         "ticker": "MSFT",
    #         "quantity": Decimal("2"),
    #         "price": Decimal("5.50"), # Premium per share
    #         "fees": Decimal("0.65"),
    #         "total_amount": Decimal("1099.35"), # (2 * 100 * 5.50) - 0.65
    #         "raw_description": "Sold MSFT Calls",
    #         "option_type": "CALL", "option_strike": Decimal("300"), "option_expiry": datetime(2024,1,19).date()
    #     }
    # ]
    #
    # try:
    #     imported_txns = service.import_transactions(account_id=test_account.id, parsed_transactions_data=sample_parsed_data)
    #     print(f"Imported {len(imported_txns)} transactions for account {test_account.id}.")
    #     for txn in imported_txns:
    #         print(f"  ID: {txn.id}, Ticker: {txn.ticker}, Action: {txn.action.value}, Amount: {txn.total_amount}")
    # except ValueError as ve:
    #     print(f"ValueError during import: {ve}")
    # except Exception as e:
    #     print(f"An error occurred: {e}")
    # finally:
    #     db_session.close()
