FROM golang:1.21-alpine AS builder

WORKDIR /build
COPY go.mod ./
COPY *.go ./
RUN go build -o /expense-validator .

FROM alpine:3.19
COPY --from=builder /expense-validator /expense-validator
EXPOSE 8080
CMD ["/expense-validator"]
