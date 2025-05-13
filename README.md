# RSS Feed REST API

A RESTful API service that manages RSS feeds, allowing you to create, retrieve, and filter content in both JSON and XML formats.

[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://buymeacoffee.com/balsamic9239)

## Features

- 📋 Get feeds in both JSON and XML formats
- 🆕 Create new feeds via simple POST requests
- 🔍 Filter feeds with powerful search queries
- 📊 Data persistence via JSON file storage
- ⚙️ Configurable via environment variables
- 🖼️ Full image support for feeds and entries
- 🧹 Automatic cleanup of outdated entries
- 🐳 Easy deployment with Docker

## How It Works

The API:
1. Stores feed data in a structured JSON file
2. Provides RESTful endpoints for CRUD operations
3. Supports both JSON and XML output formats
4. Automatically cleans up entries older than configured days
5. Limits entries per feed to maintain performance
6. Provides search functionality with multiple filter options

## Installation

### Prerequisites

- Python 3.8+ (for local installation)
- Docker (for Docker installation)

### Option 1: Local Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/daquino94/rss-rest-api.git
   cd rss-feed-api
   ```

2. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the application:
   ```bash
   python rss-rest-api.py
   ```

### Option 2: Docker Installation (Local Build)

1. Clone this repository:
   ```bash
   git clone https://github.com/daquino94/rss-rest-api.git
   cd rss-feed-api
   ```

2. Build and run with Docker:
   ```bash
   docker build -t rss-feed-api .
   docker run -d \
     --name rss-feed-api \
     -p 5000:5000 \
     -e RSS_STORAGE_FILE="/data/feeds.json" \
     -e HISTORY_DAYS=30 \
     -e GENERAL_FEED_TITLE="All Feeds" \
     -v $(pwd)/data:/data \
     rss-feed-api
   ```

### Option 3: Docker Hub Installation

1. Create a directory for your data:
   ```bash
   mkdir -p rss-feed-api/data
   cd rss-feed-api
   ```

2. Update as your prefer a docker-compose.yaml file:
   ```yaml
   services:
     rss-feed-api:
       image: asterix94/rss-rest-api
       ports:
         - "5000:5000"
       environment:
         - RSS_STORAGE_FILE=/data/feeds.json
         - HISTORY_DAYS=30
         - MAX_ENTRIES_PER_FEED=100
         - GENERAL_FEED_TITLE="All Feeds"
         - DEBUG=False
       volumes:
         - ./data:/data
       restart: unless-stopped
   ```

3. Run the container:
   ```bash
   docker-compose up -d
   ```

   Or manually:
   ```bash
   docker run -d \
     --name rss-feed-api \
     -p 5000:5000 \
     -e RSS_STORAGE_FILE="/data/feeds.json" \
     -e GENERAL_FEED_TITLE="All Feeds" \
     -e HISTORY_DAYS=30 \
     -v $(pwd)/data:/data \
      asterix94/rss-rest-api
   ```

## Configuration

The API can be configured using environment variables:

| Environment Variable | Description | Default |
|---------------------|-------------|---------|
| `RSS_STORAGE_FILE` | Path to the storage file | feeds.json |
| `HISTORY_DAYS` | Number of days to keep in history | 30 |
| `MAX_ENTRIES_PER_FEED` | Maximum number of entries per feed | 100 |
| `GENERAL_FEED_TITLE` | title for feed (global) | All Feeds |
| `PORT` | Port to expose the API | 5000 |
| `DEBUG` | Debug mode (true/false) | False |

## API Documentation

The complete OpenAPI documentation is available at `/docs` when the service is running. The OpenAPI specification files are located in the `openapi` folder of the repository.

### Key Endpoints

#### Get all feeds (JSON)
```
GET /feeds
```

#### Get a specific feed (JSON)
```
GET /feeds/{feed_id}
```

#### Get feeds in XML format
```
GET /feeds/xml
GET /feeds/{feed_id}/xml
```

#### Create a new feed
```
POST /feeds
```

#### Add an entry to a feed
```
POST /feeds/{feed_id}/entries
```

#### Search feeds with filters
```
GET /feeds/search
```

#### Delete a feed
```
DELETE /feeds/{feed_id}
```

#### Service status
```
GET /status
```

## Usage Examples

### Create a new feed

```bash
curl -X POST http://localhost:5000/feeds \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Tech Blog",
    "link": "https://tech-blog.com",
    "description": "Latest tech news",
    "language": "en-US",
    "imageUrl": "https://tech-blog.com/logo.jpg",
    "entries": [
      {
        "title": "Artificial Intelligence in 2025",
        "link": "https://tech-blog.com/ai-2025",
        "description": "How AI is changing the world",
        "pubDate": "Mon, 13 May 2025 10:00:00 GMT",
        "imageUrl": "https://tech-blog.com/images/ai.jpg"
      }
    ]
  }'
```

### Add an entry to an existing feed

```bash
curl -X POST http://localhost:5000/feeds/1234-5678/entries \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Web 3.0: The Next Evolution",
    "link": "https://tech-blog.com/web3",
    "description": "What to expect from Web 3.0",
    "pubDate": "Tue, 13 May 2025 08:15:00 GMT",
    "imageUrl": "https://tech-blog.com/images/web3.jpg"
  }'
```

### Get filtered feeds

```bash
# Get articles with "intelligence" in the title in JSON format
curl "http://localhost:5000/feeds/search?title=intelligence&format=json"

# Get articles published between two dates in XML format
curl "http://localhost:5000/feeds/search?from_date=2025-05-01&to_date=2025-05-15&format=xml"
```

## Data Persistence

When using Docker, the API stores data in the mounted `/data` directory:

- `feeds.json`: Contains all feed data and entries

Make sure to mount this directory as a volume to ensure data persistence between container restarts.

## Project Structure

- `rss-rest-api.py`: Flask application with API endpoints
- `models/`: Data models for feeds and entries
- `services/`: Business logic for feed management
- `openapi/`: OpenAPI/Swagger specification files
- `Dockerfile`: Configuration for building the Docker image
- `docker-compose.yml`: Configuration for starting with Docker Compose
- `requirements.txt`: Python dependencies

## Data Model

### Feed
A feed consists of:
- `feedId`: Unique identifier for the feed
- `title`: Feed title
- `link`: Feed URL
- `description`: Feed description
- `language`: Feed language (default: en-US)
- `imageUrl`: URL of the image associated with the feed (optional)
- `entries`: List of feed entries

### Feed Entry
A feed entry consists of:
- `title`: Entry title
- `link`: Entry URL
- `description`: Entry description
- `pubDate`: Publication date (RFC822 format)
- `guid`: Unique identifier for the entry (automatically generated if not provided)
- `imageUrl`: URL of the image associated with the entry (optional)

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.