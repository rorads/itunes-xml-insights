import xml.etree.ElementTree as ET
import plistlib
import os
from elasticsearch import Elasticsearch
import time
import logging
from collections import defaultdict
from typing import Dict, Any, List, Set, DefaultDict

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

def setup_elasticsearch_indices(es: Elasticsearch) -> None:
    """Create all Elasticsearch indices with appropriate mappings."""
    # Define all indices to create
    indices = ["tracks", "artists", "albums", "genres"]
    
    # Delete indices if they exist
    for index in indices:
        if es.indices.exists(index=index):
            logger.info(f"Deleting existing index: {index}")
            es.indices.delete(index=index)
    
    # Define and create tracks index
    tracks_mapping = {
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
                "date_modified": {"type": "date"},
                "release_date": {"type": "date"},
                "play_count": {"type": "integer"},
                "skip_count": {"type": "integer"},
                "last_played": {"type": "date"},
                "skip_date": {"type": "date"},
                "bit_rate": {"type": "integer"},
                "sample_rate": {"type": "integer"},
                "track_number": {"type": "integer"},
                "disc_number": {"type": "integer"},
                "disc_count": {"type": "integer"},
                "album_artist": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                "composer": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                "kind": {"type": "keyword"},
                "size": {"type": "long"},
                "rating": {"type": "integer"},  # 0-100
                "album_rating": {"type": "integer"},  # 0-100
                "rating_computed": {"type": "boolean"},
                "album_rating_computed": {"type": "boolean"},
                "compilation": {"type": "boolean"},
                "explicit": {"type": "boolean"},
                "location": {"type": "keyword"},
                # Add the BPM field
                "bpm": {"type": "integer"},
                # Add grouping field
                "grouping": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                # Add comments field
                "comments": {"type": "text"}
            }
        }
    }
    
    # Define artist index mapping
    artists_mapping = {
        "mappings": {
            "properties": {
                "name": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                "track_count": {"type": "integer"},
                "albums": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                "total_play_count": {"type": "integer"},
                "total_skip_count": {"type": "integer"},
                "avg_rating": {"type": "float"},
                "genres": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                "first_added": {"type": "date"},
                "last_played": {"type": "date"}
            }
        }
    }
    
    # Define album index mapping
    albums_mapping = {
        "mappings": {
            "properties": {
                "name": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                "artist": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                "year": {"type": "integer"},
                "track_count": {"type": "integer"},
                "total_time": {"type": "long"},  # total duration in ms
                "avg_bit_rate": {"type": "float"},
                "genres": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                "rating": {"type": "integer"},
                "compilation": {"type": "boolean"},
                "release_date": {"type": "date"},
                "first_added": {"type": "date"},
                "last_added": {"type": "date"},
                "total_play_count": {"type": "integer"},
                "total_skip_count": {"type": "integer"}
            }
        }
    }
    
    # Define genre index mapping
    genres_mapping = {
        "mappings": {
            "properties": {
                "name": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                "track_count": {"type": "integer"},
                "artist_count": {"type": "integer"},
                "album_count": {"type": "integer"},
                "total_time": {"type": "long"},
                "avg_bit_rate": {"type": "float"},
                "avg_rating": {"type": "float"},
                "avg_play_count": {"type": "float"},
                "total_play_count": {"type": "integer"}
            }
        }
    }
    
    # Create indices with their respective mappings
    index_mappings = {
        "tracks": tracks_mapping,
        "artists": artists_mapping,
        "albums": albums_mapping,
        "genres": genres_mapping
    }
    
    for index, mapping in index_mappings.items():
        logger.info(f"Creating index: {index}")
        es.indices.create(index=index, body=mapping)
    
    logger.info(f"Created {len(indices)} Elasticsearch indices with mappings")

def load_itunes_library(file_path: str) -> Dict[str, Any]:
    """Load the iTunes library XML file."""
    logger.info(f"Loading iTunes library from {file_path}")
    with open(file_path, 'rb') as fp:
        return plistlib.load(fp)

def transform_track(track: Dict[str, Any]) -> Dict[str, Any]:
    """Transform a track dictionary to match Elasticsearch mapping."""
    # Define fields to capture, with their source keys and default values
    field_mapping = {
        "track_id": ("Track ID", ""),
        "name": ("Name", ""),
        "artist": ("Artist", ""),
        "album": ("Album", ""),
        "album_artist": ("Album Artist", ""),
        "genre": ("Genre", ""),
        "total_time": ("Total Time", 0),
        "year": ("Year", 0),
        "play_count": ("Play Count", 0),
        "skip_count": ("Skip Count", 0),
        "bit_rate": ("Bit Rate", 0),
        "sample_rate": ("Sample Rate", 0),
        "track_number": ("Track Number", 0),
        "disc_number": ("Disc Number", 0),
        "disc_count": ("Disc Count", 0),
        "composer": ("Composer", ""),
        "kind": ("Kind", ""),
        "size": ("Size", 0),
        "rating": ("Rating", None),
        "album_rating": ("Album Rating", None),
        "rating_computed": ("Rating Computed", None),
        "album_rating_computed": ("Album Rating Computed", None),
        "compilation": ("Compilation", None),
        "explicit": ("Explicit", None),
        "location": ("Location", ""),
        "bpm": ("BPM", None),
        "grouping": ("Grouping", ""),
        "comments": ("Comments", "")
    }
    
    # Process date fields separately
    date_fields = {
        "date_added": "Date Added",
        "date_modified": "Date Modified",
        "last_played": "Play Date UTC",
        "skip_date": "Skip Date",
        "release_date": "Release Date"
    }
    
    # Create the base result dictionary
    result = {}
    
    # Process standard fields
    for es_field, (track_field, default) in field_mapping.items():
        value = track.get(track_field, default)
        
        # Convert Track ID to string
        if es_field == "track_id":
            value = str(value)
            
        # Only add non-None values
        if value is not None:
            result[es_field] = value
    
    # Process date fields
    for es_field, track_field in date_fields.items():
        value = track.get(track_field)
        if value is not None:
            result[es_field] = value
    
    return result

def process_library(library: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Process the iTunes library and transform it into structured data for Elasticsearch.
    
    Args:
        library: The loaded iTunes library
        
    Returns:
        Dictionary with data for each index
    """
    # Get the tracks data
    tracks_data = library.get("Tracks", {})
    logger.info(f"Processing {len(tracks_data)} tracks")
    
    # Initialize result structures
    track_docs = []
    
    # Initialize aggregation structures
    artists_data: DefaultDict[str, Dict[str, Any]] = defaultdict(lambda: {
        "name": "",
        "track_count": 0,
        "albums": set(),
        "total_play_count": 0,
        "total_skip_count": 0,
        "ratings": [],
        "genres": set(),
        "first_added": None,
        "last_played": None
    })
    
    albums_data: DefaultDict[str, Dict[str, Any]] = defaultdict(lambda: {
        "name": "",
        "artist": "",
        "year": None,
        "track_count": 0,
        "total_time": 0,
        "bit_rates": [],
        "genres": set(),
        "ratings": [],
        "compilation": False,
        "release_date": None,
        "added_dates": [],
        "total_play_count": 0,
        "total_skip_count": 0
    })
    
    genres_data: DefaultDict[str, Dict[str, Any]] = defaultdict(lambda: {
        "name": "",
        "track_count": 0,
        "artists": set(),
        "albums": set(),
        "total_time": 0,
        "bit_rates": [],
        "ratings": [],
        "play_counts": []
    })
    
    # Process each track
    for track_id, track_data in tracks_data.items():
        # Skip entries that don't seem to be proper tracks
        if "Track ID" not in track_data or "Name" not in track_data:
            continue
        
        # Transform track for ES
        es_track = transform_track(track_data)
        track_docs.append(es_track)
        
        # Extract data for aggregation
        artist = track_data.get("Artist", "Unknown")
        album = track_data.get("Album", "Unknown")
        album_artist = track_data.get("Album Artist", artist)
        genre = track_data.get("Genre", "Unknown")
        
        # Create a unique album key
        album_key = f"{album_artist} - {album}"
        
        # Aggregate artist data
        if artist:
            artists_data[artist]["name"] = artist
            artists_data[artist]["track_count"] += 1
            
            if album:
                artists_data[artist]["albums"].add(album)
            
            play_count = track_data.get("Play Count", 0)
            artists_data[artist]["total_play_count"] += play_count
            
            skip_count = track_data.get("Skip Count", 0)
            artists_data[artist]["total_skip_count"] += skip_count
            
            rating = track_data.get("Rating")
            if rating is not None:
                artists_data[artist]["ratings"].append(rating)
            
            if genre:
                artists_data[artist]["genres"].add(genre)
            
            date_added = track_data.get("Date Added")
            if date_added:
                if artists_data[artist]["first_added"] is None or date_added < artists_data[artist]["first_added"]:
                    artists_data[artist]["first_added"] = date_added
            
            last_played = track_data.get("Play Date UTC")
            if last_played:
                if artists_data[artist]["last_played"] is None or last_played > artists_data[artist]["last_played"]:
                    artists_data[artist]["last_played"] = last_played
        
        # Aggregate album data
        if album:
            albums_data[album_key]["name"] = album
            albums_data[album_key]["artist"] = album_artist
            albums_data[album_key]["track_count"] += 1
            
            year = track_data.get("Year")
            if year and (albums_data[album_key]["year"] is None or year < albums_data[album_key]["year"]):
                albums_data[album_key]["year"] = year
            
            total_time = track_data.get("Total Time", 0)
            albums_data[album_key]["total_time"] += total_time
            
            bit_rate = track_data.get("Bit Rate")
            if bit_rate:
                albums_data[album_key]["bit_rates"].append(bit_rate)
            
            if genre:
                albums_data[album_key]["genres"].add(genre)
            
            rating = track_data.get("Rating")
            if rating is not None:
                albums_data[album_key]["ratings"].append(rating)
            
            compilation = track_data.get("Compilation", False)
            if compilation:
                albums_data[album_key]["compilation"] = True
            
            release_date = track_data.get("Release Date")
            if release_date:
                if albums_data[album_key]["release_date"] is None or release_date < albums_data[album_key]["release_date"]:
                    albums_data[album_key]["release_date"] = release_date
            
            date_added = track_data.get("Date Added")
            if date_added:
                albums_data[album_key]["added_dates"].append(date_added)
            
            play_count = track_data.get("Play Count", 0)
            albums_data[album_key]["total_play_count"] += play_count
            
            skip_count = track_data.get("Skip Count", 0)
            albums_data[album_key]["total_skip_count"] += skip_count
        
        # Aggregate genre data
        if genre:
            genres_data[genre]["name"] = genre
            genres_data[genre]["track_count"] += 1
            
            if artist:
                genres_data[genre]["artists"].add(artist)
            
            if album:
                genres_data[genre]["albums"].add(album)
            
            total_time = track_data.get("Total Time", 0)
            genres_data[genre]["total_time"] += total_time
            
            bit_rate = track_data.get("Bit Rate")
            if bit_rate:
                genres_data[genre]["bit_rates"].append(bit_rate)
            
            rating = track_data.get("Rating")
            if rating is not None:
                genres_data[genre]["ratings"].append(rating)
            
            play_count = track_data.get("Play Count", 0)
            genres_data[genre]["play_counts"].append(play_count)
    
    # Finalize artist documents
    artist_docs = []
    for artist, data in artists_data.items():
        artist_doc = {
            "name": data["name"],
            "track_count": data["track_count"],
            "albums": list(data["albums"]),
            "total_play_count": data["total_play_count"],
            "total_skip_count": data["total_skip_count"],
            "genres": list(data["genres"]),
            "first_added": data["first_added"],
            "last_played": data["last_played"]
        }
        
        # Calculate average rating if any ratings exist
        if data["ratings"]:
            artist_doc["avg_rating"] = sum(data["ratings"]) / len(data["ratings"])
        
        artist_docs.append(artist_doc)
    
    # Finalize album documents
    album_docs = []
    for album_key, data in albums_data.items():
        album_doc = {
            "name": data["name"],
            "artist": data["artist"],
            "year": data["year"],
            "track_count": data["track_count"],
            "total_time": data["total_time"],
            "genres": list(data["genres"]),
            "compilation": data["compilation"],
            "release_date": data["release_date"],
            "total_play_count": data["total_play_count"],
            "total_skip_count": data["total_skip_count"]
        }
        
        # Calculate average bit rate if any bit rates exist
        if data["bit_rates"]:
            album_doc["avg_bit_rate"] = sum(data["bit_rates"]) / len(data["bit_rates"])
        
        # Calculate average rating if any ratings exist
        if data["ratings"]:
            album_doc["rating"] = sum(data["ratings"]) / len(data["ratings"])
        
        # Set first and last added dates
        if data["added_dates"]:
            album_doc["first_added"] = min(data["added_dates"])
            album_doc["last_added"] = max(data["added_dates"])
        
        album_docs.append(album_doc)
    
    # Finalize genre documents
    genre_docs = []
    for genre, data in genres_data.items():
        genre_doc = {
            "name": data["name"],
            "track_count": data["track_count"],
            "artist_count": len(data["artists"]),
            "album_count": len(data["albums"]),
            "total_time": data["total_time"]
        }
        
        # Calculate average bit rate if any bit rates exist
        if data["bit_rates"]:
            genre_doc["avg_bit_rate"] = sum(data["bit_rates"]) / len(data["bit_rates"])
        
        # Calculate average rating if any ratings exist
        if data["ratings"]:
            genre_doc["avg_rating"] = sum(data["ratings"]) / len(data["ratings"])
        
        # Calculate play count statistics
        if data["play_counts"]:
            genre_doc["avg_play_count"] = sum(data["play_counts"]) / len(data["play_counts"])
            genre_doc["total_play_count"] = sum(data["play_counts"])
        
        genre_docs.append(genre_doc)
    
    return {
        "tracks": track_docs,
        "artists": artist_docs,
        "albums": album_docs,
        "genres": genre_docs
    }

def index_documents(es: Elasticsearch, docs_by_index: Dict[str, List[Dict[str, Any]]]) -> None:
    """
    Index all documents into their respective Elasticsearch indices.
    
    Args:
        es: Elasticsearch client
        docs_by_index: Dictionary with documents organized by index name
    """
    for index, docs in docs_by_index.items():
        logger.info(f"Indexing {len(docs)} documents into '{index}' index")
        
        # Determine the ID field based on the index
        id_field = "track_id" if index == "tracks" else "name"
        
        # Index each document
        for doc in docs:
            doc_id = doc.get(id_field)
            if not doc_id:
                continue
                
            es.index(index=index, id=doc_id, document=doc)
        
        # Refresh index to make sure the data is available for search
        es.indices.refresh(index=index)
        
    logger.info(f"Finished indexing all documents")

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
    
    # Setup Elasticsearch indices
    setup_elasticsearch_indices(es)
    
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
    
    # Process library and get documents for each index
    docs_by_index = process_library(library)
    
    # Index all documents
    index_documents(es, docs_by_index)
    
    # Print some summary statistics
    try:
        # Get counts for each index
        index_counts = {}
        for index in docs_by_index.keys():
            count = es.count(index=index)
            index_counts[index] = count["count"]
            logger.info(f"Successfully indexed {count['count']} documents in '{index}' index")
        
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