# Stage 1: Build
FROM rust:1.79 as builder
WORKDIR /app

# Dependencies kopiëren en builden
COPY Cargo.toml Cargo.lock ./
RUN mkdir src && echo "fn main() {}" > src/main.rs
RUN cargo fetch

# Broncode kopiëren
COPY src ./src
RUN cargo build --release

# Stage 2: Minimal runtime
FROM debian:bookworm-slim
WORKDIR /app

# Nodige libraries
RUN apt-get update && apt-get install -y libsqlite3-0 && rm -rf /var/lib/apt/lists/*

# Binaire van stage 1 kopiëren
COPY --from=builder /app/target/release/rdb_sql .

# SQLite database bestand
VOLUME ["/app/data.db"]

# Run de app
CMD ["./rdb_sql"]
