from datetime import datetime, timedelta, timezone


JST = timezone(timedelta(hours=9))

class DateTimeUtil:
    @staticmethod
    def change_datetime_to_string(value: datetime | None) -> str | None:
        """datetime を API 返却用の文字列に変換する。

        Args:
            value: 変換対象の日時。

        Returns:
            `%Y-%m-%d %H:%M` 形式の文字列。値がない場合は `None`。
        """
        if not value:
            return None
        return value.strftime('%Y-%m-%d %H:%M')
