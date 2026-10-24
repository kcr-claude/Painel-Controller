FROM python:3.12-slim
WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app app
COPY scripts scripts
RUN mkdir -p dados
ENV CONTROLLER_DB_URL=sqlite:///dados/controller.db
EXPOSE 8000
CMD ["uvicorn", "app.web.app:app", "--host", "0.0.0.0", "--port", "8000"]
