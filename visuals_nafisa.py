import pandas as pd
import matplotlib.pyplot as plt
from pymongo import MongoClient

# Connect to MongoDB
client = MongoClient("mongodb://localhost:27017/")
collection = client["coral_reef"]["occurrences"]


# Q1: Distinct species per year 

q1 = collection.aggregate([
    { "$match": { "occurrenceStatus": "present" }},
    { "$group": {
        "_id": { "$year": "$eventDate" },
        "distinctSpecies": { "$addToSet": "$scientificName" }
    }},
    { "$project": { "year": "$_id", "totalSpecies": { "$size": "$distinctSpecies" } }},
    { "$sort": { "year": 1 } }
])

df_q1 = pd.DataFrame(q1)

plt.figure(figsize=(10, 5))
plt.plot(df_q1["year"], df_q1["totalSpecies"], marker="o", color="steelblue", linewidth=2)
plt.title("Distinct Coral Species Observed Per Year (All US Regions)", fontsize=13)
plt.xlabel("Year")
plt.ylabel("Number of Distinct Species")
plt.xticks(df_q1["year"])
plt.grid(axis="y", linestyle="--", alpha=0.5)
plt.tight_layout()
plt.savefig("q1_species_per_year.png")
plt.show()
print("Saved: q1_species_per_year.png")
