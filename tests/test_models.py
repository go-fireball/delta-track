import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from portfolio_tracker.models import Base, Account, Transaction, AssetTypeEnum, ActionTypeEnum, PositionSnapshot, Position
from datetime import datetime, date
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
            ticker="AAPL",
            asset_type=AssetTypeEnum.STOCK,
            action=ActionTypeEnum.BUY,
            quantity=Decimal("10"),
            price=Decimal("150.00"),
            fees=Decimal("1.00"),
            total_amount=Decimal("1501.00") # 10 * 150 + 1
        )
        self.session.add(stock_tx)
        self.session.commit()

        retrieved_tx = self.session.query(Transaction).filter_by(ticker="AAPL", action=ActionTypeEnum.BUY).first()
        self.assertIsNotNone(retrieved_tx)
        self.assertEqual(retrieved_tx.asset_type, AssetTypeEnum.STOCK)
        self.assertEqual(retrieved_tx.action, ActionTypeEnum.BUY)
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
            ticker="MSFT",
            asset_type=AssetTypeEnum.OPTION,
            action=ActionTypeEnum.SELL_TO_OPEN,
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

        retrieved_tx = self.session.query(Transaction).filter_by(ticker="MSFT", action=ActionTypeEnum.SELL_TO_OPEN).first()
        self.assertIsNotNone(retrieved_tx)
        self.assertEqual(retrieved_tx.asset_type, AssetTypeEnum.OPTION)
        self.assertEqual(retrieved_tx.action, ActionTypeEnum.SELL_TO_OPEN)
        self.assertEqual(retrieved_tx.option_type, "CALL")
        self.assertEqual(retrieved_tx.strike_price, Decimal("300.00"))
        self.assertEqual(retrieved_tx.expiry_date, datetime(2024, 1, 19).date())
        self.assertEqual(retrieved_tx.total_amount, Decimal("1099.50"))
        
    def test_transaction_account_relationship(self):
        # Add a couple of transactions to the test_account
        tx1 = Transaction(account_id=self.test_account.id, transaction_date=datetime(2023,3,1), ticker="TSLA", asset_type=AssetTypeEnum.STOCK, action=ActionTypeEnum.BUY, quantity=Decimal("5"), price=Decimal("200"), fees=Decimal("1"), total_amount=Decimal("1001"))
        tx2 = Transaction(account_id=self.test_account.id, transaction_date=datetime(2023,3,5), ticker="GOOG", asset_type=AssetTypeEnum.STOCK, action=ActionTypeEnum.SELL, quantity=Decimal("2"), price=Decimal("100"), fees=Decimal("1"), total_amount=Decimal("199"))
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

class TestPositionSnapshotModel(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

        # Create a dummy account for positions
        self.test_account = Account(user_friendly_name="Test Account for Pos", account_number="ACC123POS", broker_name="BrokerPos")
        self.session.add(self.test_account)
        self.session.commit()

    def tearDown(self):
        self.session.close()
        Base.metadata.drop_all(self.engine)

    def test_create_stock_position(self):
        stock_pos = PositionSnapshot(
            account_id=self.test_account.id,
            snapshot_date=date(2023, 12, 31),
            ticker="AAPL",
            asset_type=AssetTypeEnum.STOCK,
            quantity=Decimal("100"),
            market_price=Decimal("170.50"),
            market_value=Decimal("17050.00")
        )
        self.session.add(stock_pos)
        self.session.commit()

        retrieved_pos = self.session.query(PositionSnapshot).filter_by(ticker="AAPL", snapshot_date=date(2023,12,31)).first()
        self.assertIsNotNone(retrieved_pos)
        self.assertEqual(retrieved_pos.account_id, self.test_account.id)
        self.assertEqual(retrieved_pos.asset_type, AssetTypeEnum.STOCK)
        self.assertEqual(retrieved_pos.quantity, Decimal("100"))
        self.assertEqual(retrieved_pos.market_price, Decimal("170.50"))
        self.assertEqual(retrieved_pos.market_value, Decimal("17050.00"))

    def test_create_option_position(self):
        option_pos = PositionSnapshot(
            account_id=self.test_account.id,
            snapshot_date=date(2023, 12, 31),
            ticker="MSFT", # Underlying ticker
            asset_type=AssetTypeEnum.OPTION,
            quantity=Decimal("2"), # Number of contracts
            option_type="CALL",
            strike_price=Decimal("300.00"),
            expiry_date=date(2024, 3, 15),
            market_price=Decimal("10.25"), # Price of one option contract (per share)
            market_value=Decimal("2050.00") # 2 contracts * 100 shares/contract * 10.25
        )
        self.session.add(option_pos)
        self.session.commit()

        retrieved_pos = self.session.query(PositionSnapshot).filter_by(ticker="MSFT", option_type="CALL", snapshot_date=date(2023,12,31)).first()
        self.assertIsNotNone(retrieved_pos)
        self.assertEqual(retrieved_pos.asset_type, AssetTypeEnum.OPTION)
        self.assertEqual(retrieved_pos.quantity, Decimal("2"))
        self.assertEqual(retrieved_pos.strike_price, Decimal("300.00"))
        self.assertEqual(retrieved_pos.expiry_date, date(2024, 3, 15))
        self.assertEqual(retrieved_pos.market_price, Decimal("10.25"))
        self.assertEqual(retrieved_pos.market_value, Decimal("2050.00"))

    def test_unique_constraint_position(self):
        # Create an initial position
        pos1 = PositionSnapshot(
            account_id=self.test_account.id, snapshot_date=date(2024, 1, 1),
            ticker="GOOG", asset_type=AssetTypeEnum.STOCK, quantity=Decimal("10"),
            market_price=Decimal("140"), market_value=Decimal("1400")
        )
        self.session.add(pos1)
        self.session.commit()

        # Attempt to create an identical position (should fail due to unique constraint)
        # For stock positions, option_type, strike_price, expiry_date are None.
        # The unique constraint uq_position_snapshot includes these nullable fields.
        pos2 = PositionSnapshot(
            account_id=self.test_account.id, snapshot_date=date(2024, 1, 1),
            ticker="GOOG", asset_type=AssetTypeEnum.STOCK, quantity=Decimal("20"), # Different quantity
            market_price=Decimal("141"), market_value=Decimal("2820")
        )
        self.session.add(pos2)
        from sqlalchemy.exc import IntegrityError
        with self.assertRaises(IntegrityError):
            self.session.commit()
        self.session.rollback() # Rollback after expected error

        # Clean up the first stock position before testing option uniqueness
        self.session.delete(pos1)
        self.session.commit()

        option_pos1 = PositionSnapshot(
            account_id=self.test_account.id, snapshot_date=date(2024,1,1), ticker="GOOG",
            asset_type=AssetTypeEnum.OPTION, quantity=Decimal("1"), option_type="CALL",
            strike_price=Decimal("150"), expiry_date=date(2024,2,16),
            market_price=Decimal("5"), market_value=Decimal("500")
        )
        self.session.add(option_pos1)
        self.session.commit()
       
        # Attempt to create an identical option position (should fail)
        option_pos1_duplicate = PositionSnapshot(
            account_id=self.test_account.id, snapshot_date=date(2024,1,1), ticker="GOOG",
            asset_type=AssetTypeEnum.OPTION, quantity=Decimal("2"), option_type="CALL", # Diff quantity
            strike_price=Decimal("150"), expiry_date=date(2024,2,16),
            market_price=Decimal("6"), market_value=Decimal("1200")
        )
        self.session.add(option_pos1_duplicate)
        with self.assertRaises(IntegrityError):
            self.session.commit()
        self.session.rollback()

        # Attempt to create an option position for the same underlying but different strike (should succeed)
        option_pos2_different_strike = PositionSnapshot(
            account_id=self.test_account.id, snapshot_date=date(2024,1,1), ticker="GOOG",
            asset_type=AssetTypeEnum.OPTION, quantity=Decimal("1"), option_type="CALL",
            strike_price=Decimal("155"), expiry_date=date(2024,2,16), # Different strike
            market_price=Decimal("3"), market_value=Decimal("300")
        )
        self.session.add(option_pos2_different_strike)
        self.session.commit() 
        self.assertIsNotNone(self.session.query(PositionSnapshot).filter_by(strike_price=Decimal("155")).first())

class TestLivePositionModel(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

        self.test_account = Account(user_friendly_name="Test Account for LivePos", account_number="ACC123LIVE", broker_name="BrokerLive")
        self.session.add(self.test_account)
        self.session.commit()

    def tearDown(self):
        self.session.close()
        Base.metadata.drop_all(self.engine)

    def test_create_live_stock_position(self):
        live_stock_pos = Position( # This is the new Position model
            account_id=self.test_account.id,
            ticker="NVDA",
            asset_type=AssetTypeEnum.STOCK,
            quantity=Decimal("50")
        )
        self.session.add(live_stock_pos)
        self.session.commit()

        retrieved_pos = self.session.query(Position).filter_by(ticker="NVDA", account_id=self.test_account.id).first()
        self.assertIsNotNone(retrieved_pos)
        self.assertEqual(retrieved_pos.asset_type, AssetTypeEnum.STOCK)
        self.assertEqual(retrieved_pos.quantity, Decimal("50"))
        self.assertIsNone(retrieved_pos.strike_price) # Ensure option fields are None

    def test_create_live_option_position(self):
        live_option_pos = Position(
            account_id=self.test_account.id,
            ticker="AMD", 
            asset_type=AssetTypeEnum.OPTION,
            quantity=Decimal("5"), # Number of contracts
            option_type="PUT",
            strike_price=Decimal("150.00"),
            expiry_date=date(2024, 6, 21)
        )
        self.session.add(live_option_pos)
        self.session.commit()

        retrieved_pos = self.session.query(Position).filter_by(ticker="AMD", option_type="PUT", account_id=self.test_account.id).first()
        self.assertIsNotNone(retrieved_pos)
        self.assertEqual(retrieved_pos.asset_type, AssetTypeEnum.OPTION)
        self.assertEqual(retrieved_pos.quantity, Decimal("5"))
        self.assertEqual(retrieved_pos.strike_price, Decimal("150.00"))
        self.assertEqual(retrieved_pos.expiry_date, date(2024, 6, 21))

    def test_unique_constraint_live_position(self):
        # Initial live stock position
        pos1 = Position(account_id=self.test_account.id, ticker="INTC", asset_type=AssetTypeEnum.STOCK, quantity=Decimal("200"))
        self.session.add(pos1)
        self.session.commit()

        # Identical live stock position (should fail)
        pos2_stock_dup = Position(account_id=self.test_account.id, ticker="INTC", asset_type=AssetTypeEnum.STOCK, quantity=Decimal("25"))
        self.session.add(pos2_stock_dup)
        from sqlalchemy.exc import IntegrityError
        with self.assertRaises(IntegrityError):
            self.session.commit()
        self.session.rollback()

        # Initial live option position
        pos_opt1 = Position(
            account_id=self.test_account.id, ticker="SPY", asset_type=AssetTypeEnum.OPTION,
            quantity=Decimal("10"), option_type="CALL", strike_price=Decimal("500"), expiry_date=date(2024,12,20)
        )
        self.session.add(pos_opt1)
        self.session.commit()
        
        # Identical live option position (should fail)
        pos_opt2_dup = Position(
            account_id=self.test_account.id, ticker="SPY", asset_type=AssetTypeEnum.OPTION,
            quantity=Decimal("12"), option_type="CALL", strike_price=Decimal("500"), expiry_date=date(2024,12,20)
        )
        self.session.add(pos_opt2_dup)
        with self.assertRaises(IntegrityError):
            self.session.commit()
        self.session.rollback()

        # Live option position, different strike (should succeed)
        pos_opt3_diff = Position(
            account_id=self.test_account.id, ticker="SPY", asset_type=AssetTypeEnum.OPTION,
            quantity=Decimal("15"), option_type="CALL", strike_price=Decimal("505"), expiry_date=date(2024,12,20)
        )
        self.session.add(pos_opt3_diff)
        self.session.commit()
        self.assertIsNotNone(self.session.query(Position).filter_by(strike_price=Decimal("505")).first())
