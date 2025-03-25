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


def create_index_pattern() -> None:
    """Create Kibana index pattern for iTunes data."""
    logger.info("Creating iTunes index pattern...")
    headers = {
        "kbn-xsrf": "true",
        "Content-Type": "application/json"
    }
    
    # Simple index pattern with date field
    data = {
        "attributes": {
            "title": "itunes",
            "timeFieldName": "date_added"
        }
    }
    
    response = requests.post(
        f"{KIBANA_URL}/api/saved_objects/index-pattern/itunes",
        headers=headers,
        json=data
    )
    
    if response.status_code in [200, 201]:
        logger.info("Successfully created index pattern")
    else:
        logger.warning(f"Failed to create index pattern: {response.status_code} {response.text}")


def create_visualization(vis_id: str, title: str, vis_state: Dict[str, Any]) -> None:
    """Create a Kibana visualization."""
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
                "id": "itunes"
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


def create_dashboard(visualizations: List[str]) -> None:
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
    
    # Set up panel positions
    positions = [
        {"x": 0, "y": 0, "w": 24, "h": 15},   # Top left - top artists
        {"x": 24, "y": 0, "w": 24, "h": 15},  # Top right - top genres
        {"x": 0, "y": 15, "w": 48, "h": 15},  # Middle - music by year
        {"x": 0, "y": 30, "w": 48, "h": 15}   # Bottom - bit rate
    ]
    
    # Create panels with proper references
    for i, vis_id in enumerate(visualizations):
        panel_id = f"panel_{i+1}"
        
        # Create panel
        panel = {
            "version": "8.5.0",
            "type": "visualization",
            "gridData": positions[i],
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
    
    # Add index pattern reference
    references.append({
        "id": "itunes",
        "name": "kibanaSavedObjectMeta.searchSourceJSON.index",
        "type": "index-pattern"
    })
    
    # Create the dashboard with all references
    # Create a 100-year default time range
    current_time = time.time()
    from_time = current_time - (100 * 365 * 24 * 60 * 60)  # 100 years in seconds
    
    # Format times for Kibana
    from_time_str = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime(from_time))
    to_time_str = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime(current_time))
    
    data = {
        "attributes": {
            "title": "iTunes Music Analysis",
            "hits": 0,
            "description": "Analysis of iTunes Music Library",
            "panelsJSON": json.dumps(panels),
            "optionsJSON": json.dumps({"hidePanelTitles": False, "useMargins": True}),
            "version": 1,
            # Use explicit time range
            "timeRestore": True,
            "timeFrom": "now-100y",  # Use a relative time - 100 years ago
            "timeTo": "now",         # Current time
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


def create_top_artists_visualization() -> None:
    """Create Top Artists visualization."""
    vis_state = {
        "title": "Top Artists",
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
    create_visualization("top-artists", "Top Artists", vis_state)


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
    create_visualization("top-genres", "Top Genres", vis_state)


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
    create_visualization("music-by-year", "Music by Year", vis_state)


def create_bit_rate_visualization() -> None:
    """Create Bit Rate visualization."""
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
    create_visualization("bit-rate-distribution", "Bit Rate Distribution", vis_state)


def delete_all_saved_objects() -> None:
    """Delete all saved objects in Kibana - dashboard, visualizations, and index patterns."""
    logger.info("Deleting all existing Kibana saved objects...")
    headers = {
        "kbn-xsrf": "true",
    }
    
    # List of object types to delete
    object_types = ["dashboard", "visualization", "index-pattern"]
    object_ids = {
        "dashboard": ["itunes-analysis"],
        "visualization": ["top-artists", "top-genres", "music-by-year", "bit-rate-distribution"],
        "index-pattern": ["itunes"]
    }
    
    # Delete each object
    for obj_type in object_types:
        for obj_id in object_ids[obj_type]:
            try:
                url = f"{KIBANA_URL}/api/saved_objects/{obj_type}/{obj_id}"
                response = requests.delete(url, headers=headers)
                if response.status_code in [200, 204]:
                    logger.info(f"Successfully deleted {obj_type} {obj_id}")
                elif response.status_code != 404:  # Ignore 404 (not found)
                    logger.warning(f"Failed to delete {obj_type} {obj_id}: {response.status_code}")
            except Exception as e:
                logger.warning(f"Error deleting {obj_type} {obj_id}: {e}")
    
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
        
        # Create index pattern
        create_index_pattern()
        
        # Give Kibana a moment to process the index pattern
        time.sleep(2)
        
        # Create visualizations
        create_top_artists_visualization()
        create_top_genres_visualization()
        create_music_by_year_visualization()
        create_bit_rate_visualization()
        
        # Create dashboard
        create_dashboard([
            "top-artists",
            "top-genres",
            "music-by-year",
            "bit-rate-distribution"
        ])
        
        logger.info("Kibana setup complete!")
        
    except Exception as e:
        logger.error(f"Error setting up Kibana: {e}")


if __name__ == "__main__":
    setup_kibana()