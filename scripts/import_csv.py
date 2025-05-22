#!/usr/bin/env python3

import argparse
import os
import sys

# Add project root to sys.path to allow direct imports of project modules
# This assumes the script is in a 'scripts' directory one level below project root.
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from sqlalchemy.orm import Session

# Importer components
from portfolio_tracker.importing.parsers.schwab_transactions_parser import parse_schwab_transactions
from portfolio_tracker.importing.services.transaction_import_service import TransactionImportService

# Database setup (assuming a central place for this, e.g., portfolio_tracker/database.py)
# For this script, we'll define a simple way to get a session.
# In a real app, SessionLocal would come from a database.py file.
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from portfolio_tracker.models import Base # To ensure tables are known if not yet created by create_db.py

# --- Database Setup (Simplified for script standalone use) ---
# In a real application, use a shared database configuration.
# Example: DATABASE_URL = "sqlite:///./portfolio.db" # or os.getenv("DATABASE_URL")
# For PostgreSQL, it would be like: "postgresql://user:password@host:port/database"

# Determine the correct DATABASE_URL (adjust as needed for your setup)
# This tries to make it relative to the project root where 'portfolio.db' might be.
DEFAULT_DB_PATH = os.path.join(project_root, "portfolio.db")
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_DB_PATH}")

engine = create_engine(DATABASE_URL)
# Optional: Create tables if they don't exist. Usually `create_db.py` handles this.
# Base.metadata.create_all(bind=engine) 
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
# --- End Database Setup ---


def main():
    parser = argparse.ArgumentParser(description="Import transactions from a CSV file.")
    parser.add_argument("--account_id", type=int, required=True, help="ID of the account to associate transactions with.")
    parser.add_argument("--broker", type=str, required=True, choices=["schwab"], help="Broker name (e.g., 'schwab').")
    parser.add_argument("--format_name", type=str, required=True, choices=["transactions_v1"], help="File format name (e.g., 'transactions_v1').")
    parser.add_argument("--filepath", type=str, required=True, help="Path to the CSV file.")

    args = parser.parse_args()

    print(f"Attempting to import file: {args.filepath} for account ID: {args.account_id}")

    try:
        with open(args.filepath, 'r', encoding='utf-8-sig') as f: # utf-8-sig handles potential BOM
            csv_content = f.read()
    except FileNotFoundError:
        print(f"Error: File not found at {args.filepath}")
        return
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    parsed_data = None
    if args.broker.lower() == "schwab":
        if args.format_name.lower() == "transactions_v1":
            try:
                parsed_data = parse_schwab_transactions(csv_content)
                print(f"Parser returned {len(parsed_data) if parsed_data else 0} potential transactions.")
            except Exception as e:
                print(f"Error parsing CSV content: {e}")
                return
        else:
            print(f"Error: Format '{args.format_name}' not supported for broker '{args.broker}'.")
            return
    else:
        print(f"Error: Broker '{args.broker}' not supported.")
        return

    if parsed_data is None or not parsed_data: # Check if parsed_data is None or empty
        print("No transactions were parsed from the file.")
        return
        
    db: Session = SessionLocal()
    try:
        # Corrected instantiation: TransactionImportService expects 'session', not 'db_session'
        importer_service = TransactionImportService(session=db) 
        
        # The import_transactions method returns a list of created_transactions.
        # We should check the length of this list to determine the number of imported transactions.
        created_transactions = importer_service.import_transactions(
            account_id=args.account_id,
            parsed_transactions_data=parsed_data
        )
        num_imported = len(created_transactions) # Get the count from the returned list

        if num_imported > 0:
            print(f"Successfully imported {num_imported} transactions into account {args.account_id}.")
        else:
            print(f"No new transactions were imported. (Possible reasons: all transactions already exist, errors during individual transaction processing, or the file parsed to zero valid transactions).")

    except ValueError as ve: # Catch specific ValueErrors from the service
        print(f"ValueError during import: {ve}")
    except Exception as e:
        print(f"An error occurred during the import process: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
