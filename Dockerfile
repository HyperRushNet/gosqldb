# Stage 1: Build
FROM rust:1.79 as builder

WORKDIR /app

# Alleen Cargo.toml kopiëren
COPY Cargo.toml ./

# Source code kopiëren
COPY src ./src

# Build de release (Cargo genereert automatisch Cargo.lock)
RUN cargo build --release

# Stage 2: Minimal runtime
FROM debian:bookworm-slim

WORKDIR /app

# Kopieer het gecompileerde binaire bestand van de builder
COPY --from=builder /app/target/release/rdb /app/rdb

# Expose de poort (pas aan indien nodig)
EXPOSE 8080

# Run het binaire bestand
CMD ["./rdb"]
