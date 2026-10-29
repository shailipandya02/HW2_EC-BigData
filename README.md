# MovieGraph: MongoDB and Neo4j Movie Recommendation System

This project uses the downloaded **MovieLens ml-latest-small** dataset to answer two related questions:

1. Which movies, genres, and tags are most popular according to rating activity?
2. Which movies can be recommended to a user through shared tastes and genre relationships?

MongoDB stores flexible movie, rating, and tag documents and runs aggregation pipelines. Neo4j represents users, movies, genres, and tags as a graph and runs recommendation and similarity queries.

## Run locally

Place the downloaded `ml-latest-small.zip` in the project directory, or extract it so the folder `ml-latest-small/` is beside these files. Do not upload the dataset with the assignment.

```bash
python3 -m pip install -r requirements.txt
python3 analytics_demo.py
```

The demo reads the CSV files, computes reproducible analytics, and creates `outputs/movie_analytics.png` and `outputs/top_movies.csv`.

For the database loaders, install Docker Desktop and run:

```bash
docker compose up -d
python3 load_mongodb.py
python3 load_neo4j.py
```

## Files

- `analytics_demo.py`: local validation and visualization.
- `load_mongodb.py`: PyMongo loader and aggregation pipeline.
- `load_neo4j.py`: Neo4j loader and graph recommendation query.
- `mongodb_queries.js`: MongoDB Compass/mongosh pipelines.
- `neo4j_queries.cypher`: Neo4j Browser queries.
- `build_report.py`: PDF report generator.
- `report_sources.md`: dataset and documentation links.
