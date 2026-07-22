FROM python:3.11-slim

WORKDIR /app

# Copy function code
COPY . .

# Install the function's dependencies
RUN pip install -r requirements.txt

CMD ["opentelemetry-instrument", "python", "main.py"]
