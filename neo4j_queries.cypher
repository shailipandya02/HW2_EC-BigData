// Recommend unrated movies using users with overlapping high ratings.
MATCH (u:User {userId:1})-[r1:RATED]->(liked:Movie)<-[r2:RATED]-(other:User)-[r3:RATED]->(candidate:Movie)
WHERE r1.rating >= 4.0 AND r2.rating >= 4.0 AND r3.rating >= 4.0
  AND NOT (u)-[:RATED]->(candidate)
WITH candidate, count(DISTINCT other) AS sharedUsers, avg(r3.rating) AS predictedRating
RETURN candidate.title AS recommendation, sharedUsers,
       round(predictedRating * 100) / 100.0 AS predictedRating
ORDER BY sharedUsers DESC, predictedRating DESC LIMIT 10;

// Find movies that share genres with a user's highly rated movies.
MATCH (u:User {userId:1})-[r:RATED]->(liked:Movie)-[:IN_GENRE]->(g:Genre)<-[:IN_GENRE]-(candidate:Movie)
WHERE r.rating >= 4.0 AND NOT (u)-[:RATED]->(candidate)
RETURN candidate.title, collect(DISTINCT g.name) AS sharedGenres, count(*) AS genreMatches
ORDER BY genreMatches DESC LIMIT 10;
