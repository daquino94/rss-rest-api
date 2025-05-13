FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY rss-rest-api.py .

ENV RSS_STORAGE_FILE=/data/feeds.json
ENV HISTORY_DAYS=30
ENV MAX_ENTRIES_PER_FEED=100
ENV GENERAL_FEED_TITLE="All Feeds"
ENV PORT=5000
ENV DEBUG=False

RUN mkdir -p /data

EXPOSE 5000

CMD ["python", "rss-rest-api.py"]