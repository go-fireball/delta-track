import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from portfolio_tracker.models import Base, Account

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

if __name__ == '__main__':
    unittest.main()
