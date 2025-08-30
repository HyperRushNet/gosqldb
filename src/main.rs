use warp::Filter;
use sqlx::sqlite::SqlitePool;
use serde::{Deserialize, Serialize};

#[derive(Serialize, Deserialize)]
struct Item {
    id: i32,
    name: String,
}

#[tokio::main]
async fn main() {
    let pool = SqlitePool::connect("sqlite:rdb.db").await.unwrap();

    let list = warp::path!("items")
        .and(warp::get())
        .map(move || {
            warp::reply::json(&vec![Item { id: 1, name: "Hello".into() }])
        });

    warp::serve(list).run(([0, 0, 0, 0], 8080)).await;
}
