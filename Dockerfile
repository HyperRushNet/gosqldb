# Stage 1: Build
FROM rust:1.81 as builder
WORKDIR /app

# Kopieer de bronbestanden
COPY Cargo.toml Cargo.lock ./
COPY src ./src

# Build in release mode
RUN cargo build --release

# Stage 2: Minimal runtime
FROM debian:bookworm-slim
WORKDIR /app

# Kopieer de binaire van de builder
COPY --from=builder /app/target/release/rdb ./rdb

EXPOSE 8080
CMD ["./rdb"]
