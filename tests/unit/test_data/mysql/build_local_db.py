import importlib
import os
import pkgutil
import re
import sys
import time
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, SQLAlchemyError


ROOT_DIR = next(
    parent for parent in Path(__file__).resolve().parents
    if (parent / "app" / "models").is_dir()
)
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.models.mysql.base_model import Base

def import_mysql_models() -> None:
    import app.models.mysql as mysql_models

    for module_info in pkgutil.iter_modules(mysql_models.__path__):
        if module_info.name.startswith("_") or module_info.name == "base_model":
            continue
        importlib.import_module(f"app.models.mysql.{module_info.name}")


def detect_driver() -> str:
    driver_from_env = os.getenv("DB_DRIVER")
    if driver_from_env:
        return driver_from_env

    for driver_name, module_name in (
        ("mysqldb", "MySQLdb"),
        ("pymysql", "pymysql"),
    ):
        try:
            importlib.import_module(module_name)
            return driver_name
        except ModuleNotFoundError:
            continue

    raise RuntimeError(
        "MySQL driver is not installed for this interpreter: "
        f"{sys.executable}. Install `PyMySQL` or `mysqlclient` into the active "
        "environment, or set DB_DRIVER explicitly."
    )


def build_database_url() -> str:
    user = os.getenv("DB_USER", "teraid_pay_admin_user")
    password = os.getenv("DB_PASSWORD", "password")
    host = os.getenv("DB_HOST", "127.0.0.1")
    port = os.getenv("DB_PORT", "3307")
    database = os.getenv("DB_NAME", "db_local")
    driver = detect_driver()
    return f"mysql+{driver}://{user}:{password}@{host}:{port}/{database}?charset=utf8mb4"


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
        altered_tables = set()
        for statement in statements:
            match = re.match(r"INSERT\s+INTO\s+`?([a-zA-Z0-9_]+)`?", statement, re.IGNORECASE)
            if match:
                table_name = match.group(1)
                if table_name not in altered_tables:
                    connection.exec_driver_sql(f"DELETE FROM `{table_name}`")
                    connection.exec_driver_sql(f"ALTER TABLE `{table_name}` AUTO_INCREMENT = 1")
                    altered_tables.add(table_name)
            connection.exec_driver_sql(statement)

    return sql_file_name


def insert_stores(engine) -> str:
    return _execute_sql_file(engine, "stores.sql")


def insert_users(engine) -> str:
    return _execute_sql_file(engine, "users.sql")


def insert_wallets(engine) -> str:
    return _execute_sql_file(engine, "wallets.sql")


def insert_user_wallets(engine) -> str:
    return _execute_sql_file(engine, "user_wallets.sql")


def insert_store_wallets(engine) -> str:
    return _execute_sql_file(engine, "store_wallets.sql")


def insert_nonces(engine) -> str:
    return _execute_sql_file(engine, "nonces.sql")


def insert_user_nonces(engine) -> str:
    return _execute_sql_file(engine, "user_nonces.sql")


def insert_store_nonces(engine) -> str:
    return _execute_sql_file(engine, "store_nonces.sql")


def insert_payment_requests(engine) -> str:
    return _execute_sql_file(engine, "payment_requests.sql")


def insert_sample_data(engine) -> list[str]:
    return [
        insert_stores(engine),
        insert_users(engine),
        insert_wallets(engine),
        insert_user_wallets(engine),
        insert_store_wallets(engine),
        insert_nonces(engine),
        insert_user_nonces(engine),
        insert_store_nonces(engine),
        insert_payment_requests(engine),
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
                f"MySQL is not ready yet ({attempt}/{retries}). "
                f"Retrying in {delay_seconds} seconds..."
            )
            time.sleep(delay_seconds)

    raise SystemExit(f"Failed to connect to MySQL after {retries} attempts: {last_error}")


def main() -> None:
    import_mysql_models()

    database_url = build_database_url()
    engine = create_engine(database_url, echo=False, future=True)

    try:
        wait_for_database(engine)
        with engine.begin() as connection:
            connection.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
            Base.metadata.drop_all(bind=connection)
            Base.metadata.create_all(bind=connection)
            connection.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
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
