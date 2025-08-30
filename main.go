package main

import (
	"database/sql"
	"encoding/json"
	"log"
	"net/http"
	"os"

	_ "github.com/mattn/go-sqlite3"
)

var db *sql.DB

type Item struct {
	ID      string          `json:"id"`
	Type    string          `json:"type"`
	Payload json.RawMessage `json:"payload"`
}

func main() {
	var err error
	dbPath := "./data.db"
	db, err = sql.Open("sqlite3", dbPath)
	if err != nil {
		log.Fatal(err)
	}

	createTable := `
	CREATE TABLE IF NOT EXISTS items (
		id TEXT PRIMARY KEY,
		type TEXT,
		payload TEXT,
		created_at DATETIME DEFAULT CURRENT_TIMESTAMP
	);`
	_, err = db.Exec(createTable)
	if err != nil {
		log.Fatal(err)
	}

	http.HandleFunc("/database", handleDatabase)
	http.HandleFunc("/database/item", handleItem)
	http.HandleFunc("/database/items", handleItems)
	http.HandleFunc("/ping", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(200)
	})

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}
	log.Println("Server started on port", port)
	log.Fatal(http.ListenAndServe(":"+port, nil))
}

func handleDatabase(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		w.WriteHeader(http.StatusMethodNotAllowed)
		return
	}
	t := r.URL.Query().Get("type")
	if t == "" {
		http.Error(w, "missing type", 400)
		return
	}
	var payload map[string]interface{}
	if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
		http.Error(w, err.Error(), 400)
		return
	}
	id := payload["id"]
	if id == nil {
		http.Error(w, "missing id", 400)
		return
	}
	p, _ := json.Marshal(payload)
	_, err := db.Exec("INSERT INTO items (id,type,payload) VALUES (?,?,?)", id, t, string(p))
	if err != nil {
		http.Error(w, err.Error(), 500)
		return
	}
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(payload)
}

func handleItem(w http.ResponseWriter, r *http.Request) {
	id := r.URL.Query().Get("id")
	t := r.URL.Query().Get("type")
	if id == "" || t == "" {
		http.Error(w, "missing id or type", 400)
		return
	}
	switch r.Method {
	case http.MethodGet:
		row := db.QueryRow("SELECT payload FROM items WHERE id=? AND type=?", id, t)
		var payload string
		err := row.Scan(&payload)
		if err != nil {
			http.Error(w, "not found", 404)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		w.Write([]byte(payload))
	case http.MethodDelete:
		res, err := db.Exec("DELETE FROM items WHERE id=? AND type=?", id, t)
		if err != nil {
			http.Error(w, err.Error(), 500)
			return
		}
		cnt, _ := res.RowsAffected()
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]interface{}{"deleted": cnt})
	default:
		w.WriteHeader(405)
	}
}

func handleItems(w http.ResponseWriter, r *http.Request) {
	t := r.URL.Query().Get("type")
	if t == "" {
		http.Error(w, "missing type", 400)
		return
	}
	rows, err := db.Query("SELECT payload FROM items WHERE type=?", t)
	if err != nil {
		http.Error(w, err.Error(), 500)
		return
	}
	defer rows.Close()
	var list []json.RawMessage
	for rows.Next() {
		var payload string
		rows.Scan(&payload)
		list = append(list, json.RawMessage(payload))
	}
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(list)
}
