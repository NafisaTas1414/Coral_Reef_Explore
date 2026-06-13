import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")
collection = client["coral_reef"]["occurrences"]


# Q4: Top 10 species by % abundance loss (first vs last survey year)

q4 = collection.aggregate([
    { "$match": { "occurrenceStatus": "present", "organismQuantity": { "$gt": 0 }}},
    { "$group": {
        "_id": { "species": "$scientificName", "year": { "$year": "$eventDate" }},
        "totalAbundance": { "$sum": "$organismQuantity" }
    }},
    { "$sort": { "_id.year": 1 }},
    { "$group": {
        "_id": "$_id.species",
        "firstAbundance": { "$first": "$totalAbundance" },
        "lastAbundance":  { "$last": "$totalAbundance" }
    }}
])

df_q4 = pd.DataFrame(list(q4))
df_q4["species"]  = df_q4["_id"]
df_q4["pct_loss"] = ((df_q4["firstAbundance"] - df_q4["lastAbundance"]) / df_q4["firstAbundance"] * 100).round(1)
df_q4 = df_q4[df_q4["pct_loss"] > 0].sort_values("pct_loss", ascending=False).head(10)
df_q4 = df_q4.sort_values("pct_loss", ascending=True)

plt.figure(figsize=(11, 6))
bars = plt.barh(df_q4["species"], df_q4["pct_loss"], color="steelblue")
for bar, val in zip(bars, df_q4["pct_loss"]):
    plt.text(val + 0.5, bar.get_y() + bar.get_height() / 2,
             f"{val:.1f}%", va="center", fontsize=9)
plt.title("Top 10 Species by % Abundance Loss (First vs Most Recent Survey)", fontsize=13)
plt.xlabel("% Decline in Abundance")
plt.yticks(fontstyle="italic")
plt.xlim(0, 115)
plt.grid(axis="x", linestyle="--", alpha=0.5)
plt.tight_layout()
plt.savefig("q4_pct_loss_species.png")
plt.show()
print("Saved: q4_pct_loss_species.png")


# Q5: Absence rate per region per year (line chart)

q5 = collection.aggregate([
    { "$group": {
        "_id": { "region": "$locality", "year": { "$year": "$eventDate" }, "status": "$occurrenceStatus" },
        "count": { "$sum": 1 }
    }}
])
df_q5 = pd.DataFrame(list(q5))
df_q5["region"] = df_q5["_id"].apply(lambda x: x["region"])
df_q5["year"]   = df_q5["_id"].apply(lambda x: x["year"])
df_q5["status"] = df_q5["_id"].apply(lambda x: x["status"])

pivot = df_q5.pivot_table(index=["region","year"], columns="status", values="count", fill_value=0).reset_index()
pivot.columns.name = None
if "absent" not in pivot.columns:
    pivot["absent"] = 0
if "present" not in pivot.columns:
    pivot["present"] = 0
pivot["absence_pct"] = (pivot["absent"] / (pivot["absent"] + pivot["present"]) * 100).round(1)
pivot = pivot[pivot["year"] <= 2023]

short = {
    "Florida Keys, Florida":                          "Florida Keys",
    "Southeast Florida":                              "SE Florida",
    "Dry Tortugas, Florida":                          "Dry Tortugas",
    "Puerto Rico":                                    "Puerto Rico",
    "St. Croix, US Virgin Islands":                   "St. Croix (USVI)",
    "St. Thomas and St. John, US Virgin Islands":     "St. Thomas/John (USVI)",
    "Flower Garden Banks, Gulf of Mexico":            "Flower Garden Banks",
}
pivot["region_short"] = pivot["region"].map(short).fillna(pivot["region"])

region_order  = list(short.values())
colors_q5     = ["#8a1c1c","#c0392b","#e67e22","#2980b9","#148f77","#0d8b0d","#27ae60"]
color_map     = dict(zip(region_order, colors_q5))

plt.figure(figsize=(11, 5))
for region in region_order:
    subset = pivot[pivot["region_short"] == region].sort_values("year")
    if subset.empty:
        continue
    plt.plot(subset["year"], subset["absence_pct"], marker="o", linewidth=2,
             label=region, color=color_map.get(region, "grey"))

plt.title("Absence Rate (%) by Region Over Time", fontsize=13)
plt.xlabel("Year")
plt.ylabel("% Observations Recorded as Absent")
plt.xticks(range(2013, 2024))
plt.legend(fontsize=8, loc="upper left")
plt.grid(axis="y", linestyle="--", alpha=0.5)
plt.tight_layout()
plt.savefig("q5_absence_rate.png")
plt.show()
print("Saved: q5_absence_rate.png")


# Q8: Recovery signals -- grouped bar chart, abundance by region, first vs last survey year

q8 = collection.aggregate([
    { "$match": { "occurrenceStatus": "present", "organismQuantity": { "$gt": 0 }}},
    { "$group": {
        "_id": { "region": "$locality", "year": { "$year": "$eventDate" }},
        "totalAbundance": { "$sum": "$organismQuantity" }
    }},
    { "$sort": { "_id.year": 1 }}
])
df_q8 = pd.DataFrame(list(q8))
df_q8["region"] = df_q8["_id"].apply(lambda x: x["region"])
df_q8["year"]   = df_q8["_id"].apply(lambda x: x["year"])
df_q8 = df_q8[df_q8["year"] <= 2023]

# get first and last year per region
first = df_q8.groupby("region").first().reset_index()[["region","year","totalAbundance"]].rename(columns={"year":"firstYear","totalAbundance":"firstAb"})
last  = df_q8.groupby("region").last().reset_index()[["region","year","totalAbundance"]].rename(columns={"year":"lastYear","totalAbundance":"lastAb"})
df_fl = first.merge(last, on="region")
df_fl["region_short"] = df_fl["region"].map(short).fillna(df_fl["region"])
df_fl = df_fl.sort_values("firstAb", ascending=True)

y          = np.arange(len(df_fl))
bar_height = 0.35

fig, ax = plt.subplots(figsize=(11, 6))
ax.barh(y + bar_height / 2, df_fl["firstAb"], bar_height, label="First Survey Year",  color="skyblue")
ax.barh(y - bar_height / 2, df_fl["lastAb"],  bar_height, label="Most Recent Survey", color="salmon")
ax.set_yticks(y)
ax.set_yticklabels(df_fl["region_short"])
ax.set_xlabel("Total Coral Abundance")
ax.set_title("Coral Abundance by Region: First vs Most Recent Survey (Recovery Signals)", fontsize=13)
ax.legend()
ax.grid(axis="x", linestyle="--", alpha=0.5)
plt.tight_layout()
plt.savefig("q8_recovery_signals.png")
plt.show()
print("Saved: q8_recovery_signals.png")


# Q2: Species richness per region over time

q2 = collection.aggregate([
    { "$match": { "occurrenceStatus": "present" }},
    { "$group": {
        "_id": { "region": "$locality", "year": { "$year": "$eventDate" }},
        "distinctSpecies": { "$addToSet": "$scientificName" }
    }},
    { "$project": {
        "region": "$_id.region",
        "year":   "$_id.year",
        "speciesCount": { "$size": "$distinctSpecies" }
    }},
    { "$sort": { "year": 1 }}
])

df_q2 = pd.DataFrame(list(q2))
df_q2["region"] = df_q2["_id"].apply(lambda x: x["region"])
df_q2["year"]   = df_q2["_id"].apply(lambda x: x["year"])
df_q2 = df_q2[df_q2["year"] <= 2023]

region_colors = {
    "Florida Keys, Florida":                          "#2ecc71",
    "Southeast Florida":                              "#27ae60",
    "Dry Tortugas, Florida":                          "#16a085",
    "Puerto Rico":                                    "#8e44ad",
    "St. Croix, US Virgin Islands":                   "#c0392b",
    "St. Thomas and St. John, US Virgin Islands":     "#e67e22",
    "Flower Garden Banks, Gulf of Mexico":            "steelblue",
}

plt.figure(figsize=(11, 5))
for region, grp in df_q2.groupby("region"):
    grp   = grp.sort_values("year")
    label = short.get(region, region)
    plt.plot(grp["year"], grp["speciesCount"], marker="o", linewidth=2,
             label=label, color=region_colors.get(region, "grey"))

plt.title("Distinct Coral Species per Region Over Time", fontsize=13)
plt.xlabel("Year")
plt.ylabel("Number of Distinct Species")
plt.xticks(range(2013, 2024))
plt.legend(fontsize=8, loc="lower left")
plt.grid(axis="y", linestyle="--", alpha=0.5)
plt.tight_layout()
plt.savefig("q2_richness_by_region.png")
plt.show()
print("Saved: q2_richness_by_region.png")

client.close()