import os
import json
import uuid
import datetime
from typing import List, Optional, Dict, Any
import xml.etree.ElementTree as ET
from xml.dom import minidom
from flask import Flask, request, jsonify, Response
import threading
import time

app = Flask(__name__)

# env vars
STORAGE_FILE = os.environ.get("RSS_STORAGE_FILE", "feeds.json")
HISTORY_DAYS = int(os.environ.get("HISTORY_DAYS", "30"))
MAX_ENTRIES_PER_FEED = int(os.environ.get("MAX_ENTRIES_PER_FEED", "100"))
GENERAL_FEED_TITLE = os.environ.get("GENERAL_FEED_TITLE", "All Feeds")

# data model for entity feed
class FeedEntry:
    def __init__(self, 
                 title: str, 
                 link: str, 
                 description: str, 
                 pub_date: str,
                 guid: Optional[str] = None,
                 image_url: Optional[str] = None):
        self.title = title
        self.link = link
        self.description = description
        self.pub_date = pub_date
        self.guid = guid or str(uuid.uuid4())
        self.image_url = image_url
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "link": self.link,
            "description": self.description,
            "pubDate": self.pub_date,
            "guid": self.guid,
            "imageUrl": self.image_url
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FeedEntry':
        return cls(
            title=data["title"],
            link=data["link"],
            description=data["description"],
            pub_date=data["pubDate"],
            guid=data.get("guid"),
            image_url=data.get("imageUrl")
        )

# datamodel feed RSS
class RssFeed:
    def __init__(self, 
                 title: str, 
                 link: str, 
                 description: str,
                 language: str = "en-US",
                 feed_id: Optional[str] = None,
                 entries: Optional[List[FeedEntry]] = None,
                 image_url: Optional[str] = None):
        self.title = title
        self.link = link
        self.description = description
        self.language = language
        self.feed_id = feed_id or str(uuid.uuid4())
        self.entries = entries or []
        self.image_url = image_url
    
    def add_entry(self, entry: FeedEntry) -> None:
        self.entries.insert(0, entry)
        
        # entry limit
        if len(self.entries) > MAX_ENTRIES_PER_FEED:
            self.entries = self.entries[:MAX_ENTRIES_PER_FEED]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "feedId": self.feed_id,
            "title": self.title,
            "link": self.link,
            "description": self.description,
            "language": self.language,
            "imageUrl": self.image_url,
            "entries": [entry.to_dict() for entry in self.entries]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RssFeed':
        feed = cls(
            title=data["title"],
            link=data["link"],
            description=data["description"],
            language=data.get("language", "en-US"),
            feed_id=data.get("feedId"),
            image_url=data.get("imageUrl")
        )
        
        feed.entries = [FeedEntry.from_dict(entry) for entry in data.get("entries", [])]
        return feed
    
    def to_xml(self) -> str:
        """Convert the feed to RSS XML format."""
        rss = ET.Element("rss", version="2.0")
        channel = ET.SubElement(rss, "channel")
        
        # channel info
        ET.SubElement(channel, "title").text = self.title
        ET.SubElement(channel, "link").text = self.link
        ET.SubElement(channel, "description").text = self.description
        ET.SubElement(channel, "language").text = self.language
        
        # channel image
        if self.image_url:
            image = ET.SubElement(channel, "image")
            ET.SubElement(image, "url").text = self.image_url
            ET.SubElement(image, "title").text = self.title
            ET.SubElement(image, "link").text = self.link
        
        # feed elements
        for entry in self.entries:
            item = ET.SubElement(channel, "item")
            ET.SubElement(item, "title").text = entry.title
            ET.SubElement(item, "link").text = entry.link
            ET.SubElement(item, "description").text = entry.description
            ET.SubElement(item, "pubDate").text = entry.pub_date
            ET.SubElement(item, "guid", isPermaLink="false").text = entry.guid
            
            # image of entry
            if entry.image_url:
                enclosure = ET.SubElement(item, "enclosure", 
                                         url=entry.image_url, 
                                         type="image/jpeg")
        
        # convert xml
        rough_string = ET.tostring(rss, 'utf-8')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ")

class FeedStorage:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(FeedStorage, cls).__new__(cls)
                cls._instance.feeds = {}
                cls._instance.load()
                # start cleaning thread
                cleanup_thread = threading.Thread(target=cls._instance._cleanup_old_entries, daemon=True)
                cleanup_thread.start()
            return cls._instance
    
    def load(self) -> None:
        """Load feeds from storage file."""
        try:
            if os.path.exists(STORAGE_FILE):
                with open(STORAGE_FILE, 'r', encoding='utf-8') as file:
                    data = json.load(file)
                    self.feeds = {
                        feed_id: RssFeed.from_dict(feed_data)
                        for feed_id, feed_data in data.items()
                    }
                print(f"Loaded {len(self.feeds)} feeds from file {STORAGE_FILE}")
            else:
                print(f"File {STORAGE_FILE} not found, initializing with empty storage")
                self.feeds = {}
        except Exception as e:
            print(f"Error loading feeds: {e}")
            self.feeds = {}
    
    def save(self) -> None:
        """Save feeds to storage file."""
        try:
            with open(STORAGE_FILE, 'w', encoding='utf-8') as file:
                data = {
                    feed_id: feed.to_dict()
                    for feed_id, feed in self.feeds.items()
                }
                json.dump(data, file, ensure_ascii=False, indent=2)
            print(f"Saved {len(self.feeds)} feeds to file {STORAGE_FILE}")
        except Exception as e:
            print(f"Error saving feeds: {e}")
    
    def add_feed(self, feed: RssFeed) -> str:
        """Add a new feed to storage."""
        self.feeds[feed.feed_id] = feed
        self.save()
        return feed.feed_id
    
    def get_feed(self, feed_id: str) -> Optional[RssFeed]:
        """Get a specific feed from storage."""
        return self.feeds.get(feed_id)
    
    def get_all_feeds(self) -> List[RssFeed]:
        """Get all feeds from storage."""
        return list(self.feeds.values())
    
    def delete_feed(self, feed_id: str) -> bool:
        """Delete a feed from storage."""
        if feed_id in self.feeds:
            del self.feeds[feed_id]
            self.save()
            return True
        return False
    
    def add_entry_to_feed(self, feed_id: str, entry: FeedEntry) -> bool:
        """Add an entry to a specific feed."""
        feed = self.get_feed(feed_id)
        if feed:
            feed.add_entry(entry)
            self.save()
            return True
        return False
    
    def _cleanup_old_entries(self) -> None:
        """Thread that periodically cleans old entries from feeds."""
        while True:
            try:
                now = datetime.datetime.now()
                cutoff_date = now - datetime.timedelta(days=HISTORY_DAYS)
                cutoff_str = cutoff_date.strftime("%a, %d %b %Y %H:%M:%S GMT")
                
                feeds_modified = False
                
                for feed in self.feeds.values():
                    old_count = len(feed.entries)
                    feed.entries = [
                        entry for entry in feed.entries
                        if self._parse_date(entry.pub_date) > cutoff_date
                    ]
                    if len(feed.entries) < old_count:
                        feeds_modified = True
                
                if feeds_modified:
                    self.save()
                    print(f"Removal of entries older than {HISTORY_DAYS} days completed")
                
                #  clean every day
                time.sleep(86400)
            except Exception as e:
                print(f"Error cleaning old entries: {e}")
                time.sleep(3600)  # retry after 1 hour
    
    def _parse_date(self, date_str: str) -> datetime.datetime:
        """Convert a date string in RFC822 format to a datetime object."""
        try:
            formats = [
                "%a, %d %b %Y %H:%M:%S %Z",
                "%a, %d %b %Y %H:%M:%S GMT",
                "%a, %d %b %Y %H:%M:%S +0000",
                "%Y-%m-%dT%H:%M:%S%z",
                "%Y-%m-%dT%H:%M:%SZ"
            ]
            
            for fmt in formats:
                try:
                    return datetime.datetime.strptime(date_str, fmt)
                except ValueError:
                    continue

            return datetime.datetime.now()
        except Exception:
            return datetime.datetime.now()
    
    def filter_feeds(self, query_params: Dict[str, str]) -> List[RssFeed]:
        """Filter feeds based on query parameters."""
        filtered_feeds = []
        
        for feed in self.feeds.values():
            feed_copy = RssFeed(
                title=feed.title,
                link=feed.link,
                description=feed.description,
                language=feed.language,
                feed_id=feed.feed_id,
                image_url=feed.image_url
            )
            
            # filter feed element
            filtered_entries = feed.entries
            
            # title
            if 'title' in query_params:
                title_query = query_params['title'].lower()
                filtered_entries = [e for e in filtered_entries 
                                  if title_query in e.title.lower()]
            
            # description
            if 'description' in query_params:
                desc_query = query_params['description'].lower()
                filtered_entries = [e for e in filtered_entries 
                                   if desc_query in e.description.lower()]
            
            # date (from)
            if 'from_date' in query_params:
                try:
                    from_date = datetime.datetime.fromisoformat(query_params['from_date'])
                    filtered_entries = [e for e in filtered_entries 
                                       if self._parse_date(e.pub_date) >= from_date]
                except ValueError:
                    pass
            
            # date (to)
            if 'to_date' in query_params:
                try:
                    to_date = datetime.datetime.fromisoformat(query_params['to_date'])
                    filtered_entries = [e for e in filtered_entries 
                                       if self._parse_date(e.pub_date) <= to_date]
                except ValueError:
                    pass
            
            # limit feeds
            if 'limit' in query_params:
                try:
                    limit = int(query_params['limit'])
                    filtered_entries = filtered_entries[:limit]
                except ValueError:
                    pass
            
            feed_copy.entries = filtered_entries
            
            if filtered_entries or query_params.get('include_empty', 'false').lower() == 'true':
                filtered_feeds.append(feed_copy)
        
        return filtered_feeds

storage = FeedStorage()

#
# API Endpoints
#

@app.route('/feeds', methods=['GET'])
def get_all_feeds():
    """Endpoint to get all feeds in JSON format."""
    feeds = storage.get_all_feeds()
    return jsonify({
        "count": len(feeds),
        "feeds": [feed.to_dict() for feed in feeds]
    })

@app.route('/feeds/<feed_id>', methods=['GET'])
def get_feed(feed_id):
    """Endpoint to get a specific feed in JSON format."""
    feed = storage.get_feed(feed_id)
    if feed:
        return jsonify(feed.to_dict())
    else:
        return jsonify({"error": "Feed not found"}), 404

@app.route('/feeds/<feed_id>/xml', methods=['GET'])
def get_feed_xml(feed_id):
    """Endpoint to get a specific feed in XML format."""
    feed = storage.get_feed(feed_id)
    if feed:
        xml_content = feed.to_xml()
        return Response(xml_content, mimetype='application/xml')
    else:
        return jsonify({"error": "Feed not found"}), 404

@app.route('/feeds/xml', methods=['GET'])
def get_all_feeds_xml():
    """Endpoint to get all feeds in XML format."""

    combined_feed = RssFeed(
        title=GENERAL_FEED_TITLE,
        link=request.host_url,
        description="Combination of all available feeds"
    )
    
    for feed in storage.get_all_feeds():
        for entry in feed.entries:

            entry_copy = FeedEntry(
                title=f"[{feed.title}] {entry.title}",
                link=entry.link,
                description=entry.description,
                pub_date=entry.pub_date,
                guid=entry.guid,
                image_url=entry.image_url
            )
            combined_feed.add_entry(entry_copy)
    
    # order element by date
    combined_feed.entries.sort(
        key=lambda e: storage._parse_date(e.pub_date),
        reverse=True
    )
    
    xml_content = combined_feed.to_xml()
    return Response(xml_content, mimetype='application/xml')

@app.route('/feeds', methods=['POST'])
def create_feed():
    """Endpoint to create a new feed."""
    try:
        data = request.json
        
        # validation
        required_fields = ['title', 'link', 'description']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        # create new feed
        feed = RssFeed(
            title=data['title'],
            link=data['link'],
            description=data['description'],
            language=data.get('language', 'en-US'),
            image_url=data.get('imageUrl')
        )
        
        # add element to feed
        for entry_data in data.get('entries', []):
            if all(k in entry_data for k in ['title', 'link', 'description', 'pubDate']):
                entry = FeedEntry(
                    title=entry_data['title'],
                    link=entry_data['link'],
                    description=entry_data['description'],
                    pub_date=entry_data['pubDate'],
                    guid=entry_data.get('guid'),
                    image_url=entry_data.get('imageUrl')
                )
                feed.add_entry(entry)
        
        # save
        feed_id = storage.add_feed(feed)
        
        return jsonify({
            "message": "Feed created successfully",
            "feedId": feed_id
        }), 201
    
    except Exception as e:
        return jsonify({"error": f"Error creating feed: {str(e)}"}), 500

@app.route('/feeds/<feed_id>/entries', methods=['POST'])
def add_feed_entry(feed_id):
    """Endpoint to add an entry to an existing feed."""
    try:
        feed = storage.get_feed(feed_id)
        if not feed:
            return jsonify({"error": "Feed not found"}), 404
        
        data = request.json
        
        # validation
        required_fields = ['title', 'link', 'description', 'pubDate']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        # create new element
        entry = FeedEntry(
            title=data['title'],
            link=data['link'],
            description=data['description'],
            pub_date=data['pubDate'],
            guid=data.get('guid'),
            image_url=data.get('imageUrl')
        )
        
        # add to feed
        storage.add_entry_to_feed(feed_id, entry)
        
        return jsonify({
            "message": "Entry added successfully",
            "entryId": entry.guid
        })
    
    except Exception as e:
        return jsonify({"error": f"Error adding entry: {str(e)}"}), 500

@app.route('/feeds/search', methods=['GET'])
def search_feeds():
    """Endpoint to search feeds based on query parameters."""
    query_params = request.args.to_dict()
    
    filtered_feeds = storage.filter_feeds(query_params)
    
    output_format = query_params.get('format', 'json').lower()
    
    if output_format == 'xml':
        combined_feed = RssFeed(
            title="Search Results",
            link=request.url,
            description=f"Feeds filtered by parameters: {query_params}"
        )
        
        for feed in filtered_feeds:
            for entry in feed.entries:

                entry_copy = FeedEntry(
                    title=f"[{feed.title}] {entry.title}",
                    link=entry.link,
                    description=entry.description,
                    pub_date=entry.pub_date,
                    guid=entry.guid,
                    image_url=entry.image_url
                )
                combined_feed.add_entry(entry_copy)
        
        xml_content = combined_feed.to_xml()
        return Response(xml_content, mimetype='application/xml')
    else:
        # format json
        return jsonify({
            "count": len(filtered_feeds),
            "query": query_params,
            "feeds": [feed.to_dict() for feed in filtered_feeds]
        })

@app.route('/feeds/<feed_id>', methods=['DELETE'])
def delete_feed(feed_id):
    """Endpoint to delete a feed."""
    if storage.delete_feed(feed_id):
        return jsonify({"message": "Feed deleted successfully"})
    else:
        return jsonify({"error": "Feed not found"}), 404

@app.route('/status', methods=['GET'])
def get_status():
    """Endpoint to check service status."""
    return jsonify({
        "status": "online",
        "feeds_count": len(storage.feeds),
        "history_days": HISTORY_DAYS,
        "max_entries_per_feed": MAX_ENTRIES_PER_FEED,
        "storage_file": STORAGE_FILE
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("DEBUG", "False").lower() == "true"
    app.run(host='0.0.0.0', port=port, debug=debug)