import unittest
import tempfile
import os
from datetime import date
from decimal import Decimal

from portfolio_tracker.models import ActionTypeEnum, AssetTypeEnum
from portfolio_tracker.importing.parsers.schwab_transactions_parser import parse_schwab_transactions

class TestSchwabTransactionsParser(unittest.TestCase):

    def test_parse_schwab_transactions_valid_data(self):
        sample_csv_content = """Date,Action,Symbol,Description,Quantity,Price,Fees & Comm,Amount
5/19/2025,Buy,NVDA,NVIDIA CORP,100,$135.50,,($13,550.00)
5/15/2025,Sell to Open,MSFT 12/18/2026 400.00 P,"PUT MICROSOFT CORP $400 EXP 12/18/26",3,$27.18,$1.98,$8,152.02
5/15/2025,Qualified Dividend,AAPL,APPLE INC,,,,"$1.13"
5/14/2025,Buy to Close,NVDA 01/15/2027 70.00 P,"PUT NVIDIA CORP $70 EXP 01/15/27",1,$4.11,$0.66,($411.66)
01/01/2024,MoneyLink Transfer,,,Outgoing Transfer,,,,($1000.00)
02/01/2024,Service Fee,,SERVICE CHARGE,,,($5.00)
"""
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".csv", newline='') as tmp_csv_file:
            tmp_csv_file.write(sample_csv_content)
            tmp_csv_file.flush()
            tmp_file_path = tmp_csv_file.name

        try:
            parsed_data = parse_schwab_transactions(tmp_file_path)

            # Expect 4 transactions (Buy, Sell to Open, Dividend, Buy to Close)
            # MoneyLink Transfer and Service Fee should be skipped
            self.assertEqual(len(parsed_data), 4)

            # Transaction 1: Buy NVDA
            self.assertEqual(parsed_data[0]['transaction_date'], date(2025, 5, 19))
            self.assertEqual(parsed_data[0]['action'], ActionTypeEnum.BUY)
            self.assertEqual(parsed_data[0]['asset_type'], AssetTypeEnum.STOCK)
            self.assertEqual(parsed_data[0]['ticker'], 'NVDA')
            self.assertEqual(parsed_data[0]['quantity'], Decimal('100'))
            self.assertEqual(parsed_data[0]['price'], Decimal('135.50'))
            self.assertEqual(parsed_data[0]['fees'], Decimal('0'))
            self.assertEqual(parsed_data[0]['total_amount'], Decimal('-13550.00'))
            self.assertIsNone(parsed_data[0]['option_type'])
            self.assertIsNone(parsed_data[0]['option_strike'])
            self.assertIsNone(parsed_data[0]['option_expiry'])

            # Transaction 2: Sell to Open MSFT Option
            self.assertEqual(parsed_data[1]['transaction_date'], date(2025, 5, 15))
            self.assertEqual(parsed_data[1]['action'], ActionTypeEnum.SELL_TO_OPEN)
            self.assertEqual(parsed_data[1]['asset_type'], AssetTypeEnum.OPTION)
            self.assertEqual(parsed_data[1]['ticker'], 'MSFT')
            self.assertEqual(parsed_data[1]['quantity'], Decimal('3'))
            self.assertEqual(parsed_data[1]['price'], Decimal('27.18'))
            self.assertEqual(parsed_data[1]['fees'], Decimal('1.98'))
            self.assertEqual(parsed_data[1]['total_amount'], Decimal('8152.02')) # 3 * 27.18 * 100 (assuming standard option multiplier) - 1.98 fees -> actually schwab gives total
            self.assertEqual(parsed_data[1]['option_type'], 'PUT')
            self.assertEqual(parsed_data[1]['option_strike'], Decimal('400.00'))
            self.assertEqual(parsed_data[1]['option_expiry'], date(2026, 12, 18))

            # Transaction 3: Qualified Dividend AAPL
            self.assertEqual(parsed_data[2]['transaction_date'], date(2025, 5, 15))
            self.assertEqual(parsed_data[2]['action'], ActionTypeEnum.DIVIDEND)
            self.assertEqual(parsed_data[2]['asset_type'], AssetTypeEnum.CASH) # Dividends are cash deposits
            self.assertEqual(parsed_data[2]['ticker'], 'AAPL') # Ticker is present
            self.assertEqual(parsed_data[2]['quantity'], Decimal('0')) # No quantity for dividend
            self.assertEqual(parsed_data[2]['price'], Decimal('0')) # No price for dividend
            self.assertEqual(parsed_data[2]['fees'], Decimal('0'))
            self.assertEqual(parsed_data[2]['total_amount'], Decimal('1.13'))
            self.assertIsNone(parsed_data[2]['option_type'])
            self.assertIsNone(parsed_data[2]['option_strike'])
            self.assertIsNone(parsed_data[2]['option_expiry'])
            
            # Transaction 4: Buy to Close NVDA Option
            self.assertEqual(parsed_data[3]['transaction_date'], date(2025, 5, 14))
            self.assertEqual(parsed_data[3]['action'], ActionTypeEnum.BUY_TO_CLOSE)
            self.assertEqual(parsed_data[3]['asset_type'], AssetTypeEnum.OPTION)
            self.assertEqual(parsed_data[3]['ticker'], 'NVDA')
            self.assertEqual(parsed_data[3]['quantity'], Decimal('1'))
            self.assertEqual(parsed_data[3]['price'], Decimal('4.11'))
            self.assertEqual(parsed_data[3]['fees'], Decimal('0.66'))
            self.assertEqual(parsed_data[3]['total_amount'], Decimal('-411.66'))
            self.assertEqual(parsed_data[3]['option_type'], 'PUT')
            self.assertEqual(parsed_data[3]['option_strike'], Decimal('70.00'))
            self.assertEqual(parsed_data[3]['option_expiry'], date(2027, 1, 15))

        finally:
            os.remove(tmp_file_path)

if __name__ == '__main__':
    unittest.main()
