# HW 5: NoSQL R&D Project (GROUP PROJECT)
# BY: Anushka
# Date: 6/10/2026

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")
collection = client["coral_reef"]["occurrences"]


short = {
    "Florida Keys, Florida":                          "Florida Keys",
    "Southeast Florida":                              "SE Florida",
    "Dry Tortugas, Florida":                          "Dry Tortugas",
    "Puerto Rico":                                    "Puerto Rico",
    "St. Croix, US Virgin Islands":                   "St. Croix (USVI)",
    "St. Thomas and St. John, US Virgin Islands":     "St. Thomas/John (USVI)",
    "Flower Garden Banks, Gulf of Mexico":            "Flower Garden Banks",
}


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
# exclude 2024 (incomplete) and 2020 (COVID reduced surveys distort absence rate)
pivot = pivot[(pivot["year"] <= 2023) & (pivot["year"] != 2020)]
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
plt.xticks([y for y in range(2013, 2024) if y != 2020])
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


# Q7: Coral abundance by depth band over time

results = collection.aggregate([
    # filter out records with no depth recorded — they would wrongly default to "Deep (20m+)"
    { "$match": { "occurrenceStatus": "present", "organismQuantity": { "$gt": 0 },
                  "minimumDepthInMeters": { "$ne": None } }},
    { "$group": {
        "_id": {
            "depthBand": { "$switch": {
                "branches": [
                    { "case": { "$lt": ["$minimumDepthInMeters", 10] }, "then": "Shallow (0-10m)" },
                    { "case": { "$lt": ["$minimumDepthInMeters", 20] }, "then": "Mid (10-20m)" }
                ],
                "default": "Deep (20m+)"
            }},
            "year": { "$year": "$eventDate" }
        },
        "totalAbundance": { "$sum": "$organismQuantity" }
    }},
    { "$sort": { "_id.year": 1 }}
])

df = pd.DataFrame(results)
df["year"]      = df["_id"].apply(lambda x: x["year"])
df["depthBand"] = df["_id"].apply(lambda x: x["depthBand"])
df = df[df["year"] != 2024]

colors_depth = {
    "Shallow (0-10m)": "#28b038",
    "Mid (10-20m)":    "#4f99d5",
    "Deep (20m+)":     "#2e4057"
}

plt.figure(figsize=(11, 5))
for band, color in colors_depth.items():
    subset = df[df["depthBand"] == band].sort_values("year")
    plt.plot(subset["year"], subset["totalAbundance"], marker="o", label=band, color=color, linewidth=2)

plt.title("Coral Abundance by Depth Band Over Time", fontsize=13)
plt.xlabel("Year")
plt.ylabel("Total Abundance")
plt.legend()
plt.xticks(sorted(df["year"].unique()))
plt.grid(axis="y", linestyle="--", alpha=0.5)
plt.tight_layout()
plt.savefig("q7_depth_over_time.png")
plt.show()
print("Saved: q7_depth_over_time.png")


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

colors = ["#d62728" if 2014 <= y <= 2017 else "#4682b4" for y in df["year"]]

fig, ax = plt.subplots(figsize=(11, 5))
ax.bar(df["year"], df["locationCount"], color=colors)
ax.set_title("Are Coral Populations Shrinking Geographically Over Time?", fontsize=13, fontweight="bold")
ax.set_xlabel("Year")
ax.set_ylabel("Number of Unique Survey Locations With Coral Present")
ax.set_xticks(df["year"])
ax.tick_params(axis="x", rotation=45)
ax.axvspan(2013.5, 2017.5, color="coral", alpha=0.15, label="Bleaching Event (2014-2017)")
ax.legend(fontsize=9)
plt.tight_layout()
plt.savefig("q6_geographic_fragmentation.png")
plt.show()
print("Saved: q6_geographic_fragmentation.png")


# Survey Effort: Number of observations per region per year

q_survey = collection.aggregate([
    { "$group": {
        "_id": { "region": "$locality", "year": { "$year": "$eventDate" }},
        "obsCount": { "$sum": 1 }
    }},
    { "$sort": { "_id.year": 1 }}
])

df_survey = pd.DataFrame(list(q_survey))
df_survey["region"] = df_survey["_id"].apply(lambda x: x["region"])
df_survey["year"]   = df_survey["_id"].apply(lambda x: x["year"])
df_survey = df_survey[df_survey["year"] <= 2023]
df_survey["region_short"] = df_survey["region"].map(short).fillna(df_survey["region"])

pivot_survey = df_survey.pivot_table(index="year", columns="region_short", values="obsCount", fill_value=0)

colors_survey = ["#8a1c1c","#c0392b","#e67e22","#2980b9","#148f77","#0d8b0d","#27ae60"]

fig, ax = plt.subplots(figsize=(12, 6))
pivot_survey.plot(kind="bar", stacked=True, ax=ax, color=colors_survey, width=0.7)
ax.set_title("Survey Effort: Number of Observations per Region per Year", fontsize=13)
ax.set_xlabel("Year")
ax.set_ylabel("Number of Observations")
ax.legend(fontsize=8, bbox_to_anchor=(1.01, 1), loc="upper left")
ax.grid(axis="y", linestyle="--", alpha=0.5)
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig("survey_effort.png")
plt.show()
print("Saved: survey_effort.png")


client.close()