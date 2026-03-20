# Vuln: Using generic 'latest' tag - not pinned
FROM python:3.9

# Vuln: Running as root (no USER directive)
WORKDIR /app

# Vuln: Copying everything including .env and secrets
COPY . .

# Vuln: No --no-cache-dir, no layer optimization
RUN pip install -r requirements.txt

# Vuln: Exposing all ports
EXPOSE 8000

# Vuln: Debug mode in production, binding to 0.0.0.0
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
