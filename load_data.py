import csv
from datetime import datetime
from pymongo import MongoClient

# Fields that should be stored as decimal numbers (e.g. 17.87, -67.15)
FLOAT_FIELDS = {
    "decimalLatitude",
    "decimalLongitude",
    "minimumDepthInMeters",
    "maximumDepthInMeters",
    "coordinateUncertaintyInMeters",
}

# Fields that should be stored as whole numbers (e.g. coral count = 14)
INT_FIELDS = {"organismQuantity"}


def cast_row(row):
    # Convert location/depth fields from text to actual numbers
    for field in FLOAT_FIELDS:
        val = row.get(field, "").strip()
        row[field] = float(val) if val else None

    # Convert organism count from text to a whole number
    for field in INT_FIELDS:
        val = row.get(field, "").strip()
        row[field] = int(val) if val else None

    # Convert the date string (e.g. "2021-11-02") into a real date object
    date_str = row.get("eventDate", "").strip()
    if date_str:
        try:
            row["eventDate"] = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            row["eventDate"] = None

    return row


def load(tsv_path="occurrence.txt", batch_size=1000):
    # Connect to the local MongoDB server
    client = MongoClient("mongodb://localhost:27017/")

    # Point to the coral_reef database and occurrences collection
    collection = client["coral_reef"]["occurrences"]

    total = 0
    batch = []

    # Open the tab-separated file and read it row by row
    with open(tsv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            batch.append(cast_row(row))

            # Once we have 1000 rows, insert them all at once and reset the batch
            if len(batch) == batch_size:
                collection.insert_many(batch)
                total += len(batch)
                batch = []
                print(f"  Inserted {total} records...", end="\r")

    # Insert any remaining rows that didn't fill a full batch
    if batch:
        collection.insert_many(batch)
        total += len(batch)

    print(f"\nDone. Total records inserted: {total}")
    client.close()


if __name__ == "__main__":
    load()
