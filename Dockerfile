# Stage 1: Build
FROM rust:nightly as builder
WORKDIR /app

# Kopieer Cargo.toml en source code
COPY Cargo.toml ./
COPY src ./src

# Build release (edition 2024 ondersteund)
RUN cargo build --release

# Stage 2: Minimal runtime
FROM debian:bookworm-slim
WORKDIR /app

# Kopieer het gecompileerde binaire bestand
COPY --from=builder /app/target/release/your_binary_name ./your_binary_name

# Expose poort (pas aan naar jouw app)
EXPOSE 8080

# Start de app
CMD ["./your_binary_name"]
