FROM python:3.10-slim
WORKDIR /app
#test

COPY *.py *.json requirements.txt /app
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD curl --fail http://localhost:8501/ || exit 1
CMD ["streamlit", "run", "main.py"]