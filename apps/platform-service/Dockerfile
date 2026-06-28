FROM python:3.11-slim

WORKDIR /app

# Tối ưu cache layer cho Docker
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ code vào container
COPY . .

# Mở port 8080 (Khớp với uvicorn trong main.py)
EXPOSE 8080

CMD ["python", "main.py"]
