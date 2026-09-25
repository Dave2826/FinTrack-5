from database.connection import SessionLocal


def get_context():
    db = SessionLocal()

    try:
        yield {
            "db": db
        }
    finally:
        db.close()