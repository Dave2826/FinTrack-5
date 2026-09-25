# FinTrack-5

Backend for financial account, concept and transaction management.

## Overview

FinTrack-5 is a backend application designed to manage companies, users, financial accounts, income and expense concepts, account-concept relationships, and financial transactions.

The application exposes its operations through GraphQL and uses a layered architecture to separate API, business logic, data access, and persistence.

## Architecture

    GraphQL
       |
       v
    Services
       |
       v
    Repositories
       |
       v
    SQLAlchemy
       |
       v
    PostgreSQL

## Main modules

- Companies and users
- Financial accounts
- Income and expense concepts
- Account-concept relationships
- Financial transactions
- GraphQL API
- Database migrations

## Technology stack

- Python 3.11
- FastAPI
- Strawberry GraphQL
- SQLAlchemy
- PostgreSQL 16
- Alembic
- Docker
- Docker Compose
- JWT authentication infrastructure

## GraphQL operations

### Queries

- `accounts`
- `concepts`
- `accountConcepts`
- `transactions`

### Mutations

- `createAccount`
- `createConcept`
- `assignConceptToAccount`
- `removeConceptFromAccount`
- `createTransaction`
- `deleteTransaction`

## Running the project

Create a local `.env` file based on `.env.example`.

Then start the services:

    docker compose up -d

The main services are:

- API: `http://localhost:8002`
- GraphQL: `http://localhost:8002/graphql`
- PostgreSQL: `localhost:5434`
- pgAdmin: `http://localhost:5052`

## Database migrations

Apply the latest migration with:

    docker compose exec api alembic upgrade head

Check the current migration with:

    docker compose exec api alembic current

## Project structure

    FinTrack-5/
    ├── alembic/
    │   ├── versions/
    │   ├── env.py
    │   └── script.py.mako
    ├── database/
    ├── graphql_api/
    ├── models/
    ├── repositories/
    ├── services/
    ├── Dockerfile
    ├── compose.yaml
    ├── main.py
    ├── requirements.txt
    └── README.md