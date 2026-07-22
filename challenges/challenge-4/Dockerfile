FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY challenge-4/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY challenge-4/workflow_orchestrator.py .
COPY challenge-4/api_server.py .

# Add challenge-3 agents for OCR agent
RUN mkdir -p /app/challenge-3/agents
COPY challenge-3/agents/ocr_agent.py /app/challenge-3/agents/

# Expose API port
EXPOSE 8080

# Run API server
CMD ["python", "api_server.py"]
