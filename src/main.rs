use axum::{
    extract::{Query, State},
    routing::{get, post},
    Json, Router, http::StatusCode,
};
use serde::{Deserialize, Serialize};
use sqlx::{sqlite::SqlitePoolOptions, SqlitePool};
use std::net::SocketAddr;
use uuid::Uuid;

#[derive(Serialize, Deserialize)]
struct Item {
    id: String,
    r#type: String,
    payload: serde_json::Value,
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let pool = SqlitePoolOptions::new()
        .max_connections(5)
        .connect("sqlite://data.db")
        .await?;

    // Initialize table
    sqlx::query(
        "CREATE TABLE IF NOT EXISTS items (
            id TEXT PRIMARY KEY,
            type TEXT,
            payload TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )",
    )
    .execute(&pool)
    .await?;

    let app = Router::new()
        .route("/database", post(add_item))
        .route("/database/item", get(get_item))
        .with_state(pool.clone());

    let addr = SocketAddr::from(([0, 0, 0, 0], 8080));
    println!("Server running on {}", addr);
    axum::Server::bind(&addr).serve(app.into_make_service()).await?;
    Ok(())
}

async fn add_item(
    State(pool): State<SqlitePool>,
    Json(mut item): Json<Item>,
) -> Result<Json<Item>, (StatusCode, String)> {
    if item.id.is_empty() {
        item.id = Uuid::new_v4().to_string();
    }
    let payload_str = serde_json::to_string(&item.payload).unwrap();
    let res = sqlx::query("INSERT INTO items (id, type, payload) VALUES (?, ?, ?)")
        .bind(&item.id)
        .bind(&item.r#type)
        .bind(payload_str)
        .execute(&pool)
        .await;
    match res {
        Ok(_) => Ok(Json(item)),
        Err(e) => Err((StatusCode::INTERNAL_SERVER_ERROR, e.to_string())),
    }
}

#[derive(Deserialize)]
struct GetQuery {
    id: String,
}

async fn get_item(
    State(pool): State<SqlitePool>,
    Query(query): Query<GetQuery>,
) -> Result<Json<Item>, (StatusCode, String)> {
    let row = sqlx::query!("SELECT id, type, payload FROM items WHERE id = ?", query.id)
        .fetch_one(&pool)
        .await
        .map_err(|_| (StatusCode::NOT_FOUND, "Item not found".to_string()))?;
    let payload: serde_json::Value =
        serde_json::from_str(&row.payload).map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;
    Ok(Json(Item {
        id: row.id,
        r#type: row.r#type,
        payload,
    }))
}
