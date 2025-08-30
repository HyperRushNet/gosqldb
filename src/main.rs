use sqlx::sqlite::SqlitePoolOptions;
use sqlx::Row;
use tokio;

#[tokio::main]
async fn main() -> Result<(), sqlx::Error> {
    // Verbinding met SQLite database (in file `data.db`)
    let pool = SqlitePoolOptions::new()
        .max_connections(5)
        .connect("sqlite:data.db")
        .await?;

    // Voorbeeld: tabel aanmaken
    sqlx::query(
        "CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        );"
    )
    .execute(&pool)
    .await?;

    // Voorbeeld: item toevoegen
    sqlx::query("INSERT INTO items (name) VALUES (?)")
        .bind("RenderDB Item")
        .execute(&pool)
        .await?;

    // Voorbeeld: items lezen
    let rows = sqlx::query("SELECT id, name FROM items")
        .fetch_all(&pool)
        .await?;

    for row in rows {
        let id: i64 = row.get("id");
        let name: String = row.get("name");
        println!("{}: {}", id, name);
    }

    Ok(())
}
