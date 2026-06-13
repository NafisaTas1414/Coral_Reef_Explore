import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pymongo import MongoClient

# Connect to MongoDB
client = MongoClient("mongodb://localhost:27017/")
collection = client["coral_reef"]["occurrences"]


# Q1: Species Winners vs Losers

def get_winners_losers(sort_order, limit=10):
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
            "lastAbundance":  { "$last": "$totalAbundance" }
        }},
        { "$project": {
            "species": "$_id",
            "firstAbundance": 1, "lastAbundance": 1,
            "change": { "$subtract": ["$lastAbundance", "$firstAbundance"] }
        }},
        { "$sort": { "change": sort_order }},
        { "$limit": limit }
    ]))

winners = pd.DataFrame(get_winners_losers(sort_order=-1))
losers  = pd.DataFrame(get_winners_losers(sort_order=1))

fig, (ax_left, ax_right) = plt.subplots(1, 2, figsize=(16, 7))

# Winners — left panel
ax_left.barh(winners["species"], winners["change"], color="#2ca02c")
ax_left.set_title("Coral Species on the Rise\n(Top 10 Growing Species)", fontsize=12)
ax_left.set_xlabel("Increase in Individual Corals Counted")
ax_left.invert_yaxis()
for spine in ["top", "right"]: ax_left.spines[spine].set_visible(False)

# Losers — right panel
ax_right.barh(losers["species"], losers["change"], color="#d62728")
ax_right.set_title("Coral Species in Decline\n(Top 10 Shrinking Species)", fontsize=12)
ax_right.set_xlabel("Decrease in Individual Corals Counted")
ax_right.invert_yaxis()
for spine in ["top", "right"]: ax_right.spines[spine].set_visible(False)

fig.suptitle("Which Coral Species Are Thriving and Which Are Disappearing? (First vs Most Recent Survey)", fontsize=13, fontweight="bold")
plt.tight_layout()
plt.savefig("q1_winners_vs_losers.png")
plt.show()
print("Saved: q1_winners_vs_losers.png")


# Q6: Geographic fragmentation — are corals found in fewer locations over time?

q6_geo = collection.aggregate([
    { "$match": { "occurrenceStatus": "present", "organismQuantity": { "$gt": 0 } }},
    { "$group": {
        "_id": { "$year": "$eventDate" },
        "uniqueLocations": { "$addToSet": {
            "lat": { "$round": ["$decimalLatitude", 1] },
            "lng": { "$round": ["$decimalLongitude", 1] }
        }},
        "allLats": { "$push": "$decimalLatitude" },
        "allLngs": { "$push": "$decimalLongitude" }
    }},
    { "$project": {
        "year": "$_id",
        "uniqueLocationCount": { "$size": "$uniqueLocations" },
        "latSpread": { "$subtract": [{ "$max": "$allLats" }, { "$min": "$allLats" }] },
        "lngSpread": { "$subtract": [{ "$max": "$allLngs" }, { "$min": "$allLngs" }] }
    }},
    { "$sort": { "year": 1 }}
])

df_geo = pd.DataFrame(q6_geo)
df_geo = df_geo[~df_geo["year"].isin([2020, 2024])]

fig, ax = plt.subplots(figsize=(11, 5))

colors_bar = ["#d62728" if y >= 2014 and y <= 2017 else "#4682b4" for y in df_geo["year"]]
ax.bar(df_geo["year"], df_geo["uniqueLocationCount"], color=colors_bar)
ax.set_title("Are Coral Populations Shrinking Geographically Over Time?", fontsize=13, fontweight="bold")
ax.set_xlabel("Year")
ax.set_ylabel("Number of Unique Survey Locations With Coral Present")
ax.set_xticks(df_geo["year"])
ax.tick_params(axis="x", rotation=45)
ax.axvspan(2013.5, 2017.5, color="coral", alpha=0.15, label="Bleaching Event (2014–2017)")
ax.legend(fontsize=9)
for spine in ["top", "right"]: ax.spines[spine].set_visible(False)

plt.tight_layout()
plt.savefig("q6_geographic_fragmentation.png")
plt.show()
print("Saved: q6_geographic_fragmentation.png")


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
        "lastCount":  { "$last": "$speciesCount" }  }},
    { "$project": {
        "region": "$_id",
        "change": { "$subtract": ["$lastCount", "$firstCount"] } }},
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
        "_id": "$_id.species", "firstAbundance": { "$first": "$totalAbundance" }, "lastAbundance":  { "$last": "$totalAbundance" }
    }},
    { "$project": {"species": "$_id", "firstAbundance": 1, "lastAbundance": 1, "change": { "$subtract": ["$lastAbundance", "$firstAbundance"] }
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


# Q9: Impact of the 3rd Global Coral Bleaching Event (2014-2017)

q9 = collection.aggregate([
    { "$match": { "occurrenceStatus": "present",
        "eventDate": { "$gte": __import__("datetime").datetime(2013,1,1), "$lte": __import__("datetime").datetime(2019,12,31) }
    }},
    { "$group": {
        "_id": { "$year": "$eventDate" },
        "distinctSpecies": { "$addToSet": "$scientificName" },
        "totalAbundance":  { "$sum": "$organismQuantity" }
    }},
    { "$project": { "year": "$_id", "speciesCount": { "$size": "$distinctSpecies" }, "totalAbundance": 1 }},
    { "$sort": { "year": 1 }}
])

df_q9 = pd.DataFrame(q9).sort_values("year")

fig, ax1 = plt.subplots(figsize=(12, 6))

# shaded bleaching window
ax1.axvspan(2014, 2017, color="coral", alpha=0.25, label="Bleaching Event (2014–2017)")

# line 1 — species count (left axis)
ax1.plot(df_q9["year"], df_q9["speciesCount"], marker="o", color="darkred", linewidth=2, label="Distinct Species")
ax1.set_xlabel("Year")
ax1.set_ylabel("Number of Distinct Species", color="darkred")
ax1.tick_params(axis="y", labelcolor="darkred")

# line 2 — abundance (right axis)
ax2 = ax1.twinx()
ax2.plot(df_q9["year"], df_q9["totalAbundance"], marker="s", color="steelblue", linewidth=2, linestyle="--", label="Total Abundance")
ax2.set_ylabel("Total Coral Abundance", color="steelblue")
ax2.tick_params(axis="y", labelcolor="steelblue")

# combine legends from both axes
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left")

plt.title("3rd Global Coral Bleaching Event (2014–2017):\nImpact on Species Richness & Abundance", fontsize=13)
ax1.set_xticks(df_q9["year"])

plt.tight_layout()
plt.savefig("q9_bleaching_event.png")
plt.show()
print("Saved: q9_bleaching_event.png")

client.close()
