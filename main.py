from fastapi import FastAPI
from strawberry.fastapi import GraphQLRouter

from database.connection import SessionLocal
from graphql_api.schema import schema


app = FastAPI(
    title="Actividad 5 - Gestión Financiera",
    version="1.0.0"
)


def get_context():
    db = SessionLocal()

    return {
        "db": db
    }


graphql_app = GraphQLRouter(
    schema,
    context_getter=get_context
)

app.include_router(
    graphql_app,
    prefix="/graphql"
)


@app.get("/")
def inicio():
    return {
        "mensaje": "Backend de la Actividad 5 funcionando"
    }


@app.get("/sistema")
def obtener_sistema():
    return {
        "aplicacion": "Actividad 5 - Gestión Financiera",
        "version": "1.0.0",
        "framework": "FastAPI + GraphQL",
        "ambiente": "Docker"
    }