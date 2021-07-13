FROM python:3
RUN apt-get clean && \
    apt-get update -y && \
    apt-get install -y nginx \
    python3-dev \
    build-essential && \
    apt-get autoclean && \
    apt-get clean
WORKDIR /app
RUN pip install Flask requests flask_mysqldb
COPY . .
EXPOSE 5000
CMD ["python", "./app.py"]