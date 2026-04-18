from fastapi import FastAPI
from app.endpoints.store import store_router
from app.core.utils.logging import TeraidPayApiLog
from fastapi.middleware.cors import CORSMiddleware

# ロギング初期設定
TeraidPayApiLog.setup(
    log_level='INFO',
    enable_file_logging=False  # 必要に応じてTrueに変更
)

app = FastAPI()

origins = [
    "http://localhost:3000", # 例えばローカル開発
    "http://localhost:3001", # フロントエンドの別ポート
    # 他の必要なオリジンもここに追加
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,        # 許可するオリジンのリスト
    allow_credentials=True,       # Cookie等の資格情報も許可する場合に設定
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],     # 許可するHTTPメソッド（"GET", "POST" など）; "*" は全てを許可
    allow_headers=["*"],          # 許可するHTTPヘッダー; "*" は全てを許可
)

app.include_router(store_router, prefix="/store")
