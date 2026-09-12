"""Week 2 starter: profile CSV, JSON, Parquet, API payload, and PostgreSQL table.
Complete the TODOs. Do not hard-code expected counts.
"""
from pathlib import Path
import json, csv
import pandas as pd
DATA_DIR=Path(__file__).resolve().parents[1]/'data'

def profile_csv(path):
    # row count, columns, missing counts, duplicate rows, duplicate customer_id, inferred types
    size_bytes = path.stat().st_size
    df = pd.read_csv(path)
 
    print(f"\n--- {path.name} ---")
    print(f"File size: {size_bytes} bytes ({size_bytes / 1024:.1f} KB)")
    print(f"Rows: {df.shape[0]}, Columns: {df.shape[1]}")
 
    print("\nColumn dtypes (pandas-inferred):")
    print(df.dtypes)
 
    print("\nMissing values per column:")
    print(df.isnull().sum())
 
    dupe_rows = df.duplicated(keep=False)
    print(f"\nExact duplicate rows: {dupe_rows.sum()}")
    if dupe_rows.sum() > 0:
        print(df[dupe_rows])
 
    if "customer_id" in df.columns:
        total = len(df)
        unique_ids = df["customer_id"].nunique(dropna=False)
        print(f"\ncustomer_id: {total} rows, {unique_ids} unique values")
        print(f"Is unique? {total == unique_ids}")
        if total != unique_ids:
            dupes = df[df["customer_id"].duplicated(keep=False)].sort_values("customer_id")
            print(dupes)
 
    return df
 
 
def profile_json(path):
    # record count, keys, nested fields, date/time fields, numeric fields, nulls
    with open(path) as f:
        records = json.load(f)
 
    print(f"\n--- {path.name} ---")
    print(f"Root type: {type(records)}")
    print(f"Is list: {isinstance(records, list)}")
    print(f"Record count: {len(records)}")
 
    first_keys = set(records[0].keys())
    print(f"\nTop-level keys (record 0): {first_keys}")
 
    all_keys_match = all(set(r.keys()) == first_keys for r in records)
    print(f"All records share identical keys: {all_keys_match}")
 
    print("\nField types (record 0):")
    for k, v in records[0].items():
        print(f"  {k}: {type(v).__name__}")
 
    flat = pd.json_normalize(records)
    print("\nMissing values per flattened column:")
    print(flat.isnull().sum())
 
    return flat
 
 
def profile_parquet(path):
    # use pandas.read_parquet; report rows/columns/dtypes/nulls and file size
    # Requires pyarrow from requirements.txt
    size_bytes = path.stat().st_size
    df = pd.read_parquet(path)
 
    print(f"\n--- {path.name} ---")
    print(f"File size: {size_bytes} bytes ({size_bytes / 1024:.1f} KB)")
    print(f"Rows: {df.shape[0]}, Columns: {df.shape[1]}")
    print(f"\nDtypes:\n{df.dtypes}")
    print("\nMissing values per column:")
    print(df.isnull().sum())
 
    return df

if __name__=='__main__':
    profile_csv(DATA_DIR/'customers.csv')
    profile_json(DATA_DIR/'orders.json')
    profile_parquet(DATA_DIR/'products.parquet')
