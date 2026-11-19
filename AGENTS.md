# AGENTS.md

## テスト実装前の必須スキル

- このリポジトリでテストコードを追加・変更するときは、作業前に `.codex/skills/teraid-pay-api-tests/SKILL.md` を全文読み、記載されたDBテストとファイル構成の確認を行う。会話メモリに手順が残っていても、毎回このファイルを確認する。
- APIを実装・変更するときも、テスト方針を決める前に同スキルを読む。各層のテスト方針はユーザー共通スキル `repository-test-conventions` に従う。

**Rule:** In each command, **define → use**. Do **not** escape `$`. Use generic `'path/to/file.ext'`.

## Docstring quality gate

- Pythonコードを追加・変更した後は、完了報告前に変更対象のモジュール、クラス、関数、メソッドのdocstringを必ず精査する。
- 新規の公開クラス・公開関数・公開メソッドには、責務、`Args`、`Returns`、必要に応じて`Raises`を含む日本語docstringを追加する。
- private helperにも、処理内容や返却値が名前だけでは明確でない場合はdocstringを追加する。
- 実装と一致しない既存docstring、移動元にだけ残ったdocstring、文字化けしたdocstringを放置しない。
- テスト完了だけを完了条件にせず、`ast`等で変更対象のdocstring欠落を機械的に確認する。

---

## 1) READ (UTF‑8 no BOM, line‑numbered)

```bash
bash -lc 'powershell -NoLogo -Command "
$OutputEncoding = [Console]::OutputEncoding = [Text.UTF8Encoding]::new($false);
Set-Location -LiteralPath (Convert-Path .);
function Get-Lines { param([string]$Path,[int]$Skip=0,[int]$First=40)
  $enc=[Text.UTF8Encoding]::new($false)
  $text=[IO.File]::ReadAllText($Path,$enc)
  if($text.Length -gt 0 -and $text[0] -eq [char]0xFEFF){ $text=$text.Substring(1) }
  $ls=$text -split \"`r?`n\"
  for($i=$Skip; $i -lt [Math]::Min($Skip+$First,$ls.Length); $i++){ \"{0:D4}: {1}\" -f ($i+1), $ls[$i] }
}
Get-Lines -Path \"path/to/file.ext\" -First 120 -Skip 0
"'
```

---

## 2) WRITE (UTF‑8 no BOM, atomic replace, backup)

```bash
bash -lc 'powershell -NoLogo -Command "
$OutputEncoding = [Console]::OutputEncoding = [Text.UTF8Encoding]::new($false);
Set-Location -LiteralPath (Convert-Path .);
function Write-Utf8NoBom { param([string]$Path,[string]$Content)
  $dir = Split-Path -Parent $Path
  if (-not (Test-Path $dir)) {
    New-Item -ItemType Directory -Path $dir -Force | Out-Null
  }
  $tmp = [IO.Path]::GetTempFileName()
  try {
    $enc = [Text.UTF8Encoding]::new($false)
    [IO.File]::WriteAllText($tmp,$Content,$enc)
    Move-Item $tmp $Path -Force
  }
  finally {
    if (Test-Path $tmp) {
      Remove-Item $tmp -Force -ErrorAction SilentlyContinue
    }
  }
}
$file = "path/to/your_file.ext"
$enc  = [Text.UTF8Encoding]::new($false)
$old  = (Test-Path $file) ? ([IO.File]::ReadAllText($file,$enc)) : ''
Write-Utf8NoBom -Path $file -Content ($old+"`nYOUR_TEXT_HERE`n")
"'
```
