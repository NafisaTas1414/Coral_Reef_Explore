import pandas as pd
import numpy as np
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


# Q3: Steepest decline by region

q3 = collection.aggregate([
    { "$match": { "occurrenceStatus": "present" }},
    { "$group": {
        "_id": { "region": "$locality", "year": { "$year": "$eventDate" } },
        "distinctSpecies": { "$addToSet": "$scientificName" }
    }},
    { "$project": { "region": "$_id.region", "year": "$_id.year", "speciesCount": { "$size": "$distinctSpecies" } }},
    { "$sort": { "year": 1 }},
    { "$group": {
        "_id": "$region",
        "firstCount": { "$first": "$speciesCount" },
        "lastCount":  { "$last": "$speciesCount" }
    }},
    { "$project": {
        "region": "$_id",
        "change": { "$subtract": ["$lastCount", "$firstCount"] }
    }},
    { "$sort": { "change": 1 }}
])

df_q3 = pd.DataFrame(q3)
df_q3["region"] = df_q3["region"].str.replace(", ", "\n")

colors = ["#8a1c1c" if c < 0 else "#0d8b0d" if c > 0 else "#385d8c" for c in df_q3["change"]]

plt.figure(figsize=(11, 6))
plt.barh(df_q3["region"], df_q3["change"], color=colors)
plt.axvline(0, color="black", linewidth=0.8)
plt.title("Species Change by Region (First vs Most Recent Survey)", fontsize=13)
plt.xlabel("Change in Distinct Species Count")
plt.tight_layout()
plt.savefig("q3_decline_by_region.png")
plt.show()
print("Saved: q3_decline_by_region.png")


# Q6: Top 10 most declined species — first vs last abundance

q6 = collection.aggregate([
    { "$match": { "occurrenceStatus": "present", "organismQuantity": { "$gt": 0 } }},
    { "$group": {
        "_id": { "species": "$scientificName", "year": { "$year": "$eventDate" } },
        "totalAbundance": { "$sum": "$organismQuantity" }
    }},
    { "$sort": { "_id.year": 1 }},
    { "$group": {
        "_id": "$_id.species",
        "firstAbundance": { "$first": "$totalAbundance" },
        "lastAbundance":  { "$last": "$totalAbundance" }
    }},
    { "$project": {
        "species": "$_id",
        "firstAbundance": 1,
        "lastAbundance": 1,
        "change": { "$subtract": ["$lastAbundance", "$firstAbundance"] }
    }},
    { "$sort": { "change": 1 }},
    { "$limit": 10 }
])

df_q6 = pd.DataFrame(q6)

# creates an array for (position numbers) for the bars
y = np.arange(len(df_q6))
bar_height = 0.35

fig, ax = plt.subplots(figsize=(12,7))

# plots the bars for each species slightly above and below center
ax.barh(y + bar_height / 2, df_q6["firstAbundance"], bar_height, label="First Survey Year", color="skyblue")
ax.barh(y - bar_height / 2, df_q6["lastAbundance"],  bar_height, label="Last Survey Year",  color="salmon")

# labels 
ax.set_yticks(y)
ax.set_yticklabels(df_q6["species"], fontstyle="italic")
ax.set_xlabel("Total Abundance (Individual Corals Counted)")
ax.set_title("Top 10 Most Declined Species: First vs Most Recent Survey", fontsize=13)
ax.legend()
plt.tight_layout()
plt.savefig("q6_most_at_risk_species.png")
plt.show()
print("Saved: q6_most_at_risk_species.png")


# Q7: Coral abundance by depth band over time

q7 = collection.aggregate([
    { "$match": { "occurrenceStatus": "present", "organismQuantity": { "$gt": 0 } }},
    { "$group": {
        "_id": { "depthBand": { "$switch": {
                "branches": [
                    { "case": { "$lt": ["$minimumDepthInMeters", 10] }, "then": "Shallow (0-10m)" },
                    { "case": { "$lt": ["$minimumDepthInMeters", 20] }, "then": "Mid (10-20m)" }],
                "default": "Deep (20m+)"
            }}, "year": { "$year": "$eventDate" }}, "totalAbundance": { "$sum": "$organismQuantity" }
            }},{ "$sort": { "_id.year": 1 }}])

df_q7 = pd.DataFrame(q7)
df_q7["year"]      = df_q7["_id"].apply(lambda x: x["year"])
df_q7 = df_q7[~df_q7['year'].isin([2024])]
df_q7["depthBand"] = df_q7["_id"].apply(lambda x: x["depthBand"])

colors_depth = { "Shallow (0-10m)": "#28b038", "Mid (10-20m)": "#4f99d5",
                 "Deep (20m+)":     "#2e4057"}

plt.figure(figsize=(11, 5))
for band, color in colors_depth.items():
    subset = df_q7[df_q7["depthBand"] == band].sort_values("year")
    plt.plot(subset["year"], subset["totalAbundance"], marker="o", label=band, color=color, linewidth=2)

plt.title("Coral Abundance by Depth Band Over Time", fontsize=13)
plt.xlabel("Year")
plt.ylabel("Total Abundance")
plt.legend()
plt.xticks(sorted(df_q7["year"].unique()))
plt.grid(axis="y", linestyle="--", alpha=0.5)
plt.tight_layout()
plt.savefig("q7_depth_over_time.png")
plt.show()
print("Saved: q7_depth_over_time.png")

client.close()
