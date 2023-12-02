FROM golang:1.23 AS build

ARG VERSION
WORKDIR /build

COPY go.* ./
RUN go mod download

COPY *.go ./
RUN CGO_ENABLED=0 go build -ldflags "-X main.version=$VERSION" -o dispatch

FROM debian:12-slim

EXPOSE 8080

COPY --from=build /build/dispatch /usr/local/bin/dispatch
CMD dispatch
