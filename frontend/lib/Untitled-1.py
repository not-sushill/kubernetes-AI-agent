#!/usr/bin/env python3

import os
import csv
import glob
import json
import sys
from datetime import datetime

import pandas as pd

###############################################################################
# Configuration
###############################################################################

BASE_DIR = "/opt/aurora_audit"

STATE_FILE = os.path.join(BASE_DIR, "state.json")

today = datetime.now()

YEAR = today.strftime("%Y")
MONTH = today.strftime("%m")
DATE = today.strftime("%d-%m-%Y")

REPORT_DIR = os.path.join(
    BASE_DIR,
    "reports",
    YEAR,
    MONTH
)

os.makedirs(REPORT_DIR, exist_ok=True)

report_path = os.path.join(
    REPORT_DIR,
    f"{DATE}.xlsx"
)

###############################################################################
# Read today's log directory
###############################################################################

if len(sys.argv) != 2:
    print("Usage: python3 merge_audit_logs.py <audit_log_directory>")
    sys.exit(1)

LOG_DIR = sys.argv[1]

if not os.path.isdir(LOG_DIR):
    print("Invalid log directory")
    sys.exit(1)

###############################################################################
# Read state.json
###############################################################################

if not os.path.exists(STATE_FILE):

    state = {
        "last_timestamp": 0
    }

else:

    with open(STATE_FILE, "r") as f:

        state = json.load(f)

LAST_TIMESTAMP = int(state["last_timestamp"])

print(f"Last Processed Timestamp : {LAST_TIMESTAMP}")

###############################################################################
# Read Audit Logs
###############################################################################

audit_rows = []

latest_timestamp = LAST_TIMESTAMP

files = sorted(glob.glob(os.path.join(LOG_DIR, "audit.log*")))

print(f"Found {len(files)} audit log files")

###############################################################################
# Parse each file
###############################################################################

for file in files:

    print(f"Reading : {os.path.basename(file)}")

    with open(file, "r", encoding="utf-8", errors="ignore") as f:

        reader = csv.reader(
            f,
            delimiter=',',
            quotechar="'"
        )

        for row in reader:

            if len(row) != 10:
                print(f"Skipping malformed row: {row}")
                continue

            try:

                timestamp = int(row[0])

            except:

                continue

            ###############################################################
            # Skip duplicate entries
            ###############################################################

            if timestamp <= LAST_TIMESTAMP:
                continue

            ###############################################################
            # Keep latest timestamp
            ###############################################################

            if timestamp > latest_timestamp:

                latest_timestamp = timestamp

            ###############################################################
            # Only QUERY_DDL
            ###############################################################

            if row[6].strip() != "QUERY":
                continue

            ###############################################################
            # Convert timestamp
            ###############################################################

            dt = datetime.fromtimestamp(
                timestamp / 1000000
            )

            audit_rows.append({

                "Timestamp": dt.strftime("%Y-%m-%d %H:%M:%S"),

                "Epoch": timestamp,

                "Instance": row[1],

                "User": row[2],

                "Host": row[3],

                "Thread ID": row[4],

                "Query ID": row[5],

                "Event": row[6],

                "Database": row[7],

                "SQL Query": row[8],

                "Status": row[9],

                "Source File": os.path.basename(file)

            })

###############################################################################
# DataFrame
###############################################################################

df = pd.DataFrame(audit_rows)
df["SQL Query"] = df["SQL Query"].str.replace(
    r"\s+",
    " ",
    regex=True
).str.strip()

print()

print(f"New DDL Records : {len(df)}")

###############################################################################
# Exit if no DDL records
###############################################################################

if df.empty:

    print("No new DDL activity found.")
    sys.exit(0)

###############################################################################
# Remove duplicate rows across all audit logs
###############################################################################

print("\nRemoving duplicate records...")

before = len(df)

df = df.drop_duplicates(
    subset=[
        "Epoch",
        "SQL Query"
    ],
    keep="first"
)

after = len(df)

print(f"Duplicates Removed : {before-after}")
print(f"Records Remaining  : {after}")
###############################################################################
# Sort by Timestamp
###############################################################################

df = df.sort_values(
    by=[
        "Epoch",
        "Source File"
    ],
    ascending=True
)

df.reset_index(
    drop=True,
    inplace=True
)

###############################################################################
# Prepare Report Name
###############################################################################

today = datetime.now().strftime("%d-%m-%Y")

report_path = os.path.join(
    REPORT_DIR,
    f"{today}.xlsx"
)

print()
print("Report will be saved to:")
print(report_path)

###############################################################################
# Create Excel Writer
###############################################################################

writer = pd.ExcelWriter(
    report_path,
    engine="openpyxl"
)

df.to_excel(
    writer,
    sheet_name="DDL_Audit",
    index=False
)

workbook = writer.book
sheet = writer.sheets["DDL_Audit"]

###############################################################################
# Format Excel
###############################################################################

from openpyxl.styles import Alignment, Font

# Bold header
for cell in sheet[1]:
    cell.font = Font(bold=True)

# Wrap SQL Query column
sql_column = None

for cell in sheet[1]:
    if cell.value == "SQL Query":
        sql_column = cell.column_letter
        break

if sql_column:

    for cell in sheet[sql_column]:

        cell.alignment = Alignment(
            wrap_text=True,
            vertical="top"
        )

###############################################################################
# Auto Fit Columns
###############################################################################

for column_cells in sheet.columns:

    max_length = 0

    column = column_cells[0].column_letter

    for cell in column_cells:

        try:

            if cell.value is not None:

                value = str(cell.value)

                if len(value) > max_length:

                    max_length = len(value)

        except:

            pass

    if max_length > 100:
        max_length = 100

    sheet.column_dimensions[column].width = max_length + 3

###############################################################################
# Freeze Header
###############################################################################

sheet.freeze_panes = "A2"
sheet.auto_filter.ref = sheet.dimensions

###############################################################################
# Save Workbook
###############################################################################

writer.close()

print()
print("Excel created successfully.")

###############################################################################
# Update state.json
###############################################################################

with open(STATE_FILE, "w") as f:

    json.dump(
        {
            "last_timestamp": latest_timestamp
        },
        f,
        indent=4
    )

print("state.json updated.")

###############################################################################
# Final Summary
###############################################################################

print()
print("==============================================")
print("Aurora Audit Report Completed")
print("==============================================")
print(f"Records Exported : {len(df)}")
print(f"Excel File       : {report_path}")
print(f"Latest Timestamp : {latest_timestamp}")
print("==============================================")