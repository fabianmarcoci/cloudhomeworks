import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

DATA_DIR    = os.path.join(os.path.dirname(__file__), "data")
MOVIES_FILE = os.path.join(DATA_DIR, "movies.json")
GENRES_FILE = os.path.join(DATA_DIR, "genres.json")

VALID_STATUSES = {"watched", "watching", "plan_to_watch"}


def load(filepath):
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def save(filepath, data):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def next_id(items):
    return max((item["id"] for item in items), default=0) + 1


class WatchlistHandler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        print(f"  {self.command} {self.path}  →  {fmt % args}")

    def send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_json_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None

    def parse_path(self):
        path = urlparse(self.path).path
        return [p for p in path.strip("/").split("/") if p]

    def do_GET(self):
        parts = self.parse_path()

        if parts == ["movies"]:
            self.send_json(200, load(MOVIES_FILE))

        elif len(parts) == 2 and parts[0] == "movies":
            try:
                movie_id = int(parts[1])
            except ValueError:
                self.send_json(400, {"error": "Invalid movie ID"})
                return

            movie = None
            for m in load(MOVIES_FILE):
                if m["id"] == movie_id:
                    movie = m
                    break

            if movie is None:
                self.send_json(404, {"error": "Movie not found"})
            else:
                self.send_json(200, movie)

        elif parts == ["genres"]:
            self.send_json(200, load(GENRES_FILE))

        elif len(parts) == 2 and parts[0] == "genres":
            try:
                genre_id = int(parts[1])
            except ValueError:
                self.send_json(400, {"error": "Invalid genre ID"})
                return

            genre = None
            for g in load(GENRES_FILE):
                if g["id"] == genre_id:
                    genre = g
                    break

            if genre is None:
                self.send_json(404, {"error": "Genre not found"})
            else:
                self.send_json(200, genre)

        else:
            self.send_json(404, {"error": "Route not found"})

    def do_POST(self):
        parts = self.parse_path()
        body  = self.read_json_body()
        if body is None:
            self.send_json(400, {"error": "Request body must be valid JSON"})
            return

        if parts == ["movies"]:
            for field in ["title", "year", "director", "genre_id", "status"]:
                if field not in body:
                    self.send_json(400, {"error": f"Missing field: {field}"})
                    return

            if body["status"] not in VALID_STATUSES:
                self.send_json(400, {"error": f"status must be one of: {sorted(VALID_STATUSES)}"})
                return

            genre_exists = False
            for g in load(GENRES_FILE):
                if g["id"] == body["genre_id"]:
                    genre_exists = True
                    break
            if not genre_exists:
                self.send_json(404, {"error": f"Genre with id={body['genre_id']} does not exist"})
                return

            movies = load(MOVIES_FILE)
            new_movie = {
                "id":       next_id(movies),
                "title":    body["title"],
                "year":     body["year"],
                "director": body["director"],
                "genre_id": body["genre_id"],
                "status":   body["status"],
                "rating":   body.get("rating"),
                "review":   body.get("review", ""),
            }
            movies.append(new_movie)
            save(MOVIES_FILE, movies)
            self.send_json(201, new_movie)

        elif parts == ["genres"]:
            if "name" not in body:
                self.send_json(400, {"error": "Missing field: name"})
                return

            genres = load(GENRES_FILE)
            if any(g["name"].lower() == body["name"].lower() for g in genres):
                self.send_json(409, {"error": f"Genre '{body['name']}' already exists"})
                return

            new_genre = {
                "id":          next_id(genres),
                "name":        body["name"],
                "description": body.get("description", ""),
            }
            genres.append(new_genre)
            save(GENRES_FILE, genres)
            self.send_json(201, new_genre)

        else:
            self.send_json(404, {"error": "Route not found"})

    def do_PUT(self):
        parts = self.parse_path()
        body  = self.read_json_body()
        if body is None:
            self.send_json(400, {"error": "Request body must be valid JSON"})
            return

        if len(parts) == 2 and parts[0] == "movies":
            try:
                movie_id = int(parts[1])
            except ValueError:
                self.send_json(400, {"error": "Invalid movie ID"})
                return

            movies = load(MOVIES_FILE)
            idx = None
            for i, m in enumerate(movies):
                if m["id"] == movie_id:
                    idx = i
                    break

            if idx is None:
                self.send_json(404, {"error": "Movie not found"})
                return

            for field in ["title", "year", "director", "genre_id", "status"]:
                if field not in body:
                    self.send_json(400, {"error": f"Missing field: {field}"})
                    return

            if body["status"] not in VALID_STATUSES:
                self.send_json(400, {"error": f"status must be one of: {sorted(VALID_STATUSES)}"})
                return

            genre_exists = False
            for g in load(GENRES_FILE):
                if g["id"] == body["genre_id"]:
                    genre_exists = True
                    break
            if not genre_exists:
                self.send_json(404, {"error": f"Genre with id={body['genre_id']} does not exist"})
                return

            updated = {
                "id":       movie_id,
                "title":    body["title"],
                "year":     body["year"],
                "director": body["director"],
                "genre_id": body["genre_id"],
                "status":   body["status"],
                "rating":   body.get("rating", movies[idx].get("rating")),
                "review":   body.get("review", movies[idx].get("review", "")),
            }
            movies[idx] = updated
            save(MOVIES_FILE, movies)
            self.send_json(200, updated)

        elif len(parts) == 2 and parts[0] == "genres":
            try:
                genre_id = int(parts[1])
            except ValueError:
                self.send_json(400, {"error": "Invalid genre ID"})
                return

            genres = load(GENRES_FILE)
            idx = None
            for i, g in enumerate(genres):
                if g["id"] == genre_id:
                    idx = i
                    break

            if idx is None:
                self.send_json(404, {"error": "Genre not found"})
                return

            if "name" not in body:
                self.send_json(400, {"error": "Missing field: name"})
                return

            if any(g["name"].lower() == body["name"].lower() and g["id"] != genre_id for g in genres):
                self.send_json(409, {"error": f"Genre '{body['name']}' already exists"})
                return

            updated = {
                "id":          genre_id,
                "name":        body["name"],
                "description": body.get("description", genres[idx].get("description", "")),
            }
            genres[idx] = updated
            save(GENRES_FILE, genres)
            self.send_json(200, updated)

        else:
            self.send_json(404, {"error": "Route not found"})

    def do_DELETE(self):
        parts = self.parse_path()

        if len(parts) == 2 and parts[0] == "movies":
            try:
                movie_id = int(parts[1])
            except ValueError:
                self.send_json(400, {"error": "Invalid movie ID"})
                return

            movies    = load(MOVIES_FILE)
            remaining = [m for m in movies if m["id"] != movie_id]
            if len(remaining) == len(movies):
                self.send_json(404, {"error": "Movie not found"})
                return

            save(MOVIES_FILE, remaining)
            self.send_json(200, {"message": f"Movie {movie_id} deleted successfully"})

        elif len(parts) == 2 and parts[0] == "genres":
            try:
                genre_id = int(parts[1])
            except ValueError:
                self.send_json(400, {"error": "Invalid genre ID"})
                return

            genres    = load(GENRES_FILE)
            remaining = [g for g in genres if g["id"] != genre_id]
            if len(remaining) == len(genres):
                self.send_json(404, {"error": "Genre not found"})
                return

            movies = load(MOVIES_FILE)
            if any(m["genre_id"] == genre_id for m in movies):
                self.send_json(409, {
                    "error": "Cannot delete genre: movies are still referencing it."
                })
                return

            save(GENRES_FILE, remaining)
            self.send_json(200, {"message": f"Genre {genre_id} deleted successfully"})

        else:
            self.send_json(404, {"error": "Route not found"})


if __name__ == "__main__":
    PORT   = 8080
    server = HTTPServer(("", PORT), WatchlistHandler)
    print(f"Movie Watchlist API http://localhost:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        server.server_close()
