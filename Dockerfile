# Builder stage
FROM rust:1.80-bullseye AS builder
WORKDIR /app

# Installeer SQLite dev libraries
RUN apt-get update && apt-get install -y libsqlite3-dev pkg-config && rm -rf /var/lib/apt/lists/*

# Kopieer Cargo bestanden
COPY Cargo.toml Cargo.lock ./
COPY src ./src

# Build in release mode
RUN cargo build --release

# Runtime stage
FROM debian:bookworm-slim
WORKDIR /app

# Install SQLite runtime libraries
RUN apt-get update && apt-get install -y libsqlite3-0 && rm -rf /var/lib/apt/lists/*

# Kopieer binary van builder
COPY --from=builder /app/target/release/rdb /app/rdb

# Expose poort
EXPOSE 8080

CMD ["./rdb"]
