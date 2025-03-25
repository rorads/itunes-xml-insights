import requests
import json
import time
import logging
from typing import Dict, Any, List

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

KIBANA_URL = "http://localhost:5601"


def wait_for_kibana() -> None:
    """Wait for Kibana to be available."""
    logger.info("Waiting for Kibana to start...")
    max_retries = 60  # Increased to 60 retries (5 minutes)
    retry_interval = 5  # seconds

    for attempt in range(max_retries):
        try:
            response = requests.get(f"{KIBANA_URL}/api/status", timeout=10)
            if response.status_code == 200:
                logger.info("Kibana is running!")
                # Wait a bit longer to make sure Kibana is fully initialized
                logger.info("Waiting 10 more seconds for Kibana to fully initialize...")
                time.sleep(10)
                return
        except Exception as e:
            pass

        if (attempt + 1) % 5 == 0:  # Only log every 5 attempts to reduce output
            logger.info(f"Attempt {attempt+1}/{max_retries}, retrying in {retry_interval} seconds...")
        time.sleep(retry_interval)

    raise ConnectionError("Failed to connect to Kibana after multiple attempts")


def create_index_patterns() -> None:
    """Create Kibana index patterns for all data indices."""
    indices = ["tracks", "artists", "albums", "genres"]
    date_fields = {
        "tracks": "date_added",
        "artists": "first_added",
        "albums": "first_added",
        "genres": None  # No date field for genres
    }
    
    headers = {
        "kbn-xsrf": "true",
        "Content-Type": "application/json"
    }
    
    # Create each index pattern
    for index in indices:
        logger.info(f"Creating index pattern for '{index}'...")
        
        # Define index pattern attributes
        attributes = {
            "title": index,
        }
        
        # Add time field if applicable
        if date_fields[index]:
            attributes["timeFieldName"] = date_fields[index]
        
        data = {"attributes": attributes}
        
        # Send request to create index pattern
        response = requests.post(
            f"{KIBANA_URL}/api/saved_objects/index-pattern/{index}",
            headers=headers,
            json=data
        )
        
        if response.status_code in [200, 201]:
            logger.info(f"Successfully created index pattern for '{index}'")
        else:
            logger.warning(f"Failed to create index pattern for '{index}': {response.status_code} {response.text}")


def create_visualization(vis_id: str, title: str, vis_state: Dict[str, Any], index_pattern: str) -> None:
    """Create a Kibana visualization for a specific index pattern."""
    logger.info(f"Creating visualization: {title}")
    headers = {
        "kbn-xsrf": "true",
        "Content-Type": "application/json"
    }
    
    # Create visualization with no time constraints (will inherit from dashboard)
    data = {
        "attributes": {
            "title": title,
            "visState": json.dumps(vis_state),
            "uiStateJSON": "{}",
            "description": "",
            "kibanaSavedObjectMeta": {
                "searchSourceJSON": json.dumps({
                    "query": {"query": "", "language": "kuery"},
                    "filter": [],
                    "indexRefName": "kibanaSavedObjectMeta.searchSourceJSON.index"
                })
            }
        },
        "references": [
            {
                "name": "kibanaSavedObjectMeta.searchSourceJSON.index",
                "type": "index-pattern",
                "id": index_pattern
            }
        ]
    }
    
    response = requests.post(
        f"{KIBANA_URL}/api/saved_objects/visualization/{vis_id}",
        headers=headers,
        json=data
    )
    
    if response.status_code in [200, 201]:
        logger.info(f"Successfully created visualization: {title}")
    else:
        logger.warning(f"Failed to create visualization: {response.status_code} {response.text}")


def create_dashboard(visualizations: List[Dict[str, str]]) -> None:
    """Create a Kibana dashboard with the given visualizations."""
    logger.info("Creating iTunes Analysis dashboard...")
    
    # First, let's try to delete the existing dashboard if it exists
    headers = {
        "kbn-xsrf": "true",
    }
    
    try:
        requests.delete(
            f"{KIBANA_URL}/api/saved_objects/dashboard/itunes-analysis",
            headers=headers
        )
        logger.info("Deleted existing dashboard")
    except Exception:
        pass
    
    # Now create a dashboard using Kibana's expected format
    headers = {
        "kbn-xsrf": "true", 
        "Content-Type": "application/json"
    }
    
    # Create a simpler panel structure that correctly references visualizations
    panels = []
    references = []
    
    # Create panels with proper references
    y_position = 0
    for i, vis_info in enumerate(visualizations):
        vis_id = vis_info["id"]
        panel_id = f"panel_{i+1}"
        
        # For track visualizations, put them at the top in a grid
        if vis_info.get("section") == "tracks":
            if i % 2 == 0:  # Even index
                x_position = 0
            else:  # Odd index
                x_position = 24
                
            if i % 2 == 1:  # After every two track visualizations, move down
                y_position += 15
            
            width = 24
            height = 15
        else:
            # For other visualizations, use full width and stack vertically
            x_position = 0
            y_position += 15
            width = 48
            height = 15
        
        # Create panel
        panel = {
            "version": "8.5.0",
            "type": "visualization",
            "gridData": {
                "x": x_position,
                "y": y_position,
                "w": width,
                "h": height
            },
            "panelIndex": panel_id,
            "embeddableConfig": {},
            "panelRefName": panel_id
        }
        panels.append(panel)
        
        # Add reference
        references.append({
            "id": vis_id,
            "name": panel_id,
            "type": "visualization"
        })
    
    # Add index pattern references
    indices = ["tracks", "artists", "albums", "genres"]
    for index in indices:
        references.append({
            "id": index,
            "name": f"kibanaSavedObjectMeta.searchSourceJSON.index_{index}",
            "type": "index-pattern"
        })
    
    # Create the dashboard with all references
    data = {
        "attributes": {
            "title": "iTunes Music Analysis",
            "hits": 0,
            "description": "Analysis of iTunes Music Library with artist, album, and genre insights",
            "panelsJSON": json.dumps(panels),
            "optionsJSON": json.dumps({"hidePanelTitles": False, "useMargins": True}),
            "version": 1,
            "timeRestore": True,
            "timeFrom": "now-100y", 
            "timeTo": "now",
            "refreshInterval": {
                "pause": True,
                "value": 0
            },
            "kibanaSavedObjectMeta": {
                "searchSourceJSON": json.dumps({
                    "query": {"query": "", "language": "kuery"},
                    "filter": []
                })
            }
        },
        "references": references
    }
    
    response = requests.post(
        f"{KIBANA_URL}/api/saved_objects/dashboard/itunes-analysis",
        headers=headers,
        json=data
    )
    
    if response.status_code in [200, 201]:
        logger.info("Successfully created dashboard")
        logger.info("Access your iTunes Music Analysis dashboard at: http://localhost:5601/app/dashboards#/view/itunes-analysis")
    else:
        logger.warning(f"Failed to create dashboard: {response.status_code} {response.text}")


# Track visualizations
def create_top_artists_by_tracks() -> None:
    """Create Top Artists by Track Count visualization."""
    vis_state = {
        "title": "Top Artists by Track Count",
        "type": "pie",
        "aggs": [
            {
                "id": "1",
                "enabled": True,
                "type": "count",
                "schema": "metric",
                "params": {}
            },
            {
                "id": "2",
                "enabled": True,
                "type": "terms",
                "schema": "segment",
                "params": {
                    "field": "artist.keyword",
                    "orderBy": "1",
                    "order": "desc",
                    "size": 10,
                    "otherBucket": True,
                    "otherBucketLabel": "Other",
                    "missingBucket": False,
                    "missingBucketLabel": "Missing"
                }
            }
        ],
        "params": {
            "type": "pie",
            "addTooltip": True,
            "addLegend": True,
            "legendPosition": "right",
            "isDonut": False,
            "labels": {
                "show": True,
                "values": True,
                "last_level": True,
                "truncate": 100
            }
        }
    }
    create_visualization("top-artists-by-tracks", "Top Artists by Track Count", vis_state, "tracks")


def create_top_genres_visualization() -> None:
    """Create Top Genres visualization."""
    vis_state = {
        "title": "Top Genres",
        "type": "pie",
        "aggs": [
            {
                "id": "1",
                "enabled": True,
                "type": "count",
                "schema": "metric",
                "params": {}
            },
            {
                "id": "2",
                "enabled": True,
                "type": "terms",
                "schema": "segment",
                "params": {
                    "field": "genre.keyword",
                    "orderBy": "1",
                    "order": "desc",
                    "size": 10,
                    "otherBucket": True,
                    "otherBucketLabel": "Other",
                    "missingBucket": False,
                    "missingBucketLabel": "Missing"
                }
            }
        ],
        "params": {
            "type": "pie",
            "addTooltip": True,
            "addLegend": True,
            "legendPosition": "right",
            "isDonut": False,
            "labels": {
                "show": True,
                "values": True,
                "last_level": True,
                "truncate": 100
            }
        }
    }
    create_visualization("top-genres-visualization", "Top Genres", vis_state, "tracks")


def create_music_by_year_visualization() -> None:
    """Create Music by Year visualization."""
    vis_state = {
        "title": "Music by Year",
        "type": "histogram",
        "aggs": [
            {
                "id": "1",
                "enabled": True,
                "type": "count",
                "schema": "metric",
                "params": {}
            },
            {
                "id": "2",
                "enabled": True,
                "type": "histogram",
                "schema": "segment",
                "params": {
                    "field": "year",
                    "interval": 5,
                    "min_doc_count": 1,
                    "extended_bounds": {}
                }
            }
        ],
        "params": {
            "type": "histogram",
            "grid": {"categoryLines": False},
            "categoryAxes": [
                {
                    "id": "CategoryAxis-1",
                    "type": "category",
                    "position": "bottom",
                    "show": True,
                    "style": {},
                    "scale": {"type": "linear"},
                    "labels": {"show": True, "filter": True, "truncate": 100},
                    "title": {}
                }
            ],
            "valueAxes": [
                {
                    "id": "ValueAxis-1",
                    "name": "LeftAxis-1",
                    "type": "value",
                    "position": "left",
                    "show": True,
                    "style": {},
                    "scale": {"type": "linear", "mode": "normal"},
                    "labels": {"show": True, "rotate": 0, "filter": False, "truncate": 100},
                    "title": {"text": "Count"}
                }
            ],
            "seriesParams": [
                {
                    "show": True,
                    "type": "histogram",
                    "mode": "stacked",
                    "data": {"label": "Count", "id": "1"},
                    "valueAxis": "ValueAxis-1",
                    "drawLinesBetweenPoints": True,
                    "lineWidth": 2,
                    "showCircles": True
                }
            ],
            "addTooltip": True,
            "addLegend": True,
            "legendPosition": "right",
            "times": [],
            "addTimeMarker": False,
            "labels": {"show": False},
            "thresholdLine": {"show": False, "value": 10, "width": 1, "style": "full", "color": "#E7664C"}
        }
    }
    create_visualization("music-by-year", "Music by Year", vis_state, "tracks")


def create_bit_rate_visualization() -> None:
    """Create Bit Rate Distribution visualization."""
    vis_state = {
        "title": "Bit Rate Distribution",
        "type": "histogram",
        "aggs": [
            {
                "id": "1",
                "enabled": True,
                "type": "count",
                "schema": "metric",
                "params": {}
            },
            {
                "id": "2",
                "enabled": True,
                "type": "histogram",
                "schema": "segment",
                "params": {
                    "field": "bit_rate",
                    "interval": 50,
                    "min_doc_count": 1,
                    "extended_bounds": {}
                }
            }
        ],
        "params": {
            "type": "histogram",
            "grid": {"categoryLines": False},
            "categoryAxes": [
                {
                    "id": "CategoryAxis-1",
                    "type": "category",
                    "position": "bottom",
                    "show": True,
                    "style": {},
                    "scale": {"type": "linear"},
                    "labels": {"show": True, "filter": True, "truncate": 100},
                    "title": {}
                }
            ],
            "valueAxes": [
                {
                    "id": "ValueAxis-1",
                    "name": "LeftAxis-1",
                    "type": "value",
                    "position": "left",
                    "show": True,
                    "style": {},
                    "scale": {"type": "linear", "mode": "normal"},
                    "labels": {"show": True, "rotate": 0, "filter": False, "truncate": 100},
                    "title": {"text": "Count"}
                }
            ],
            "seriesParams": [
                {
                    "show": True,
                    "type": "histogram",
                    "mode": "stacked",
                    "data": {"label": "Count", "id": "1"},
                    "valueAxis": "ValueAxis-1",
                    "drawLinesBetweenPoints": True,
                    "lineWidth": 2,
                    "showCircles": True
                }
            ],
            "addTooltip": True,
            "addLegend": True,
            "legendPosition": "right",
            "times": [],
            "addTimeMarker": False,
            "labels": {"show": False},
            "thresholdLine": {"show": False, "value": 10, "width": 1, "style": "full", "color": "#E7664C"}
        }
    }
    create_visualization("bit-rate-distribution", "Bit Rate Distribution", vis_state, "tracks")


def create_ratings_distribution_visualization() -> None:
    """Create Ratings Distribution visualization."""
    vis_state = {
        "title": "Ratings Distribution",
        "type": "histogram",
        "aggs": [
            {
                "id": "1",
                "enabled": True,
                "type": "count",
                "schema": "metric",
                "params": {}
            },
            {
                "id": "2",
                "enabled": True,
                "type": "histogram",
                "schema": "segment",
                "params": {
                    "field": "rating",
                    "interval": 20,
                    "min_doc_count": 1,
                    "extended_bounds": {}
                }
            }
        ],
        "params": {
            "type": "histogram",
            "grid": {"categoryLines": False},
            "categoryAxes": [
                {
                    "id": "CategoryAxis-1",
                    "type": "category",
                    "position": "bottom",
                    "show": True,
                    "style": {},
                    "scale": {"type": "linear"},
                    "labels": {"show": True, "filter": True, "truncate": 100},
                    "title": {"text": "Rating"}
                }
            ],
            "valueAxes": [
                {
                    "id": "ValueAxis-1",
                    "name": "LeftAxis-1",
                    "type": "value",
                    "position": "left",
                    "show": True,
                    "style": {},
                    "scale": {"type": "linear", "mode": "normal"},
                    "labels": {"show": True, "rotate": 0, "filter": False, "truncate": 100},
                    "title": {"text": "Count"}
                }
            ],
            "seriesParams": [
                {
                    "show": True,
                    "type": "histogram",
                    "mode": "stacked",
                    "data": {"label": "Count", "id": "1"},
                    "valueAxis": "ValueAxis-1",
                    "drawLinesBetweenPoints": True,
                    "lineWidth": 2,
                    "showCircles": True
                }
            ],
            "addTooltip": True,
            "addLegend": True,
            "legendPosition": "right",
            "times": [],
            "addTimeMarker": False,
            "labels": {"show": False}
        }
    }
    create_visualization("ratings-distribution", "Ratings Distribution", vis_state, "tracks")


# Artist visualizations
def create_top_artists_by_plays() -> None:
    """Create Top Artists by Play Count visualization."""
    vis_state = {
        "title": "Top Artists by Play Count",
        "type": "horizontal_bar",
        "aggs": [
            {
                "id": "1",
                "enabled": True,
                "type": "sum",
                "schema": "metric",
                "params": {
                    "field": "total_play_count"
                }
            },
            {
                "id": "2",
                "enabled": True,
                "type": "terms",
                "schema": "segment",
                "params": {
                    "field": "name.keyword",
                    "orderBy": "1",
                    "order": "desc",
                    "size": 10,
                    "otherBucket": True,
                    "otherBucketLabel": "Other",
                    "missingBucket": False
                }
            }
        ],
        "params": {
            "type": "horizontal_bar",
            "addTooltip": True,
            "addLegend": True,
            "legendPosition": "right",
            "times": [],
            "addTimeMarker": False,
            "labels": {
                "show": True
            },
            "thresholdLine": {
                "show": False,
                "value": 10,
                "width": 1,
                "style": "full",
                "color": "#E7664C"
            }
        }
    }
    create_visualization("top-artists-by-plays", "Top Artists by Play Count", vis_state, "artists")


def create_artist_rating_visualization() -> None:
    """Create Artist Rating visualization."""
    vis_state = {
        "title": "Artist Ratings",
        "type": "horizontal_bar",
        "aggs": [
            {
                "id": "1",
                "enabled": True,
                "type": "avg",
                "schema": "metric",
                "params": {
                    "field": "avg_rating"
                }
            },
            {
                "id": "2",
                "enabled": True,
                "type": "terms",
                "schema": "segment",
                "params": {
                    "field": "name.keyword",
                    "orderBy": "1",
                    "order": "desc",
                    "size": 10,
                    "otherBucket": False,
                    "otherBucketLabel": "Other",
                    "missingBucket": False
                }
            }
        ],
        "params": {
            "type": "horizontal_bar",
            "addLegend": True,
            "addTooltip": True,
            "legendPosition": "right",
            "times": [],
            "addTimeMarker": False
        }
    }
    create_visualization("artist-ratings", "Top Artists by Rating", vis_state, "artists")


# Album visualizations
def create_top_albums_by_plays() -> None:
    """Create Top Albums by Play Count visualization."""
    vis_state = {
        "title": "Top Albums by Play Count",
        "type": "horizontal_bar",
        "aggs": [
            {
                "id": "1",
                "enabled": True,
                "type": "sum", 
                "schema": "metric",
                "params": {
                    "field": "total_play_count"
                }
            },
            {
                "id": "2",
                "enabled": True,
                "type": "terms",
                "schema": "segment",
                "params": {
                    "field": "name.keyword",
                    "orderBy": "1",
                    "order": "desc",
                    "size": 10,
                    "otherBucket": True,
                    "otherBucketLabel": "Other Albums",
                    "missingBucket": False
                }
            }
        ],
        "params": {
            "type": "horizontal_bar",
            "addTooltip": True,
            "addLegend": True,
            "legendPosition": "right",
            "times": [],
            "addTimeMarker": False
        }
    }
    create_visualization("top-albums-by-plays", "Top Albums by Play Count", vis_state, "albums")


def create_albums_by_year() -> None:
    """Create Albums by Year visualization."""
    vis_state = {
        "title": "Albums by Year",
        "type": "histogram",
        "aggs": [
            {
                "id": "1",
                "enabled": True,
                "type": "count",
                "schema": "metric",
                "params": {}
            },
            {
                "id": "2",
                "enabled": True,
                "type": "histogram",
                "schema": "segment",
                "params": {
                    "field": "year",
                    "interval": 5,
                    "min_doc_count": 1,
                    "extended_bounds": {}
                }
            }
        ],
        "params": {
            "type": "histogram",
            "grid": {"categoryLines": False},
            "categoryAxes": [
                {
                    "id": "CategoryAxis-1",
                    "type": "category",
                    "position": "bottom",
                    "show": True,
                    "style": {},
                    "scale": {"type": "linear"},
                    "labels": {"show": True, "filter": True, "truncate": 100},
                    "title": {"text": "Year"}
                }
            ],
            "valueAxes": [
                {
                    "id": "ValueAxis-1",
                    "name": "LeftAxis-1",
                    "type": "value",
                    "position": "left",
                    "show": True,
                    "style": {},
                    "scale": {"type": "linear", "mode": "normal"},
                    "labels": {"show": True, "rotate": 0, "filter": False, "truncate": 100},
                    "title": {"text": "Number of Albums"}
                }
            ],
            "seriesParams": [
                {
                    "show": True,
                    "type": "histogram",
                    "mode": "stacked",
                    "data": {"label": "Count", "id": "1"},
                    "valueAxis": "ValueAxis-1",
                    "drawLinesBetweenPoints": True,
                    "lineWidth": 2,
                    "showCircles": True
                }
            ],
            "addTooltip": True,
            "addLegend": False,
            "times": [],
            "addTimeMarker": False
        }
    }
    create_visualization("albums-by-year", "Albums by Year", vis_state, "albums")


# Genre visualizations
def create_genre_avg_rating() -> None:
    """Create Genre Average Rating visualization."""
    vis_state = {
        "title": "Genre Average Rating",
        "type": "horizontal_bar",
        "aggs": [
            {
                "id": "1",
                "enabled": True,
                "type": "avg",
                "schema": "metric",
                "params": {
                    "field": "avg_rating"
                }
            },
            {
                "id": "2",
                "enabled": True,
                "type": "terms",
                "schema": "segment",
                "params": {
                    "field": "name.keyword",
                    "orderBy": "1",
                    "order": "desc",
                    "size": 10,
                    "otherBucket": False,
                    "otherBucketLabel": "Other",
                    "missingBucket": False
                }
            }
        ],
        "params": {
            "type": "horizontal_bar",
            "addLegend": True,
            "addTooltip": True,
            "legendPosition": "right",
            "times": [],
            "addTimeMarker": False
        }
    }
    create_visualization("genre-avg-rating", "Genre Average Rating", vis_state, "genres")


def create_genre_play_time() -> None:
    """Create Genre Play Time visualization."""
    vis_state = {
        "title": "Genre Play Time (hours)",
        "type": "pie",
        "aggs": [
            {
                "id": "1",
                "enabled": True,
                "type": "sum",
                "schema": "metric",
                "params": {
                    "field": "total_time",
                    "customLabel": "Hours of Music"
                }
            },
            {
                "id": "2",
                "enabled": True,
                "type": "terms",
                "schema": "segment",
                "params": {
                    "field": "name.keyword",
                    "orderBy": "1",
                    "order": "desc",
                    "size": 10,
                    "otherBucket": True,
                    "otherBucketLabel": "Other Genres",
                    "missingBucket": False
                }
            }
        ],
        "params": {
            "type": "pie",
            "addTooltip": True,
            "addLegend": True,
            "legendPosition": "right",
            "isDonut": True,
            "labels": {
                "show": True,
                "values": True,
                "last_level": True,
                "truncate": 100
            },
            "metric": {
                "accessor": 0,
                "format": {
                    "id": "hours",
                    "params": {
                        "parsedUrl": {
                            "origin": "*",
                            "pathname": "*",
                            "basePath": ""
                        }
                    }
                },
                "type": "custom",
                "format": {"id": "hours", "params": {}}
            }
        }
    }
    create_visualization("genre-play-time", "Genre Play Time", vis_state, "genres")


def delete_all_saved_objects() -> None:
    """Delete all saved objects in Kibana - dashboard, visualizations, and index patterns."""
    logger.info("Deleting all existing Kibana saved objects...")
    headers = {
        "kbn-xsrf": "true",
    }
    
    # List of object types to delete
    object_types = ["dashboard", "visualization", "index-pattern"]
    
    # First, get all visualization IDs we want to delete
    visualizations = [
        # Track visualizations
        "top-artists-by-tracks",
        "top-genres-visualization",
        "music-by-year",
        "bit-rate-distribution",
        "ratings-distribution",
        # Artist visualizations
        "top-artists-by-plays",
        "artist-ratings",
        # Album visualizations
        "top-albums-by-plays",
        "albums-by-year",
        # Genre visualizations
        "genre-avg-rating",
        "genre-play-time"
    ]
    
    # Index patterns to delete
    index_patterns = ["tracks", "artists", "albums", "genres", "itunes"]
    
    # Dashboard IDs to delete
    dashboards = ["itunes-analysis"]
    
    # Try to delete dashboard first
    for dashboard_id in dashboards:
        try:
            url = f"{KIBANA_URL}/api/saved_objects/dashboard/{dashboard_id}"
            response = requests.delete(url, headers=headers)
            if response.status_code in [200, 204]:
                logger.info(f"Successfully deleted dashboard {dashboard_id}")
            elif response.status_code != 404:  # Ignore 404 (not found)
                logger.warning(f"Failed to delete dashboard {dashboard_id}: {response.status_code}")
        except Exception as e:
            logger.warning(f"Error deleting dashboard {dashboard_id}: {e}")
    
    # Then delete visualizations
    for vis_id in visualizations:
        try:
            url = f"{KIBANA_URL}/api/saved_objects/visualization/{vis_id}"
            response = requests.delete(url, headers=headers)
            if response.status_code in [200, 204]:
                logger.info(f"Successfully deleted visualization {vis_id}")
            elif response.status_code != 404:  # Ignore 404 (not found)
                logger.warning(f"Failed to delete visualization {vis_id}: {response.status_code}")
        except Exception as e:
            logger.warning(f"Error deleting visualization {vis_id}: {e}")
    
    # Finally delete index patterns
    for pattern_id in index_patterns:
        try:
            url = f"{KIBANA_URL}/api/saved_objects/index-pattern/{pattern_id}"
            response = requests.delete(url, headers=headers)
            if response.status_code in [200, 204]:
                logger.info(f"Successfully deleted index-pattern {pattern_id}")
            elif response.status_code != 404:  # Ignore 404 (not found)
                logger.warning(f"Failed to delete index-pattern {pattern_id}: {response.status_code}")
        except Exception as e:
            logger.warning(f"Error deleting index-pattern {pattern_id}: {e}")
    
    # Wait a moment to ensure objects are deleted
    time.sleep(1)

def setup_kibana(clean_first: bool = True) -> None:
    """Set up Kibana with index patterns, visualizations, and dashboards."""
    try:
        # Wait for Kibana to be available
        wait_for_kibana()
        
        # Delete all saved objects first if requested
        if clean_first:
            delete_all_saved_objects()
        
        # Create index patterns
        create_index_patterns()
        
        # Give Kibana a moment to process the index patterns
        time.sleep(2)
        
        # Create track visualizations
        create_top_artists_by_tracks()
        create_top_genres_visualization()
        create_music_by_year_visualization()
        create_bit_rate_visualization()
        create_ratings_distribution_visualization()
        
        # Create artist visualizations
        create_top_artists_by_plays()
        create_artist_rating_visualization()
        
        # Create album visualizations
        create_top_albums_by_plays()
        create_albums_by_year()
        
        # Create genre visualizations
        create_genre_avg_rating()
        create_genre_play_time()
        
        # Create dashboard with all visualizations
        visualization_info = [
            # Track section visualizations (top row)
            {"id": "top-artists-by-tracks", "section": "tracks"},
            {"id": "top-genres-visualization", "section": "tracks"},
            {"id": "ratings-distribution", "section": "tracks"},
            {"id": "bit-rate-distribution", "section": "tracks"},
            
            # Music timeline (full width)
            {"id": "music-by-year", "section": "timeline"},
            
            # Artist section
            {"id": "top-artists-by-plays", "section": "artists"},
            {"id": "artist-ratings", "section": "artists"},
            
            # Album section
            {"id": "top-albums-by-plays", "section": "albums"},
            {"id": "albums-by-year", "section": "albums"},
            
            # Genre section
            {"id": "genre-avg-rating", "section": "genres"},
            {"id": "genre-play-time", "section": "genres"}
        ]
        
        create_dashboard(visualization_info)
        
        logger.info("Kibana setup complete!")
        
    except Exception as e:
        logger.error(f"Error setting up Kibana: {e}")


if __name__ == "__main__":
    setup_kibana()