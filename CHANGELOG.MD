# ECONO Engine API — DevSecOps Test Task

## Что сделано

### 1. SAST
- Настроен Semgrep
- Исправлены Critical/High проблемы в приложении
- Отчёт по находкам приложен в PDF

### 2. Dependency Scanning
- Настроен Trivy для filesystem scan и image scan
- Уязвимые зависимости обновлены или описаны как accepted risk в отчёте

### 3. Secrets Management
- Секреты вынесены из кода и compose в `.env`
- Добавлен `.env.example`
- Настроен gitleaks для поиска секретов
- `.env` добавлен в `.gitignore`

### 4. CI/CD Security Gates
- GitHub Actions pipeline:
  - Semgrep
  - Gitleaks
  - Trivy FS
  - Docker build
  - Trivy image scan

### 5. Hardening
- Docker контейнер запускается не от root
- Убран privileged mode
- Redis не опубликован наружу
- Nginx настроен с security headers
- Закрыт `/nginx_status`
- Отключён autoindex

## Как запустить

```bash
cp .env.example .env
docker compose up --build