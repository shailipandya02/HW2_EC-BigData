// Top-rated movies with a minimum of 50 ratings.
db.ratings.aggregate([
  {$group: {_id: "$movieId", ratingCount: {$sum: 1}, averageRating: {$avg: "$rating"}}},
  {$match: {ratingCount: {$gte: 50}}},
  {$sort: {averageRating: -1, ratingCount: -1}},
  {$limit: 10},
  {$lookup: {from: "movies", localField: "_id", foreignField: "movieId", as: "movie"}},
  {$unwind: "$movie"},
  {$project: {_id: 0, title: "$movie.title", genres: "$movie.genres", averageRating: 1, ratingCount: 1}}
])

// Rating activity by genre using a lookup and split/explode pattern.
db.movies.aggregate([
  {$project: {movieId: 1, genres: {$split: ["$genres", "|"]}}},
  {$unwind: "$genres"},
  {$lookup: {from: "ratings", localField: "movieId", foreignField: "movieId", as: "ratings"}},
  {$unwind: "$ratings"},
  {$group: {_id: "$genres", ratings: {$sum: 1}, averageRating: {$avg: "$ratings.rating"}}},
  {$sort: {ratings: -1}}
])
