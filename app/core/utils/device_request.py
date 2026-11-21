"""端末向けリクエストの数値IDの検証を提供する。"""


SIGNED_BIGINT_MAX = 9_223_372_036_854_775_807


def validate_decimal_id(value: object, label: str) -> str | int:
    """整数またはASCIIの十進数字だけで構成される文字列を受け付ける。

    Args:
        value: 整数の型変換を行う前の入力値。
        label: 入力エラーのメッセージに使う項目名。

    Returns:
        型変換と範囲検証に渡す元の値。

    Raises:
        ValueError: 整数またはASCIIの十進数字で構成される文字列以外の場合。
    """
    if type(value) is int:
        return value
    if not isinstance(value, str) or not value.isascii() or not value.isdecimal():
        raise ValueError(f"{label}は十進整数で指定してください。")
    return value
