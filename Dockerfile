# Build stage
FROM rust:1.73 as builder
WORKDIR /app
COPY Cargo.toml Cargo.lock ./
COPY src ./src
RUN cargo build --release

# Runtime stage
FROM debian:bookworm-slim
WORKDIR /app
COPY --from=builder /app/target/release/rdb-rust .
EXPOSE 8080
CMD ["./rdb-rust"]
