FROM python:3.11-slim

WORKDIR /app/extract

# Copy requirements from root → /app
COPY ./extract/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --upgrade pip && pip install -r /app/requirements.txt 

# 3. Install Playwright & deps
RUN playwright install && playwright install chromium && playwright install-deps