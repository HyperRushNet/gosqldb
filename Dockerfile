# Build stage
FROM golang:1.21-alpine AS build
WORKDIR /app
COPY go.mod ./
COPY main.go ./
RUN go mod tidy && go build -o rdb .

# Final stage
FROM alpine:latest
WORKDIR /app
COPY --from=build /app/rdb .
EXPOSE 8080
CMD ["./rdb"]
