# Build stage
FROM golang:1.21-alpine AS build
WORKDIR /app

# Installeer C compiler en SQLite dev libs
RUN apk add --no-cache gcc musl-dev sqlite-dev

COPY go.mod ./
COPY main.go ./
RUN go mod tidy
RUN go build -o rdb .

# Final stage
FROM alpine:latest
WORKDIR /app
COPY --from=build /app/rdb .
EXPOSE 8080
CMD ["./rdb"]
