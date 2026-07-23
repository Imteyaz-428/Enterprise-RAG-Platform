# Day 4 - Interview Notes

## What is Docker?

Docker is a containerization platform used to package an application with all its dependencies so it runs consistently across different environments.

---

## Difference between Image and Container

Image:
- Blueprint of an application.

Container:
- Running instance of an image.

---

## What is Dockerfile?

A Dockerfile contains instructions to build a Docker image.

Common instructions:

- FROM
- WORKDIR
- COPY
- RUN
- EXPOSE
- CMD

---

## What is Docker Compose?

Docker Compose is used to run multiple containers together using a single YAML file.

In this project it manages:

- Backend
- PostgreSQL
- Redis

---

## Why use Volumes?

Volumes persist data even if containers are deleted.

Example:
- PostgreSQL database
- Uploaded files

---

## What is a Health Check?

A health check verifies whether a service is ready to accept requests.

Examples:

PostgreSQL:
- pg_isready

Redis:
- redis-cli ping

---

## Why use Docker?

- Easy deployment
- Environment consistency
- Dependency isolation
- Scalability
- Simplified development

---

## Docker Commands

Build:

docker compose build

Run:

docker compose up

Run in background:

docker compose up -d

Stop:

docker compose down

View containers:

docker ps

View logs:

docker compose logs

Rebuild:

docker compose up --build