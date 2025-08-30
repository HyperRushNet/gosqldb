# Stage 1: Build
FROM rust:1.73 as builder
WORKDIR /app

# Kopieer alleen Cargo.toml en source
COPY Cargo.toml ./
COPY src ./src

# Build release
RUN cargo build --release

# Stage 2: Minimal runtime
FROM debian:bookworm-slim
WORKDIR /app

# Kopieer het gecompileerde binaire bestand
COPY --from=builder /app/target/release/your_binary_name ./your_binary_name

# Expose poort (pas aan indien nodig)
EXPOSE 8080

# Start de app
CMD ["./your_binary_name"]
