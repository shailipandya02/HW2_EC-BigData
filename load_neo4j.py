import os
from pathlib import Path
import pandas as pd
from neo4j import GraphDatabase

ROOT = Path(__file__).parent; DATA = ROOT / "ml-latest-small"
if not DATA.exists(): raise FileNotFoundError("Extract ml-latest-small.zip into this folder first.")
driver = GraphDatabase.driver(os.getenv("NEO4J_URI", "bolt://localhost:7687"), auth=(os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "moviegraph")))
movies = pd.read_csv(DATA / "movies.csv"); ratings = pd.read_csv(DATA / "ratings.csv")
with driver.session() as s:
    s.run("MATCH (n) DETACH DELETE n")
    s.run("CREATE CONSTRAINT movie_id IF NOT EXISTS FOR (m:Movie) REQUIRE m.movieId IS UNIQUE")
    s.run("CREATE CONSTRAINT user_id IF NOT EXISTS FOR (u:User) REQUIRE u.userId IS UNIQUE")
    s.run("UNWIND $rows AS r MERGE (m:Movie {movieId:toInteger(r.movieId)}) SET m.title=r.title, m.genres=r.genres", rows=movies.to_dict("records"))
    s.run("UNWIND $rows AS r MERGE (u:User {userId:toInteger(r.userId)}) MERGE (m:Movie {movieId:toInteger(r.movieId)}) MERGE (u)-[x:RATED]->(m) SET x.rating=toFloat(r.rating), x.timestamp=toInteger(r.timestamp)", rows=ratings.to_dict("records"))
    s.run("MATCH (m:Movie) UNWIND split(m.genres, '|') AS g WITH m, g WHERE g <> '(no genres listed)' MERGE (genre:Genre {name:g}) MERGE (m)-[:IN_GENRE]->(genre)")
    query = """MATCH (u:User {userId:1})-[r1:RATED]->(liked:Movie)<-[r2:RATED]-(other:User)-[r3:RATED]->(candidate:Movie) WHERE r1.rating >= 4.0 AND r2.rating >= 4.0 AND r3.rating >= 4.0 AND NOT (u)-[:RATED]->(candidate) WITH candidate, count(DISTINCT other) AS sharedUsers, avg(r3.rating) AS predictedRating RETURN candidate.title AS recommendation, sharedUsers, round(predictedRating * 100) / 100.0 AS predictedRating ORDER BY sharedUsers DESC, predictedRating DESC LIMIT 10"""
    print("Neo4j recommendations for user 1:")
    for row in s.run(query): print(dict(row))
driver.close()
