FROM python:3.11-slim

WORKDIR /app

# Update git so dbt debug, dpt deps etc dont break
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*
# Install only compatible versions
RUN pip install --upgrade pip && pip install dbt-core==1.7.7 dbt-duckdb==1.7.5 protobuf==4.23.4
CMD ["tail", "-f", "/dev/null"]

