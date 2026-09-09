$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
    throw 'Create .venv and install requirements.txt first; see README.md.'
}
New-Item -ItemType Directory -Force -Path '.dev' | Out-Null
& '.\.venv\Scripts\python.exe' manage.py migrate --settings=brijvas.settings_dev --noinput
if ($LASTEXITCODE -ne 0) { throw 'Development migration failed.' }
& '.\.venv\Scripts\python.exe' manage.py runserver 127.0.0.1:8000 --settings=brijvas.settings_dev
