# HW 5: NoSQL R&D Project (GROUP PROJECT)
# BY: Nafisa
# Date: 6/10/2026

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")
collection = client["coral_reef"]["occurrences"]


# Q1: Species Winners vs Losers
# compares each species' total abundance in its first survey year vs most recent

def get_species_change(sort_order, limit=10):
    # excludes 2024 since surveys were incomplete that year
    return list(collection.aggregate([
        { "$match": { "occurrenceStatus": "present", "organismQuantity": { "$gt": 0 },
                      "eventDate": { "$lt": datetime(2024, 1, 1) } }},
        { "$group": {
            "_id": { "species": "$scientificName", "year": { "$year": "$eventDate" } },
            "totalAbundance": { "$sum": "$organismQuantity" }
        }},
        { "$sort": { "_id.year": 1 }},
        { "$group": {
            "_id": "$_id.species",
            "firstAbundance": { "$first": "$totalAbundance" },
            "lastAbundance":  { "$last":  "$totalAbundance" }
        }},
        { "$project": {"species": "$_id", "firstAbundance": 1, "lastAbundance": 1,
            "change": { "$subtract": ["$lastAbundance", "$firstAbundance"] }}},
        { "$sort": { "change": sort_order }},
        { "$limit": limit }
    ]))

# sort_order=-1 gets biggest gainers, 1 gets biggest losers
winners = pd.DataFrame(get_species_change(sort_order=-1))
losers  = pd.DataFrame(get_species_change(sort_order=1))

fig, (ax_left, ax_right) = plt.subplots(1, 2, figsize=(16, 7))

ax_left.barh(winners["species"], winners["change"], color="#2ca02c")
ax_left.set_title("Top 10 Growing Species", fontsize=12)
ax_left.set_xlabel("Increase in Individual Corals Counted")
ax_left.invert_yaxis()

ax_right.barh(losers["species"], losers["change"], color="#d62728")
ax_right.set_title("Top 10 Shrinking Species", fontsize=12)
ax_right.set_xlabel("Decrease in Individual Corals Counted")
ax_right.invert_yaxis()

fig.suptitle("Growing vs Declining Coral Species (First vs Most Recent Survey)",
             fontsize=13, fontweight="bold")
plt.tight_layout()
plt.savefig("q1_growing_vs_decreasing_corals.png")
plt.show()
print("Saved: q1_growing_vs_decreasing_corals.png")


# Q3: Species richness change by region (first vs most recent survey)
# negative change = fewer species recorded, positive = more species observed

results = collection.aggregate([
    # exclude 2024 so Flower Garden Banks (last surveyed 2024) isn't compared on an incomplete year
    { "$match": { "occurrenceStatus": "present",
                  "eventDate": { "$lt": datetime(2024, 1, 1) } }},
    { "$group": {
        "_id": { "region": "$locality", "year": { "$year": "$eventDate" } },
        "distinctSpecies": { "$addToSet": "$scientificName" }
    }},
    { "$project": { "region":  "$_id.region",
        "year":  "$_id.year",
        "speciesCount": { "$size": "$distinctSpecies" }
    }},
    { "$sort": { "year": 1 }},
    { "$group": {
        "_id":  "$region",
        "firstCount": { "$first": "$speciesCount" },
        "lastCount":  { "$last":  "$speciesCount" }
    }},
    { "$project": {
        "region": "$_id",
        "change": { "$subtract": ["$lastCount", "$firstCount"] }
    }},
    { "$sort": { "change": 1 }}
])

df = pd.DataFrame(results)
df["region"] = df["region"].str.replace(", ", "\n")
# red = decline, green = gain, blue = no change
colors = ["#8a1c1c" if c < 0 else "#0d8b0d" if c > 0 else "#385d8c" for c in df["change"]]

plt.figure(figsize=(11, 6))
plt.barh(df["region"], df["change"], color=colors)
plt.axvline(0, color="black", linewidth=0.8)
plt.title("Species Change by Region (First vs Most Recent Survey)", fontsize=13)
plt.xlabel("Change in Distinct Species Count")
plt.tight_layout()
plt.savefig("q3_decline_by_region.png")
plt.show()
print("Saved: q3_decline_by_region.png")


# Heatmap: species richness by region and year
# blank cells = region not surveyed that year

short = {
    "Florida Keys, Florida":  "Florida Keys",
    "Southeast Florida":  "SE Florida",
    "Dry Tortugas, Florida": "Dry Tortugas",
    "Puerto Rico":   "Puerto Rico",
    "St. Croix, US Virgin Islands":  "St. Croix (USVI)",
    "St. Thomas and St. John, US Virgin Islands":   "St. Thomas/John (USVI)",
    "Flower Garden Banks, Gulf of Mexico":  "Flower Garden Banks",
}

results = collection.aggregate([
    { "$match": { "occurrenceStatus": "present" }},
    { "$group": {
        "_id": { "region": "$locality", "year": { "$year": "$eventDate" }},
        "distinctSpecies": { "$addToSet": "$scientificName" }
    }},
    { "$project": {
        "region":       "$_id.region",
        "year":         "$_id.year",
        "speciesCount": { "$size": "$distinctSpecies" }
    }},
    { "$sort": { "year": 1 }}
])

df = pd.DataFrame(results)
df["region"] = df["_id"].apply(lambda x: x["region"])
df["year"]   = df["_id"].apply(lambda x: x["year"])

# exclude 2020 (COVID) and 2024 (incomplete)
df = df[~df["year"].isin([2020, 2024])]
df["region_short"] = df["region"].map(short).fillna(df["region"])

pivot = df.pivot_table(index="region_short", columns="year", values="speciesCount")

region_order = [
    "St. Croix (USVI)", "Puerto Rico", "Dry Tortugas",
    "St. Thomas/John (USVI)", "Flower Garden Banks", "SE Florida", "Florida Keys"
]
pivot = pivot.reindex([r for r in region_order if r in pivot.index])

fig, ax = plt.subplots(figsize=(14, 5))
im = ax.imshow(pivot.values, aspect="auto", cmap="RdYlGn", vmin=10, vmax=55)

ax.set_xticks(range(len(pivot.columns)))
ax.set_xticklabels(pivot.columns.astype(int), rotation=45)
ax.set_yticks(range(len(pivot.index)))
ax.set_yticklabels(pivot.index)

# write species count inside each cell
for i in range(len(pivot.index)):
    for j in range(len(pivot.columns)):
        val = pivot.values[i, j]
        if not np.isnan(val):
            ax.text(j, i, str(int(val)), ha="center", va="center", fontsize=9)

plt.colorbar(im, ax=ax, label="Distinct Species Count")
ax.set_title("Coral Species Richness Across US Reef Regions Over Time", fontsize=13, fontweight="bold")
ax.set_xlabel("Year")
plt.tight_layout()
plt.savefig("q5_richness_heatmap.png")
plt.show()
print("Saved: q5_richness_heatmap.png")


# Q4: Recovery Mismatch Index
# plots each region on two axes: abundance change (x) vs species richness change (y)
# quadrant position reveals whether recovery is genuine or misleading

results = collection.aggregate([
    { "$match": { "occurrenceStatus": "present", "organismQuantity": { "$gt": 0 }}},
    { "$group": {
        "_id": { "region": "$locality", "year": { "$year": "$eventDate" }},
        "totalAbundance":  { "$sum": "$organismQuantity" },
        "distinctSpecies": { "$addToSet": "$scientificName" }
    }},
    { "$project": {"region": "$_id.region", "year":  "$_id.year",
        "totalAbundance": 1, "speciesCount":   { "$size": "$distinctSpecies" }}},
    { "$sort": { "year": 1 }}
])

# pull region and year out of the grouped _id field
df = pd.DataFrame(results)
df["region"] = df["_id"].apply(lambda x: x["region"])
df["year"]   = df["_id"].apply(lambda x: x["year"])
df = df[df["year"] < 2024].sort_values("year")

# get first and last survey year per region
first = df.groupby("region").first().reset_index()[["region","year","totalAbundance","speciesCount"]]
first = first.rename(columns={"year":"firstYear","totalAbundance":"firstAb","speciesCount":"firstRichness"})

last = df.groupby("region").last().reset_index()[["region","year","totalAbundance","speciesCount"]]
last = last.rename(columns={"year":"lastYear","totalAbundance":"lastAb","speciesCount":"lastRichness"})

df = first.merge(last, on="region")
# positive = increased, negative = decreased
df["abChange"]       = df["lastAb"]       - df["firstAb"]
df["richnessChange"] = df["lastRichness"]  - df["firstRichness"]

def get_category(row):
    # assigns each region to one of four quadrants based on direction of change
    if row["abChange"] >= 0 and row["richnessChange"] >= 0:
        return "Strong Recovery"
    elif row["abChange"] >= 0 and row["richnessChange"] < 0:
        return "False Recovery"
    elif row["abChange"] < 0 and row["richnessChange"] >= 0:
        return "Diversity Shift"
    else:
        return "Overall Decline"

df["category"]     = df.apply(get_category, axis=1)
df["region_short"] = df["region"].map(short).fillna(df["region"])

cat_colors = {"Strong Recovery": "#006400", "False Recovery":  "#8B0000",
    "Diversity Shift": "#003366", "Overall Decline": "#4A4A4A", }

# manual offsets so region labels don't overlap near the center
label_offsets = {
    "Florida Keys": (8, 6),
    "Dry Tortugas":(8, 5),
    "SE Florida":(10, -10),
    "Flower Garden Banks":(10,  8),
    "St. Thomas/John (USVI)": (8, 5),
    "Puerto Rico":(8, 5),
    "St. Croix (USVI)":(8,  -2),
}

fig, ax = plt.subplots(figsize=(13, 7))

for cat, color in cat_colors.items():
    subset = df[df["category"] == cat]
    if subset.empty:
        continue
    ax.scatter(subset["abChange"], subset["richnessChange"],
               color=color, s=180, label=cat, edgecolors="black", linewidths=0.8, alpha=0.9)
    for _, row in subset.iterrows():
        offset = label_offsets.get(row["region_short"], (8, 5))
        ax.annotate(row["region_short"],
                    (row["abChange"], row["richnessChange"]),
                    textcoords="offset points", xytext=offset, fontsize=8.5)

# dividing lines that split the chart into the four quadrants
ax.axvline(0, color="black", linewidth=1, linestyle="--")
ax.axhline(0, color="black", linewidth=1, linestyle="--")

# quadrant labels in each corner using axis-relative coordinates
ax.text(0.78, 0.95, "Strong Recovery", transform=ax.transAxes, color="#006400", fontsize=9, alpha=0.8, va="top")
ax.text(0.78, 0.05, "False Recovery",  transform=ax.transAxes, color="#8B0000", fontsize=9, alpha=0.8, va="bottom")
ax.text(0.03, 0.95, "Diversity Shift", transform=ax.transAxes, color="#003366", fontsize=9, alpha=0.8, va="top")
ax.text(0.03, 0.05, "Overall Decline", transform=ax.transAxes, color="#4A4A4A", fontsize=9, alpha=0.8, va="bottom")

ax.set_title("Recovery Mismatch Index: Abundance Change vs Species Richness Change",
             fontsize=13, fontweight="bold")
ax.set_xlabel("Change in Total Coral Abundance")
ax.set_ylabel("Change in Distinct Species Count")
ax.legend(title="Recovery Category", fontsize=9, bbox_to_anchor=(1.02, 1), loc="upper left")
ax.grid(True, linestyle="--", alpha=0.4)
ax.margins(0.2)

plt.tight_layout()
plt.savefig("q4_recovery_mismatch.png", bbox_inches="tight")
plt.show()
print("Saved: q4_recovery_mismatch.png")


# Q9: 3rd Global Coral Bleaching Event (2014–2017)
# dual y-axis: species richness (left) and total abundance (right) over 2013–2019

results = collection.aggregate([
    { "$match": {
        "occurrenceStatus": "present",
        "eventDate": { "$gte": datetime(2013, 1, 1), "$lte": datetime(2019, 12, 31) }
    }},
    { "$group": {
        "_id":  { "$year": "$eventDate" },
        "distinctSpecies":  { "$addToSet": "$scientificName" },
        "totalAbundance":   { "$sum": "$organismQuantity" }
    }},
    { "$project": {
        "year": "$_id",
        "speciesCount": { "$size": "$distinctSpecies" },
        "totalAbundance": 1
    }},
    { "$sort": { "year": 1 }}
])

df = pd.DataFrame(results).sort_values("year")

fig, ax1 = plt.subplots(figsize=(12, 6))

ax1.axvspan(2014, 2017, color="coral", alpha=0.25, label="Bleaching Event (2014–2017)")
ax1.plot(df["year"], df["speciesCount"], marker="o", color="darkred", linewidth=2, label="Distinct Species")
ax1.set_xlabel("Year")
ax1.set_ylabel("Number of Distinct Species", color="darkred")
ax1.tick_params(axis="y", labelcolor="darkred")

# second y-axis so species count and abundance can share the same chart
ax2 = ax1.twinx()
ax2.plot(df["year"], df["totalAbundance"], marker="s", color="steelblue", linewidth=2, linestyle="--", label="Total Abundance")
ax2.set_ylabel("Total Coral Abundance", color="steelblue")
ax2.tick_params(axis="y", labelcolor="steelblue")

# merge legends from both axes into one
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left")

plt.title("3rd Global Coral Bleaching Event (2014–2017):\nImpact on Species Richness & Abundance", fontsize=13)
ax1.set_xticks(df["year"])
plt.tight_layout()
plt.savefig("q9_bleaching_event.png")
plt.show()
print("Saved: q9_bleaching_event.png")

client.close()
