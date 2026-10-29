from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

ROOT = Path(__file__).parent
DATA = ROOT / "ml-latest-small"
if not DATA.exists():
    raise FileNotFoundError("Extract ml-latest-small.zip into this folder first.")
movies = pd.read_csv(DATA / "movies.csv")
ratings = pd.read_csv(DATA / "ratings.csv")
tags = pd.read_csv(DATA / "tags.csv")
ratings["movie_count"] = ratings.groupby("movieId")["rating"].transform("count")
movie_stats = ratings.groupby("movieId").agg(rating_count=("rating", "count"), average_rating=("rating", "mean")).reset_index()
movie_stats = movie_stats.merge(movies, on="movieId")
qualified = movie_stats[movie_stats.rating_count >= 50].copy().sort_values(["average_rating", "rating_count"], ascending=False)
genre_stats = movie_stats.assign(genre=movie_stats.genres.str.split("\\|", regex=True)).explode("genre").groupby("genre").agg(movies=("movieId", "nunique"), average_rating=("average_rating", "mean")).reset_index().sort_values("movies", ascending=False)
tag_stats = tags.groupby("tag").agg(uses=("movieId", "count"), unique_movies=("movieId", "nunique")).reset_index().sort_values(["uses", "unique_movies"], ascending=False)
out = ROOT / "outputs"; out.mkdir(exist_ok=True)
qualified.head(20).to_csv(out / "top_movies.csv", index=False)
genre_stats.to_csv(out / "genre_summary.csv", index=False)
tag_stats.head(20).to_csv(out / "top_tags.csv", index=False)
plot = genre_stats.head(12).sort_values("movies").plot.barh(x="genre", y="movies", legend=False, color="#355C7D")
plot.set_title("MovieLens movies by genre"); plot.set_xlabel("Number of movies"); plot.set_ylabel("")
plt.tight_layout(); plt.savefig(out / "movie_analytics.png", dpi=150); plt.close()
print("MovieLens records:", len(movies), "movies,", len(ratings), "ratings,", len(tags), "tags")
print("Top qualified movies (minimum 50 ratings):")
print(qualified[["title", "average_rating", "rating_count"]].head(10).to_string(index=False))
print("Most common genres:")
print(genre_stats.head(10).to_string(index=False))
