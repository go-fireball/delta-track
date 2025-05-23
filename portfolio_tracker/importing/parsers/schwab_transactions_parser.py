# portfolio_tracker/importing/parsers/schwab_transactions_parser.py

import csv
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation

# This relative import assumes that models.py is in portfolio_tracker/models.py
# and this file is in portfolio_tracker/importing/parsers/
from ....models import ActionTypeEnum, AssetTypeEnum

def parse_schwab_decimal(value_str):
    if not value_str:
        return Decimal("0")
    value_str = str(value_str).replace("$", "").replace(",", "")
    if value_str.startswith("(") and value_str.endswith(")"):
        return Decimal("-" + value_str[1:-1])
    try:
        return Decimal(value_str)
    except InvalidOperation:
        # print(f"Warning: Could not parse decimal from '{value_str}', returning 0.")
        return Decimal("0")

OPTION_DESC_REGEX = re.compile(r"(CALL|PUT)\s+([A-Z\s.]+?)\s+\$(\d+\.\d{2,})\s+EXP\s+(\d{1,2}/\d{1,2}/\d{2,4})")
OPTION_SYMBOL_REGEX = re.compile(r"([A-Z]+)\s+(\d{1,2}/\d{1,2}/\d{2,4})\s+([\d\.]+)\s+([CP])")

ACTION_MAP = {
    "Buy": ActionTypeEnum.BUY,
    "Sell": ActionTypeEnum.SELL,
    "Sell to Open": ActionTypeEnum.SELL_TO_OPEN,
    "Buy to Open": ActionTypeEnum.BUY_TO_OPEN,
    "Sell to Close": ActionTypeEnum.SELL_TO_CLOSE,
    "Buy to Close": ActionTypeEnum.BUY_TO_CLOSE,
    "Qualified Dividend": ActionTypeEnum.DIVIDEND,
    "Cash Dividend": ActionTypeEnum.DIVIDEND,
    "Interest Income": ActionTypeEnum.INTEREST,
    # "MoneyLink Transfer": None, # Handled by explicit skip
    # "Journal": None, # Handled by explicit skip
    # "Service Fee": ActionTypeEnum.FEE # Example if needed
}

def parse_schwab_transactions(csv_file_path: str):
    with open(csv_file_path, 'r', encoding='utf-8') as f:
        csv_content_string = f.read()
    # Replace null bytes if they exist
    csv_content_string = csv_content_string.replace('\x00', '').replace(' ', '')
    reader = csv.DictReader(csv_content_string.splitlines())
    parsed_transactions = []

    for row_idx, row in enumerate(reader):
        raw_action = row.get("Action", "").strip()
        
        if not raw_action: 
            continue

        action_enum = ACTION_MAP.get(raw_action)

        if action_enum is None:
            if raw_action.lower() not in ["moneylink transfer", "journal", "service fee", "funds received", "funds paid", "dividend paid", "adjustment", "bank interest", "atm withdrawal", "bill pay", "check paid", "client requested electronic funding receipt (pull)", "client requested electronic funding disbursement (push)", "dividend reinvestment", "funds transfer", "tax payment", "wire transfer incoming", "wire transfer outgoing"]: 
                print(f"Skipping row {row_idx+2} with unmapped action: '{raw_action}'. Data: {row}")
            continue
            
        try:
            transaction_date_str = row.get("Date", "").strip()
            if not transaction_date_str:
                continue
            transaction_date = datetime.strptime(transaction_date_str, "%m/%d/%Y").date()
            
            symbol_str = row.get("Symbol", "").strip()
            description_str = row.get("Description", "").strip()
            
            quantity_str = row.get("Quantity","")
            price_str = row.get("Price","")
            fees_str = row.get("Fees & Comm","")
            amount_str = row.get("Amount","")

            quantity = parse_schwab_decimal(quantity_str) if quantity_str else Decimal("0")
            price = parse_schwab_decimal(price_str) if price_str else Decimal("0")
            fees = parse_schwab_decimal(fees_str) if fees_str else Decimal("0")
            amount = parse_schwab_decimal(amount_str) if amount_str else Decimal("0")

            asset_type_enum = AssetTypeEnum.STOCK 
            option_type_str = None
            option_strike_val = None
            option_expiry_date = None
            ticker_str = symbol_str 

            if action_enum in [ActionTypeEnum.SELL_TO_OPEN, ActionTypeEnum.BUY_TO_OPEN, ActionTypeEnum.SELL_TO_CLOSE, ActionTypeEnum.BUY_TO_CLOSE]:
                asset_type_enum = AssetTypeEnum.OPTION
                parsed_option_details = False
                
                if symbol_str: 
                    match_sym = OPTION_SYMBOL_REGEX.match(symbol_str)
                    if match_sym:
                        ticker_str = match_sym.group(1)
                        expiry_str = match_sym.group(2)
                        strike_str = match_sym.group(3)
                        type_char = match_sym.group(4)
                        
                        option_type_str = "CALL" if type_char == "C" else "PUT"
                        option_strike_val = Decimal(strike_str)
                        try:
                            option_expiry_date = datetime.strptime(expiry_str, "%m/%d/%Y").date()
                        except ValueError:
                            option_expiry_date = datetime.strptime(expiry_str, "%m/%d/%y").date()
                        parsed_option_details = True

                if not parsed_option_details and description_str:
                    match_desc = OPTION_DESC_REGEX.search(description_str.upper())
                    if match_desc:
                        option_type_str = match_desc.group(1)
                        
                        extracted_name_from_desc = match_desc.group(2).strip()
                        if symbol_str and not OPTION_SYMBOL_REGEX.match(symbol_str) and " " not in symbol_str: 
                             ticker_str = symbol_str 
                        else: 
                            ticker_str = extracted_name_from_desc.split(' ')[0]
                        
                        option_strike_val = Decimal(match_desc.group(3))
                        expiry_str = match_desc.group(4)
                        try:
                            option_expiry_date = datetime.strptime(expiry_str, "%m/%d/%Y").date()
                        except ValueError:
                            option_expiry_date = datetime.strptime(expiry_str, "%m/%d/%y").date()
                        parsed_option_details = True
                
                if not parsed_option_details:
                    print(f"WARNING: Option action '{raw_action}' for '{symbol_str}'-'{description_str}' but could not parse option details.")
                    continue 
            
            elif action_enum == ActionTypeEnum.DIVIDEND or action_enum == ActionTypeEnum.INTEREST:
                asset_type_enum = AssetTypeEnum.CASH
                ticker_str = symbol_str if symbol_str else description_str 
                if not ticker_str and "dividend" in description_str.lower(): 
                    ticker_str = description_str.replace("Dividend", "").strip()
            
            fees = fees.copy_abs()

            parsed_transactions.append({
                "transaction_date": transaction_date,
                "action": action_enum,
                "asset_type": asset_type_enum,
                "ticker": ticker_str.strip(), 
                "quantity": quantity.copy_abs() if quantity else Decimal(0), 
                "price": price.copy_abs() if price else Decimal(0),       
                "fees": fees,
                "total_amount": amount, 
                "option_type": option_type_str,
                "option_strike": option_strike_val,
                "option_expiry": option_expiry_date,
                "raw_description": description_str,
                "raw_symbol": symbol_str
            })

        except Exception as e:
            print(f"Error parsing row {row_idx+2} ({row}): {e}")
            continue
            
    return parsed_transactions

if __name__ == '__main__':
    import argparse
    import os

    parser = argparse.ArgumentParser(description="Parse Schwab transaction CSV file.")
    parser.add_argument("csv_file", help="Path to the Schwab transactions CSV file.")
    
    args = parser.parse_args()

    if not os.path.exists(args.csv_file):
        print(f"Error: File not found at {args.csv_file}")
    elif not os.path.isfile(args.csv_file):
        print(f"Error: Path {args.csv_file} is not a file.")
    else:
        try:
            parsed_data = parse_schwab_transactions(args.csv_file)
            print(f"Successfully parsed {len(parsed_data)} transactions from {args.csv_file}.")
            for item_idx, item in enumerate(parsed_data):
                print(f"Item {item_idx+1}: {item}")
        except Exception as e:
            print(f"An error occurred while parsing the file: {e}")
