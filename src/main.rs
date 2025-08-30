use axum::{
    routing::{get, post},
    Json, Router,
};
use serde::{Deserialize, Serialize};
use sqlx::{sqlite::SqlitePoolOptions, Pool, Sqlite};
use std::net::SocketAddr;
use uuid::Uuid;

#[derive(Serialize, Deserialize)]
struct Item {
    id: String,
    name: String,
}

#[tokio::main]
async fn main() -> Result<(), sqlx::Error> {
    // SQLite in-memory database (voor demo)
    let pool = SqlitePoolOptions::new()
        .max_connections(5)
        .connect("sqlite:rdb.db")
        .await?;

    // Maak table als die nog niet bestaat
    sqlx::query(
        "CREATE TABLE IF NOT EXISTS items (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL
        );",
    )
    .execute(&pool)
    .await?;

    let app = Router::new()
        .route("/items", get({
            let pool = pool.clone();
            move || list_items(pool.clone())
        }))
        .route("/items", post({
            let pool = pool.clone();
            move |Json(item): Json<Item>| add_item(pool.clone(), item)
        }));

    let addr = SocketAddr::from(([0, 0, 0, 0], 8080));
    println!("Listening on {}", addr);
    axum::Server::bind(&addr).serve(app.into_make_service()).await.unwrap();

    Ok(())
}

async fn list_items(pool: Pool<Sqlite>) -> Json<Vec<Item>> {
    let items = sqlx::query_as!(Item, "SELECT id, name FROM items")
        .fetch_all(&pool)
        .await
        .unwrap_or_default();
    Json(items)
}

async fn add_item(pool: Pool<Sqlite>, mut item: Item) -> Json<Item> {
    item.id = Uuid::new_v4().to_string();
    sqlx::query!("INSERT INTO items (id, name) VALUES (?, ?)", item.id, item.name)
        .execute(&pool)
        .await
        .unwrap();
    Json(item)
}
