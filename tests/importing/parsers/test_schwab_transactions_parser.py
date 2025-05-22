# tests/importing/parsers/test_schwab_transactions_parser.py

import unittest
from datetime import date
from decimal import Decimal

from portfolio_tracker.models import ActionTypeEnum, AssetTypeEnum
from portfolio_tracker.importing.parsers.schwab_transactions_parser import parse_schwab_transactions

class TestSchwabTransactionsParser(unittest.TestCase):

    def test_parse_stock_buy(self):
        csv_content = """Date,Action,Symbol,Description,Quantity,Price,Fees & Comm,Amount
05/19/2025,Buy,NVDA,NVIDIA CORP,100,$135.50,,($13,550.00)"""
        parsed = parse_schwab_transactions(csv_content)
        self.assertEqual(len(parsed), 1)
        tx = parsed[0]
        self.assertEqual(tx['transaction_date'], date(2025, 5, 19))
        self.assertEqual(tx['action'], ActionTypeEnum.BUY)
        self.assertEqual(tx['asset_type'], AssetTypeEnum.STOCK)
        self.assertEqual(tx['ticker'], "NVDA")
        self.assertEqual(tx['quantity'], Decimal("100"))
        self.assertEqual(tx['price'], Decimal("135.50"))
        self.assertEqual(tx['fees'], Decimal("0"))
        self.assertEqual(tx['total_amount'], Decimal("-13550.00"))
        self.assertIsNone(tx['option_type'])

    def test_parse_option_sell_to_open_symbol_format(self):
        csv_content = """Date,Action,Symbol,Description,Quantity,Price,Fees & Comm,Amount
05/15/2025,Sell to Open,MSFT 12/18/2026 400.00 P,"PUT MICROSOFT CORP $400 EXP 12/18/26",3,$27.18,$1.98,$8,152.02"""
        parsed = parse_schwab_transactions(csv_content)
        self.assertEqual(len(parsed), 1)
        tx = parsed[0]
        self.assertEqual(tx['transaction_date'], date(2025, 5, 15))
        self.assertEqual(tx['action'], ActionTypeEnum.SELL_TO_OPEN)
        self.assertEqual(tx['asset_type'], AssetTypeEnum.OPTION)
        self.assertEqual(tx['ticker'], "MSFT")
        self.assertEqual(tx['quantity'], Decimal("3"))
        self.assertEqual(tx['price'], Decimal("27.18"))
        self.assertEqual(tx['fees'], Decimal("1.98"))
        self.assertEqual(tx['total_amount'], Decimal("8152.02"))
        self.assertEqual(tx['option_type'], "PUT")
        self.assertEqual(tx['option_strike'], Decimal("400.00"))
        self.assertEqual(tx['option_expiry'], date(2026, 12, 18))

    def test_parse_option_buy_to_close_description_format(self):
        csv_content = """Date,Action,Symbol,Description,Quantity,Price,Fees & Comm,Amount
05/14/2025,Buy to Close,NVDA,"PUT NVIDIA CORP $70 EXP 01/15/27",1,$4.11,$0.66,($411.66)"""
        # Note: Schwab CSV often has underlying ticker in Symbol for options parsed from Description
        parsed = parse_schwab_transactions(csv_content)
        self.assertEqual(len(parsed), 1)
        tx = parsed[0]
        self.assertEqual(tx['transaction_date'], date(2025, 5, 14))
        self.assertEqual(tx['action'], ActionTypeEnum.BUY_TO_CLOSE)
        self.assertEqual(tx['asset_type'], AssetTypeEnum.OPTION)
        self.assertEqual(tx['ticker'], "NVDA") # Assumes parser uses Symbol field if Description is for option
        self.assertEqual(tx['quantity'], Decimal("1"))
        self.assertEqual(tx['price'], Decimal("4.11"))
        self.assertEqual(tx['fees'], Decimal("0.66"))
        self.assertEqual(tx['total_amount'], Decimal("-411.66"))
        self.assertEqual(tx['option_type'], "PUT")
        self.assertEqual(tx['option_strike'], Decimal("70.00"))
        self.assertEqual(tx['option_expiry'], date(2027, 1, 15)) # YY format in desc

    def test_parse_option_sell_to_open_description_format_yy_expiry(self):
        csv_content = """Date,Action,Symbol,Description,Quantity,Price,Fees & Comm,Amount
05/14/2025,Sell to Open,NVDA,"PUT NVIDIA CORP $100 EXP 06/18/26",1,$8.31,$0.66,$830.34"""
        parsed = parse_schwab_transactions(csv_content)
        self.assertEqual(len(parsed), 1)
        tx = parsed[0]
        self.assertEqual(tx['option_type'], "PUT")
        self.assertEqual(tx['option_strike'], Decimal("100.00"))
        self.assertEqual(tx['option_expiry'], date(2026, 6, 18)) # YY format test

    def test_parse_dividend(self):
        csv_content = """Date,Action,Symbol,Description,Quantity,Price,Fees & Comm,Amount
05/15/2025,Qualified Dividend,AAPL,APPLE INC,,,,"$1.13""""
        parsed = parse_schwab_transactions(csv_content)
        self.assertEqual(len(parsed), 1)
        tx = parsed[0]
        self.assertEqual(tx['action'], ActionTypeEnum.DIVIDEND)
        self.assertEqual(tx['asset_type'], AssetTypeEnum.CASH)
        self.assertEqual(tx['ticker'], "AAPL") # Stock that paid dividend
        self.assertEqual(tx['total_amount'], Decimal("1.13"))
        self.assertEqual(tx['quantity'], Decimal("0")) # Or based on how parser handles blank
        self.assertEqual(tx['price'], Decimal("0"))    # Or based on how parser handles blank

    def test_skip_moneylink_transfer(self):
        csv_content = """Date,Action,Symbol,Description,Quantity,Price,Fees & Comm,Amount
01/01/2024,MoneyLink Transfer,,,Outgoing Transfer,,,,($1000.00)"""
        parsed = parse_schwab_transactions(csv_content)
        self.assertEqual(len(parsed), 0)

    def test_parse_with_empty_fees(self):
        csv_content = """Date,Action,Symbol,Description,Quantity,Price,Fees & Comm,Amount
05/19/2025,Buy,GOOG,GOOGLE INC,10,$150.00,,($1,500.00)"""
        parsed = parse_schwab_transactions(csv_content)
        self.assertEqual(len(parsed), 1)
        tx = parsed[0]
        self.assertEqual(tx['fees'], Decimal("0"))
        self.assertEqual(tx['total_amount'], Decimal("-1500.00"))

    def test_handle_option_symbol_with_spaces_in_ticker(self):
        # Example: "SPXW 03/28/2024 4500.00 C" (if SPXW is the ticker)
        # Current OPTION_SYMBOL_REGEX might only capture "SPXW" not "SPX W" if that were a thing.
        # This test is more for future-proofing or complex tickers.
        # For now, testing the provided "SPXW" example from earlier.
        csv_content = """Date,Action,Symbol,Description,Quantity,Price,Fees & Comm,Amount
03/10/2024,Buy to Open,SPXW,"CALL SPXW INDEX $4500 EXP 03/28/24",2,$50.00,$1.30,($10001.30)"""
        # The parser uses OPTION_DESC_REGEX for this one if symbol is just "SPXW"
        parsed = parse_schwab_transactions(csv_content)
        self.assertEqual(len(parsed), 1)
        tx = parsed[0]
        self.assertEqual(tx['ticker'], "SPXW") # From description parser
        self.assertEqual(tx['asset_type'], AssetTypeEnum.OPTION)
        self.assertEqual(tx['option_type'], "CALL")
        self.assertEqual(tx['option_strike'], Decimal("4500.00"))
        self.assertEqual(tx['option_expiry'], date(2024, 3, 28))

    def test_empty_input(self):
        csv_content = """Date,Action,Symbol,Description,Quantity,Price,Fees & Comm,Amount""" # Header only
        parsed = parse_schwab_transactions(csv_content)
        self.assertEqual(len(parsed), 0)
        
        csv_content_empty = ""
        parsed_empty = parse_schwab_transactions(csv_content_empty)
        self.assertEqual(len(parsed_empty), 0)

    def test_row_with_only_action_no_other_data(self):
        csv_content = """Date,Action,Symbol,Description,Quantity,Price,Fees & Comm,Amount
,Buy,,,,,,,"""
        parsed = parse_schwab_transactions(csv_content) # Should be skipped by date check or other errors
        self.assertEqual(len(parsed), 0)

if __name__ == '__main__':
    unittest.main()
