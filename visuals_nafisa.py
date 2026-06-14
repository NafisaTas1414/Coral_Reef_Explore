import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")
collection = client["coral_reef"]["occurrences"]


# Q1: Species Winners vs Losers

def get_species_change(sort_order, limit=10):
    return list(collection.aggregate([
        { "$match": { "occurrenceStatus": "present", "organismQuantity": { "$gt": 0 } }},
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
        { "$project": {
            "species": "$_id",
            "firstAbundance": 1, "lastAbundance": 1,
            "change": { "$subtract": ["$lastAbundance", "$firstAbundance"] }
        }},
        { "$sort": { "change": sort_order }},
        { "$limit": limit }
    ]))

winners = pd.DataFrame(get_species_change(sort_order=-1))
losers  = pd.DataFrame(get_species_change(sort_order=1))

fig, (ax_left, ax_right) = plt.subplots(1, 2, figsize=(16, 7))

ax_left.barh(winners["species"], winners["change"], color="#2ca02c")
ax_left.set_title("Coral Species on the Rise\n(Top 10 Growing Species)", fontsize=12)
ax_left.set_xlabel("Increase in Individual Corals Counted")
ax_left.invert_yaxis()

ax_right.barh(losers["species"], losers["change"], color="#d62728")
ax_right.set_title("Coral Species in Decline\n(Top 10 Shrinking Species)", fontsize=12)
ax_right.set_xlabel("Decrease in Individual Corals Counted")
ax_right.invert_yaxis()

fig.suptitle("Which Coral Species Are Thriving and Which Are Disappearing? (First vs Most Recent Survey)",
             fontsize=13, fontweight="bold")
plt.tight_layout()
plt.savefig("q1_winners_vs_losers.png")
plt.show()
print("Saved: q1_winners_vs_losers.png")


# Q6 (Geographic): Are corals found in fewer locations over time?

results = collection.aggregate([
    { "$match": { "occurrenceStatus": "present", "organismQuantity": { "$gt": 0 } }},
    { "$group": {
        "_id": { "$year": "$eventDate" },
        "uniqueLocations": { "$addToSet": {
            "lat": { "$round": ["$decimalLatitude", 1] },
            "lng": { "$round": ["$decimalLongitude", 1] }
        }}
    }},
    { "$project": {
        "year":          "$_id",
        "locationCount": { "$size": "$uniqueLocations" }
    }},
    { "$sort": { "year": 1 }}
])

df = pd.DataFrame(results)
df = df[~df["year"].isin([2020, 2024])]

# red bars for bleaching years, blue for others
colors = ["#d62728" if 2014 <= y <= 2017 else "#4682b4" for y in df["year"]]

fig, ax = plt.subplots(figsize=(11, 5))
ax.bar(df["year"], df["locationCount"], color=colors)
ax.set_title("Are Coral Populations Shrinking Geographically Over Time?", fontsize=13, fontweight="bold")
ax.set_xlabel("Year")
ax.set_ylabel("Number of Unique Survey Locations With Coral Present")
ax.set_xticks(df["year"])
ax.tick_params(axis="x", rotation=45)
ax.axvspan(2013.5, 2017.5, color="coral", alpha=0.15, label="Bleaching Event (2014–2017)")
ax.legend(fontsize=9)
plt.tight_layout()
plt.savefig("q6_geographic_fragmentation.png")
plt.show()
print("Saved: q6_geographic_fragmentation.png")


# Q3: Species change by region (first vs most recent survey)

results = collection.aggregate([
    { "$match": { "occurrenceStatus": "present" }},
    { "$group": {
        "_id": { "region": "$locality", "year": { "$year": "$eventDate" } },
        "distinctSpecies": { "$addToSet": "$scientificName" }
    }},
    { "$project": {
        "region":       "$_id.region",
        "year":         "$_id.year",
        "speciesCount": { "$size": "$distinctSpecies" }
    }},
    { "$sort": { "year": 1 }},
    { "$group": {
        "_id":        "$region",
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

short = {
    "Florida Keys, Florida":                          "Florida Keys",
    "Southeast Florida":                              "SE Florida",
    "Dry Tortugas, Florida":                          "Dry Tortugas",
    "Puerto Rico":                                    "Puerto Rico",
    "St. Croix, US Virgin Islands":                   "St. Croix (USVI)",
    "St. Thomas and St. John, US Virgin Islands":     "St. Thomas/John (USVI)",
    "Flower Garden Banks, Gulf of Mexico":            "Flower Garden Banks",
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

results = collection.aggregate([
    { "$match": { "occurrenceStatus": "present", "organismQuantity": { "$gt": 0 }}},
    { "$group": {
        "_id": { "region": "$locality", "year": { "$year": "$eventDate" }},
        "totalAbundance":  { "$sum": "$organismQuantity" },
        "distinctSpecies": { "$addToSet": "$scientificName" }
    }},
    { "$project": {
        "region":         "$_id.region",
        "year":           "$_id.year",
        "totalAbundance": 1,
        "speciesCount":   { "$size": "$distinctSpecies" }
    }},
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

cat_colors = {
    "Strong Recovery": "#006400",
    "False Recovery":  "#8B0000",
    "Diversity Shift": "#003366",
    "Overall Decline": "#4A4A4A",
}

fig, ax = plt.subplots(figsize=(12, 7))

for cat, color in cat_colors.items():
    subset = df[df["category"] == cat]
    if subset.empty:
        continue
    ax.scatter(subset["abChange"], subset["richnessChange"],
               color=color, s=150, label=cat, edgecolors="black", linewidths=0.8)
    for _, row in subset.iterrows():
        ax.annotate(row["region_short"],
                    (row["abChange"], row["richnessChange"]),
                    textcoords="offset points", xytext=(8, 5), fontsize=9)

ax.axvline(0, color="black", linewidth=1, linestyle="--")
ax.axhline(0, color="black", linewidth=1, linestyle="--")

# quadrant labels in each corner
ax.text(0.78, 0.95, "Strong Recovery", transform=ax.transAxes, color="#006400", fontsize=9, alpha=0.8, va="top")
ax.text(0.78, 0.05, "False Recovery",  transform=ax.transAxes, color="#8B0000", fontsize=9, alpha=0.8, va="bottom")
ax.text(0.03, 0.95, "Diversity Shift", transform=ax.transAxes, color="#003366", fontsize=9, alpha=0.8, va="top")
ax.text(0.03, 0.05, "Overall Decline", transform=ax.transAxes, color="#4A4A4A", fontsize=9, alpha=0.8, va="bottom")

ax.set_title("Recovery Mismatch Index: Abundance Change vs Species Richness Change",
             fontsize=13, fontweight="bold")
ax.set_xlabel("Change in Total Coral Abundance")
ax.set_ylabel("Change in Distinct Species Count")
ax.legend(title="Recovery Category", fontsize=9)
ax.grid(True, linestyle="--", alpha=0.4)
plt.tight_layout()
plt.savefig("q4_recovery_mismatch.png")
plt.show()
print("Saved: q4_recovery_mismatch.png")

print("\nRecovery Mismatch Summary")
for _, row in df.sort_values("category").iterrows():
    print(f"{row['region_short']}: abundance change={int(row['abChange'])}, "
          f"richness change={int(row['richnessChange'])}, category={row['category']}")


# Q6 (Species): Top 10 most declined species

results = collection.aggregate([
    { "$match": { "occurrenceStatus": "present", "organismQuantity": { "$gt": 0 } }},
    { "$group": {
        "_id": { "species": "$scientificName", "year": { "$year": "$eventDate" } },
        "totalAbundance": { "$sum": "$organismQuantity" }
    }},
    { "$sort": { "_id.year": 1 }},
    { "$group": {
        "_id":            "$_id.species",
        "firstAbundance": { "$first": "$totalAbundance" },
        "lastAbundance":  { "$last":  "$totalAbundance" }
    }},
    { "$project": {
        "species":        "$_id",
        "firstAbundance": 1, "lastAbundance": 1,
        "change":         { "$subtract": ["$lastAbundance", "$firstAbundance"] }
    }},
    { "$sort": { "change": 1 }},
    { "$limit": 10 }
])

df = pd.DataFrame(results)
# y positions for each species, offset slightly so bars sit side by side
y = np.arange(len(df))
bar_height = 0.35

fig, ax = plt.subplots(figsize=(12, 7))
ax.barh(y + bar_height / 2, df["firstAbundance"], bar_height, label="First Survey Year", color="skyblue")
ax.barh(y - bar_height / 2, df["lastAbundance"],  bar_height, label="Last Survey Year",  color="salmon")
ax.set_yticks(y)
ax.set_yticklabels(df["species"], fontstyle="italic")
ax.set_xlabel("Total Abundance (Individual Corals Counted)")
ax.set_title("Top 10 Most Declined Species: First vs Most Recent Survey", fontsize=13)
ax.legend()
plt.tight_layout()
plt.savefig("q6_most_at_risk_species.png")
plt.show()
print("Saved: q6_most_at_risk_species.png")


# Q9: 3rd Global Coral Bleaching Event (2014–2017)

results = collection.aggregate([
    { "$match": {
        "occurrenceStatus": "present",
        "eventDate": { "$gte": datetime(2013, 1, 1), "$lte": datetime(2019, 12, 31) }
    }},
    { "$group": {
        "_id":              { "$year": "$eventDate" },
        "distinctSpecies":  { "$addToSet": "$scientificName" },
        "totalAbundance":   { "$sum": "$organismQuantity" }
    }},
    { "$project": {
        "year":         "$_id",
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
