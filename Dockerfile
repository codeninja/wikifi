# Multi-stage build placeholder
FROM python:3.12-slim AS backend
WORKDIR /app
COPY backend /app/backend

FROM node:22-slim AS frontend
WORKDIR /app
COPY frontend /app/frontend

FROM debian:stable-slim AS runtime
CMD ["/bin/sh", "-c", "echo Configure services in docker-compose.yml"]
