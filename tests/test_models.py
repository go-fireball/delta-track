import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from portfolio_tracker.models import Base, Account, Transaction
from datetime import datetime
from decimal import Decimal

class TestAccountModel(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    def tearDown(self):
        self.session.close()
        Base.metadata.drop_all(self.engine)

    def test_create_and_retrieve_account(self):
        new_account = Account(
            user_friendly_name="Test Account",
            account_number="12345XYZ",
            broker_name="TestBroker"
        )
        self.session.add(new_account)
        self.session.commit()

        retrieved_account = self.session.query(Account).filter_by(account_number="12345XYZ").first()

        self.assertIsNotNone(retrieved_account)
        self.assertEqual(retrieved_account.user_friendly_name, "Test Account")
        self.assertEqual(retrieved_account.broker_name, "TestBroker")

class TestTransactionModel(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

        # Create a dummy account for transactions
        self.test_account = Account(user_friendly_name="Test Account for Trans", account_number="ACC123TRANS", broker_name="BrokerTrans")
        self.session.add(self.test_account)
        self.session.commit()

    def tearDown(self):
        self.session.close()
        Base.metadata.drop_all(self.engine)

    def test_create_stock_buy_transaction(self):
        stock_tx = Transaction(
            account_id=self.test_account.id,
            transaction_date=datetime(2023, 1, 15, 10, 30, 0),
            symbol="AAPL",
            asset_type="STOCK",
            action="BUY",
            quantity=Decimal("10"),
            price=Decimal("150.00"),
            fees=Decimal("1.00"),
            total_amount=Decimal("1501.00") # 10 * 150 + 1
        )
        self.session.add(stock_tx)
        self.session.commit()

        retrieved_tx = self.session.query(Transaction).filter_by(symbol="AAPL", action="BUY").first()
        self.assertIsNotNone(retrieved_tx)
        self.assertEqual(retrieved_tx.account_id, self.test_account.id)
        self.assertEqual(retrieved_tx.quantity, Decimal("10"))
        self.assertEqual(retrieved_tx.price, Decimal("150.00"))
        self.assertEqual(retrieved_tx.fees, Decimal("1.00"))
        self.assertEqual(retrieved_tx.total_amount, Decimal("1501.00"))
        self.assertEqual(retrieved_tx.account.account_number, "ACC123TRANS")

    def test_create_option_sell_to_open_transaction(self):
        option_tx = Transaction(
            account_id=self.test_account.id,
            transaction_date=datetime(2023, 2, 10, 14, 0, 0),
            symbol="MSFT",
            asset_type="OPTION",
            action="SELL_TO_OPEN",
            quantity=Decimal("2"), # Number of contracts
            price=Decimal("5.50"),  # Price per share/unit for the option premium
            fees=Decimal("0.50"),
            total_amount=Decimal("1099.50"), # 2 contracts * 100 shares/contract * 5.50 premium/share - 0.50 fee
            option_type="CALL",
            strike_price=Decimal("300.00"),
            expiry_date=datetime(2024, 1, 19).date() # Ensure this is a date object
        )
        # Note: total_amount for options often calculated as quantity * price * multiplier (e.g., 100 for US stock options) +/- fees
        # For SELL_TO_OPEN, total_amount would be (quantity * price * 100) - fees
        # The example total_amount=Decimal("1099.50") assumes a multiplier of 100. (2 * 5.50 * 100) - 0.50 = 1100 - 0.50 = 1099.50
        self.session.add(option_tx)
        self.session.commit()

        retrieved_tx = self.session.query(Transaction).filter_by(symbol="MSFT", action="SELL_TO_OPEN").first()
        self.assertIsNotNone(retrieved_tx)
        self.assertEqual(retrieved_tx.asset_type, "OPTION")
        self.assertEqual(retrieved_tx.option_type, "CALL")
        self.assertEqual(retrieved_tx.strike_price, Decimal("300.00"))
        self.assertEqual(retrieved_tx.expiry_date, datetime(2024, 1, 19).date())
        self.assertEqual(retrieved_tx.total_amount, Decimal("1099.50"))
        
    def test_transaction_account_relationship(self):
        # Add a couple of transactions to the test_account
        tx1 = Transaction(account_id=self.test_account.id, transaction_date=datetime(2023,3,1), symbol="TSLA", asset_type="STOCK", action="BUY", quantity=Decimal("5"), price=Decimal("200"), fees=Decimal("1"), total_amount=Decimal("1001"))
        tx2 = Transaction(account_id=self.test_account.id, transaction_date=datetime(2023,3,5), symbol="GOOG", asset_type="STOCK", action="SELL", quantity=Decimal("2"), price=Decimal("100"), fees=Decimal("1"), total_amount=Decimal("199"))
        self.session.add_all([tx1, tx2])
        self.session.commit()

        # Retrieve the account and check its transactions
        retrieved_account = self.session.query(Account).filter_by(account_number="ACC123TRANS").first()
        self.assertIsNotNone(retrieved_account)
        self.assertEqual(len(retrieved_account.transactions), 2)
        self.assertIn(tx1, retrieved_account.transactions)
        self.assertIn(tx2, retrieved_account.transactions)

if __name__ == '__main__':
    unittest.main()
