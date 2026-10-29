"""Compare equivalent collaborative-filtering queries in MongoDB and Neo4j.

Measures client-observed query time, including receiving and consuming all
result rows. Run after both databases have been loaded. Results are saved to
outputs/recommendation_benchmark.json for inclusion in the generated report.
"""
import json
import os
import statistics
import time
from pathlib import Path

from neo4j import GraphDatabase
from pymongo import MongoClient

ROOT = Path(__file__).parent
OUT = ROOT / "outputs"
OUT.mkdir(exist_ok=True)
USER_ID = int(os.getenv("BENCHMARK_USER_ID", "1"))
WARMUPS = int(os.getenv("BENCHMARK_WARMUPS", "1"))
REPEATS = int(os.getenv("BENCHMARK_REPEATS", "5"))
MIN_RATING = 4.0
LIMIT = 10

mongo = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017"))
ratings = mongo["moviegraph"]["ratings"]
movies = mongo["moviegraph"]["movies"]
neo = GraphDatabase.driver(
    os.getenv("NEO4J_URI", "bolt://localhost:7687"),
    auth=(os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "moviegraph")),
)

seen_ids = [d["movieId"] for d in ratings.find({"userId": USER_ID}, {"movieId": 1, "_id": 0})]
if not seen_ids:
    raise RuntimeError(f"No ratings found for user {USER_ID}; load the dataset first.")

# MongoDB performs the same neighborhood steps as Neo4j:
# target user's high ratings -> other users sharing those movies -> their
# high-rated unseen movies -> rank by distinct supporting users, then mean rating.
mongo_pipeline = [
    {"$match": {"userId": USER_ID, "rating": {"$gte": MIN_RATING}}},
    {"$lookup": {
        "from": "ratings",
        "let": {"likedMovie": "$movieId"},
        "pipeline": [{"$match": {"$expr": {"$and": [
            {"$eq": ["$movieId", "$$likedMovie"]},
            {"$ne": ["$userId", USER_ID]},
            {"$gte": ["$rating", MIN_RATING]},
        ]}}}],
        "as": "neighbors",
    }},
    {"$unwind": "$neighbors"},
    {"$lookup": {
        "from": "ratings",
        "let": {"neighborId": "$neighbors.userId"},
        "pipeline": [{"$match": {"$expr": {"$and": [
            {"$eq": ["$userId", "$$neighborId"]},
            {"$gte": ["$rating", MIN_RATING]},
        ]}}}],
        "as": "candidateRatings",
    }},
    {"$unwind": "$candidateRatings"},
    {"$match": {"candidateRatings.movieId": {"$nin": seen_ids}}},
    {"$group": {
        "_id": "$candidateRatings.movieId",
        "supportingUsers": {"$addToSet": "$neighbors.userId"},
        "predictedRating": {"$avg": "$candidateRatings.rating"},
    }},
    {"$set": {"sharedUsers": {"$size": "$supportingUsers"}}},
    {"$sort": {"sharedUsers": -1, "predictedRating": -1, "_id": 1}},
    {"$limit": LIMIT},
    {"$lookup": {"from": "movies", "localField": "_id", "foreignField": "movieId", "as": "movie"}},
    {"$unwind": "$movie"},
    {"$project": {"_id": 0, "movieId": "$_id", "recommendation": "$movie.title", "sharedUsers": 1, "predictedRating": 1}},
]

neo_query = """
MATCH (u:User {userId: $user_id})-[r1:RATED]->(liked:Movie)
WHERE r1.rating >= $min_rating
MATCH (other:User)-[r2:RATED]->(liked)
WHERE other <> u AND r2.rating >= $min_rating
MATCH (other)-[r3:RATED]->(candidate:Movie)
WHERE r3.rating >= $min_rating
  AND NOT EXISTS { MATCH (u)-[:RATED]->(candidate) }
WITH candidate, count(DISTINCT other) AS sharedUsers,
     avg(r3.rating) AS predictedRating
RETURN candidate.movieId AS movieId, candidate.title AS recommendation,
       sharedUsers, round(predictedRating * 100) / 100.0 AS predictedRating
ORDER BY sharedUsers DESC, predictedRating DESC, movieId ASC
LIMIT $limit
"""

def mongo_query():
    return list(ratings.aggregate(mongo_pipeline, allowDiskUse=True))

def neo_query_run():
    with neo.session() as session:
        return [dict(r) for r in session.run(neo_query, user_id=USER_ID, min_rating=MIN_RATING, limit=LIMIT)]

def measure(fn):
    for _ in range(WARMUPS):
        fn()
    samples, last = [], []
    for _ in range(REPEATS):
        start = time.perf_counter()
        last = fn()
        samples.append((time.perf_counter() - start) * 1000)
    return samples, last

mongo_ms, mongo_rows = measure(mongo_query)
neo_ms, neo_rows = measure(neo_query_run)

def normalize(rows):
    return [{"movieId": int(r.get("movieId", r.get("_id"))),
             "recommendation": r["recommendation"],
             "sharedUsers": int(r["sharedUsers"]),
             "predictedRating": round(float(r["predictedRating"]), 2)} for r in rows]

mongo_results, neo_results = normalize(mongo_rows), normalize(neo_rows)
same_ordered_recommendations = [r["movieId"] for r in mongo_results] == [r["movieId"] for r in neo_results]
payload = {
    "dataset": "MovieLens ml-latest-small",
    "user_id": USER_ID,
    "minimum_rating": MIN_RATING,
    "top_k": LIMIT,
    "warmups": WARMUPS,
    "repetitions": REPEATS,
    "timing_method": "Client-observed wall-clock milliseconds; includes query execution and full result consumption; warm-up excluded.",
    "mongo": {"samples_ms": [round(x, 3) for x in mongo_ms], "median_ms": round(statistics.median(mongo_ms), 3), "min_ms": round(min(mongo_ms), 3), "results": mongo_results},
    "neo4j": {"samples_ms": [round(x, 3) for x in neo_ms], "median_ms": round(statistics.median(neo_ms), 3), "min_ms": round(min(neo_ms), 3), "results": neo_results},
    "same_ordered_recommendations": same_ordered_recommendations,
}
(OUT / "recommendation_benchmark.json").write_text(json.dumps(payload, indent=2))
print(f"Benchmark: user={USER_ID}, minimum rating={MIN_RATING}, top {LIMIT}, {REPEATS} measured runs after {WARMUPS} warm-up")
print(f"MongoDB median: {payload['mongo']['median_ms']} ms; samples: {payload['mongo']['samples_ms']}")
print(f"Neo4j median:   {payload['neo4j']['median_ms']} ms; samples: {payload['neo4j']['samples_ms']}")
print("Same ordered movie recommendations:", same_ordered_recommendations)
print("Saved outputs/recommendation_benchmark.json")
print("Top MongoDB recommendations:")
for row in mongo_results: print(row)
print("Top Neo4j recommendations:")
for row in neo_results: print(row)
neo.close()
mongo.close()
