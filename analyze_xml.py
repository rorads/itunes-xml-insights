#!/usr/bin/env python3
"""
Recursively analyze iTunes XML file structure with minimal assumptions. This can be run locally via `uvx python analyze_xml.py`
"""

import plistlib
import json
from collections import Counter, defaultdict
from typing import Dict, Any, List, Set, DefaultDict
import sys


def analyze_data_structure(data: Any, path: str = "", depth: int = 0, max_depth: int = None, 
                          max_examples: int = 5) -> Dict[str, Any]:
    """
    Recursively analyze a data structure with minimal assumptions.
    
    Args:
        data: The data to analyze
        path: Current path in the data structure
        depth: Current recursion depth
        max_depth: Maximum recursion depth (None for unlimited)
        max_examples: Maximum number of example values to collect
        
    Returns:
        Dictionary with analysis results
    """
    # Check recursion depth limit
    if max_depth is not None and depth > max_depth:
        return {"type": "max_depth_exceeded"}
    
    # Analyze based on data type
    data_type = type(data).__name__
    result = {"type": data_type}
    
    if data_type == "dict":
        # For dictionaries, analyze keys and their values
        result["count"] = len(data)
        result["keys"] = {}
        
        # Track key frequencies
        key_counter = Counter(data.keys())
        result["key_frequencies"] = dict(key_counter.most_common())
        
        # Sample some keys for deeper analysis
        sample_keys = list(key_counter.keys())
        if len(sample_keys) > max_examples:
            # If too many keys, take most common ones
            sample_keys = [k for k, _ in key_counter.most_common(max_examples)]
        
        for key in sample_keys:
            new_path = f"{path}.{key}" if path else key
            result["keys"][key] = analyze_data_structure(
                data[key], new_path, depth + 1, max_depth, max_examples
            )
            
    elif data_type == "list" or data_type == "tuple":
        # For lists/tuples, analyze length and sample some elements
        result["count"] = len(data)
        
        # Sample some values
        sample_size = min(max_examples, len(data))
        samples = []
        
        if sample_size > 0:
            # Take evenly distributed samples
            indices = [int(i * len(data) / sample_size) for i in range(sample_size)]
            for i, idx in enumerate(indices):
                samples.append(
                    analyze_data_structure(
                        data[idx], f"{path}[{idx}]", depth + 1, max_depth, max_examples
                    )
                )
        
        result["samples"] = samples
        
    elif data_type in ("str", "int", "float", "bool", "date"):
        # For basic types, just store the value
        result["value"] = data
        
    elif data_type == "bytes":
        # For binary data, just note the length
        result["length"] = len(data)
        
    return result


def analyze_itunes_xml(file_path: str, max_depth: int = 5, max_examples: int = 5) -> Dict[str, Any]:
    """
    Analyze iTunes XML file structure recursively.
    
    Args:
        file_path: Path to the iTunes XML file
        max_depth: Maximum recursion depth
        max_examples: Maximum number of example values to collect
        
    Returns:
        Dictionary with analysis results
    """
    print(f"Loading iTunes library from {file_path}...", file=sys.stderr)
    
    with open(file_path, 'rb') as fp:
        library = plistlib.load(fp)
    
    # Top-level analysis
    print(f"Analyzing iTunes XML structure...", file=sys.stderr)
    result = analyze_data_structure(library, "", 0, max_depth, max_examples)
    
    return result


def analyze_track_fields(library: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze available fields in tracks.
    
    Args:
        library: The loaded iTunes library
        
    Returns:
        Dictionary with field analysis
    """
    tracks = library.get("Tracks", {})
    print(f"Analyzing fields across {len(tracks)} tracks...", file=sys.stderr)
    
    # Collect all unique fields
    all_fields: Set[str] = set()
    field_counter: Counter = Counter()
    field_types: DefaultDict[str, Set[str]] = defaultdict(set)
    value_examples: DefaultDict[str, List[Any]] = defaultdict(list)
    
    # Process each track
    for track_id, track_data in tracks.items():
        # Count each field
        for field, value in track_data.items():
            all_fields.add(field)
            field_counter[field] += 1
            field_types[field].add(type(value).__name__)
            
            # Store example values (up to 3 per field)
            if len(value_examples[field]) < 3:
                if isinstance(value, bytes):
                    # Don't store binary data
                    value = f"<binary data of length {len(value)}>"
                elif isinstance(value, (dict, list)):
                    # For complex objects, just note the type and size
                    value = f"<{type(value).__name__} of size {len(value)}>"
                    
                if value not in value_examples[field]:
                    value_examples[field].append(value)
    
    # Convert to serializable format
    result = {
        "total_tracks": len(tracks),
        "total_fields": len(all_fields),
        "fields": {}
    }
    
    for field in sorted(all_fields):
        result["fields"][field] = {
            "count": field_counter[field],
            "percentage": field_counter[field] / len(tracks) * 100,
            "types": list(field_types[field]),
            "examples": value_examples[field]
        }
    
    return result


if __name__ == "__main__":
    file_path = "iTunes Music Library.xml"
    
    # Load the library
    with open(file_path, 'rb') as fp:
        library = plistlib.load(fp)
    
    # Analyze structure
    structure = {
        "top_level_keys": list(library.keys()),
        "tracks_count": len(library.get("Tracks", {})),
        "playlists_count": len(library.get("Playlists", [])),
    }
    
    # Analyze track fields
    fields_analysis = analyze_track_fields(library)
    
    # Combine results
    result = {
        "structure": structure,
        "fields_analysis": fields_analysis
    }
    
    # Output as JSON
    print(json.dumps(result, indent=2, default=str))