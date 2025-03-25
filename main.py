import xml.etree.ElementTree as ET
import plistlib
import os
from elasticsearch import Elasticsearch
import time
import logging
from typing import Dict, Any, List

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def connect_to_elasticsearch() -> Elasticsearch:
    """Connect to the Elasticsearch instance with retry logic."""
    es = None
    max_retries = 5
    retry_interval = 10  # seconds
    
    for attempt in range(max_retries):
        try:
            es = Elasticsearch("http://localhost:9200")
            if es.ping():
                logger.info("Connected to Elasticsearch")
                return es
            raise ConnectionError("Failed to ping Elasticsearch")
        except Exception as e:
            logger.warning(f"Attempt {attempt+1}/{max_retries} to connect failed: {e}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_interval} seconds...")
                time.sleep(retry_interval)
    
    raise ConnectionError("Failed to connect to Elasticsearch after multiple attempts")

def setup_elasticsearch_index(es: Elasticsearch) -> None:
    """Create the Elasticsearch index with appropriate mappings."""
    # Delete index if it exists
    if es.indices.exists(index="itunes"):
        es.indices.delete(index="itunes")
    
    # Define mapping
    mappings = {
        "mappings": {
            "properties": {
                "track_id": {"type": "keyword"},
                "name": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                "artist": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                "album": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                "genre": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                "total_time": {"type": "long"},  # in milliseconds
                "year": {"type": "integer"},
                "date_added": {"type": "date"},
                "play_count": {"type": "integer"},
                "skip_count": {"type": "integer"},
                "last_played": {"type": "date"},
                "bit_rate": {"type": "integer"},
                "track_number": {"type": "integer"},
                "album_artist": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                "kind": {"type": "keyword"},
                "location": {"type": "keyword"}
            }
        }
    }
    
    # Create index with mappings
    es.indices.create(index="itunes", body=mappings)
    logger.info("Created Elasticsearch index with mappings")

def load_itunes_library(file_path: str) -> Dict[str, Any]:
    """Load the iTunes library XML file."""
    logger.info(f"Loading iTunes library from {file_path}")
    with open(file_path, 'rb') as fp:
        return plistlib.load(fp)

def transform_track(track: Dict[str, Any]) -> Dict[str, Any]:
    """Transform a track dictionary to match Elasticsearch mapping."""
    # Handle date fields properly - make sure they're either valid dates or None (null in Elasticsearch)
    date_added = track.get("Date Added")
    last_played = track.get("Play Date UTC")
    
    result = {
        "track_id": str(track.get("Track ID", "")),
        "name": track.get("Name", ""),
        "artist": track.get("Artist", ""),
        "album": track.get("Album", ""),
        "album_artist": track.get("Album Artist", ""),
        "genre": track.get("Genre", ""),
        "total_time": track.get("Total Time", 0),  # in milliseconds
        "year": track.get("Year", 0),
        "play_count": track.get("Play Count", 0),
        "skip_count": track.get("Skip Count", 0),
        "bit_rate": track.get("Bit Rate", 0),
        "track_number": track.get("Track Number", 0),
        "kind": track.get("Kind", ""),
        "location": track.get("Location", "")
    }
    
    # Only add date fields if they exist and are not empty
    if date_added:
        result["date_added"] = date_added
    
    if last_played:
        result["last_played"] = last_played
        
    return result

def index_tracks(es: Elasticsearch, tracks: Dict[str, Dict[str, Any]]) -> None:
    """Index all tracks into Elasticsearch."""
    logger.info(f"Indexing {len(tracks)} tracks into Elasticsearch")
    
    for track_id, track_data in tracks.items():
        # Some entries might not be actual tracks
        if "Track ID" not in track_data or "Name" not in track_data:
            continue
            
        es_track = transform_track(track_data)
        es.index(index="itunes", id=es_track["track_id"], document=es_track)
    
    # Refresh index to make sure the data is available for search
    es.indices.refresh(index="itunes")
    logger.info("Finished indexing tracks")

def main():
    """Main entry point for the application."""
    logger.info("Starting iTunes XML insights application")
    
    # Connect to Elasticsearch
    try:
        es = connect_to_elasticsearch()
    except ConnectionError as e:
        logger.error(f"Failed to connect to Elasticsearch: {e}")
        logger.info("Make sure Docker containers are running: docker-compose up -d")
        return
    
    # Setup Elasticsearch index
    setup_elasticsearch_index(es)
    
    # Load iTunes XML library
    xml_path = "iTunes Music Library.xml"
    if not os.path.exists(xml_path):
        logger.error(f"iTunes XML file not found at {xml_path}")
        return
    
    try:
        library = load_itunes_library(xml_path)
    except Exception as e:
        logger.error(f"Failed to load iTunes library: {e}")
        return
    
    # Extract and index tracks
    tracks = library.get("Tracks", {})
    index_tracks(es, tracks)
    
    # Print some summary statistics from Elasticsearch
    try:
        count = es.count(index="itunes")
        logger.info(f"Successfully indexed {count['count']} tracks")
        
        # Print info about accessing Kibana
        logger.info("\n" + "="*80)
        logger.info("Data ingestion complete!")
        logger.info("Access Kibana at http://localhost:5601")
        logger.info("="*80)
        
        # Set up Kibana dashboards
        logger.info("Setting up Kibana dashboards...")
        try:
            from kibana_setup import setup_kibana
            setup_kibana()
        except Exception as e:
            logger.error(f"Error setting up Kibana dashboards: {e}")
            logger.info("You can still access Kibana and create dashboards manually")
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")

if __name__ == "__main__":
    main()