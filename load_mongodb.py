import os
from pathlib import Path
import pandas as pd
from pymongo import MongoClient

ROOT = Path(__file__).parent; DATA = ROOT / "ml-latest-small"
if not DATA.exists(): raise FileNotFoundError("Extract ml-latest-small.zip into this folder first.")
db = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017"))["moviegraph"]
movies = pd.read_csv(DATA / "movies.csv").to_dict("records")
ratings = pd.read_csv(DATA / "ratings.csv").to_dict("records")
tags = pd.read_csv(DATA / "tags.csv").to_dict("records")
for name, rows in [("movies", movies), ("ratings", ratings), ("tags", tags)]:
    db[name].delete_many({}); db[name].insert_many(rows)
db.ratings.create_index([("movieId", 1), ("rating", -1)])
db.ratings.create_index([("userId", 1), ("rating", -1)])
pipeline = [{"$group": {"_id": "$movieId", "ratingCount": {"$sum": 1}, "averageRating": {"$avg": "$rating"}}}, {"$match": {"ratingCount": {"$gte": 50}}}, {"$sort": {"averageRating": -1, "ratingCount": -1}}, {"$limit": 10}, {"$lookup": {"from": "movies", "localField": "_id", "foreignField": "movieId", "as": "movie"}}, {"$unwind": "$movie"}, {"$project": {"_id": 0, "title": "$movie.title", "averageRating": 1, "ratingCount": 1}}]
print("MongoDB top movies:")
for row in db.ratings.aggregate(pipeline): print(row)
