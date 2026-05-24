import importlib
import os
import pkgutil
import re
import sys
import time
from functools import lru_cache
from pathlib import Path
from PIL import Image

from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, SQLAlchemyError


ROOT_DIR = next(
    parent for parent in Path(__file__).resolve().parents
    if (parent / "app" / "models").is_dir()
)
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.models.postgres.base_model import Base
from app.helpers.face_helper import FaceHelper


TEST_DATA_DIR = ROOT_DIR / "tests" / "unit" / "test_data"
ADAFACE_WEIGHT_PATH = TEST_DATA_DIR / "s3" / "buckets" / "weights" / "adaface" / "adaface_ir50_ms1mv2.ckpt"
SCRFD_WEIGHT_PATH = TEST_DATA_DIR / "s3" / "buckets" / "weights" / "scrfd" / "scrfd.onnx"
TEST_FACE_PATH = TEST_DATA_DIR / "images" / "scrfd" / "one_face.png"
TEST_FACE_EMBEDDING_USER_ID = 107


def import_postgres_models() -> None:
    import app.models.postgres as postgres_models

    for module_info in pkgutil.iter_modules(postgres_models.__path__):
        if module_info.name.startswith("_") or module_info.name in {"base_model", "vector"}:
            continue
        importlib.import_module(f"app.models.postgres.{module_info.name}")


def detect_driver() -> str:
    driver_from_env = os.getenv("POSTGRES_DB_DRIVER")
    if driver_from_env:
        return driver_from_env

    for driver_name, module_name in (
        ("psycopg2", "psycopg2"),
    ):
        try:
            importlib.import_module(module_name)
            return driver_name
        except ModuleNotFoundError:
            continue

    raise RuntimeError(
        "PostgreSQL driver is not installed for this interpreter: "
        f"{sys.executable}. Install `psycopg2-binary` into the active "
        "environment, or set POSTGRES_DB_DRIVER explicitly."
    )


def build_database_url() -> str:
    user = os.getenv("POSTGRES_DB_USER", "vector_user")
    password = os.getenv("POSTGRES_DB_PASSWORD", "vector_password")
    host = os.getenv("POSTGRES_DB_HOST", "127.0.0.1")
    port = os.getenv("POSTGRES_DB_PORT", "5432")
    database = os.getenv("POSTGRES_DB_NAME", "vector_db")
    driver = detect_driver()
    return f"postgresql+{driver}://{user}:{password}@{host}:{port}/{database}"


def _parse_sql_statements(sql_file_name: str) -> list[str]:
    current_dir = Path(__file__).resolve().parent
    sql_file = current_dir / sql_file_name
    sql_text = sql_file.read_text(encoding="utf-8")
    statements = []
    current_statement = []

    for line in sql_text.splitlines():
        stripped_line = line.strip()
        if not stripped_line or stripped_line.startswith("--"):
            continue

        current_statement.append(line)
        if stripped_line.endswith(";"):
            statement = "\n".join(current_statement).strip()
            if statement.endswith(";"):
                statement = statement[:-1].strip()
            if statement:
                statements.append(statement)
            current_statement = []

    if current_statement:
        statement = "\n".join(current_statement).strip()
        if statement:
            statements.append(statement)

    return statements


def _execute_sql_file(engine, sql_file_name: str) -> str:
    statements = _parse_sql_statements(sql_file_name)

    with engine.begin() as connection:
        truncated_tables = set()
        for statement in statements:
            match = re.match(r'INSERT\s+INTO\s+"?([a-zA-Z0-9_]+)"?', statement, re.IGNORECASE)
            if match:
                table_name = match.group(1)
                if table_name not in truncated_tables:
                    connection.exec_driver_sql(f'TRUNCATE TABLE "{table_name}" RESTART IDENTITY')
                    truncated_tables.add(table_name)
            connection.exec_driver_sql(statement)

    return sql_file_name


@lru_cache(maxsize=1)
def _build_test_face_embedding() -> list[float]:

    scrfd_weight_bytes = SCRFD_WEIGHT_PATH.read_bytes()
    image = Image.open(TEST_FACE_PATH).convert("RGB")
    face_image = FaceHelper._get_face_landmark(weight_bytes=scrfd_weight_bytes, image=image)
    _alignment_face = FaceHelper._alignment_face(face_image=face_image)

    adaface_weight_bytes = ADAFACE_WEIGHT_PATH.read_bytes()
    embedding = FaceHelper._get_embedding(weight_bytes=adaface_weight_bytes, face_image=_alignment_face)
    if len(embedding) != 512:
        raise ValueError(f"test_face.png の embedding は 512 次元である必要があります: {len(embedding)}")
    return embedding


def _update_test_face_embedding(engine) -> None:
    vector_literal = "[" + ",".join(str(float(value)) for value in _build_test_face_embedding()) + "]"
    with engine.begin() as connection:
        result = connection.execute(
            text(
                """
                UPDATE face_embeddings
                SET embedding = CAST(:embedding AS vector)
                WHERE user_id = :user_id
                """
            ),
            {
                "embedding": vector_literal,
                "user_id": TEST_FACE_EMBEDDING_USER_ID,
            },
        )
        if result.rowcount != 1:
            raise RuntimeError(f"user_id={TEST_FACE_EMBEDDING_USER_ID} の face_embedding が存在しません。")


def insert_face_embeddings(engine) -> str:
    executed_file = _execute_sql_file(engine, "face_embeddings.sql")
    _update_test_face_embedding(engine)
    return executed_file


def insert_sample_data(engine) -> list[str]:
    return [
        insert_face_embeddings(engine),
    ]


def wait_for_database(engine, retries: int = 30, delay_seconds: int = 2) -> None:
    last_error = None

    for attempt in range(1, retries + 1):
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return
        except OperationalError as exc:
            last_error = exc
            if attempt == retries:
                break
            print(
                f"PostgreSQL is not ready yet ({attempt}/{retries}). "
                f"Retrying in {delay_seconds} seconds..."
            )
            time.sleep(delay_seconds)

    raise SystemExit(f"Failed to connect to PostgreSQL after {retries} attempts: {last_error}")


def main() -> None:
    import_postgres_models()

    database_url = build_database_url()
    engine = create_engine(database_url, echo=False, future=True)

    try:
        wait_for_database(engine)
        with engine.begin() as connection:
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            Base.metadata.drop_all(bind=connection)
            Base.metadata.create_all(bind=connection)
        executed_files = insert_sample_data(engine)
    except SQLAlchemyError as exc:
        raise SystemExit(f"Failed to create tables: {exc}") from exc

    table_names = sorted(Base.metadata.tables.keys())
    print("Created tables:")
    for table_name in table_names:
        print(f"- {table_name}")
    print("Executed SQL files:")
    for file_name in executed_files:
        print(f"- {file_name}")


if __name__ == "__main__":
    main()
