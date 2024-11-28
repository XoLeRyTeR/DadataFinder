FROM python:slim
WORKDIR /app


COPY *.py *.json requirements.txt /app

RUN pip install --no-cache-dir -r requirements.txt

CMD ["streamlit", "run", "main.py"]
EXPOSE 8501