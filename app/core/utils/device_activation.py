"""端末初回有効化で使用するコード形式とハッシュ化を提供する。"""

import hashlib


ACTIVATION_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
ACTIVATION_CODE_LENGTH = 12
ACTIVATION_CODE_GROUP_SIZE = 4
_ACTIVATION_CODE_GROUP = f"[{ACTIVATION_CODE_ALPHABET}]{{{ACTIVATION_CODE_GROUP_SIZE}}}"
_ACTIVATION_CODE_GROUP_COUNT = ACTIVATION_CODE_LENGTH // ACTIVATION_CODE_GROUP_SIZE
_ACTIVATION_CODE_FORMAT = "-".join([_ACTIVATION_CODE_GROUP] * _ACTIVATION_CODE_GROUP_COUNT)
ACTIVATION_CODE_PATTERN = f"^{_ACTIVATION_CODE_FORMAT}$"


def hash_device_secret(value: str) -> str:
    """有効化コードまたは端末認証情報をDB保存用にハッシュ化する。

    Args:
        value: ハイフンを含む平文の有効化コード、または平文の端末認証情報。

    Returns:
        UTF-8でエンコードした値のSHA-256ハッシュを表す16進文字列。
    """
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
