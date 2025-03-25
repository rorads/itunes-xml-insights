# iTunes XML Insights

Analyze your iTunes XML library data using Elasticsearch and Kibana to visualize your music listening habits.

## Features

- Parse iTunes XML library export
- Ingest music library data into Elasticsearch
- Visualize listening habits with Kibana dashboards
- All containerized with Docker, no local installs needed

## Prerequisites

- Docker and Docker Compose installed
- iTunes XML library export file (typically named "iTunes Music Library.xml")
- File needed in root directory:
  ```
  # iTunes Music Library XML file - found in /Users/username/Music/iTunes/ 
  # for macOS, not sure about Windows
  iTunes Music Library.xml
  ```

## Setup

1. Make sure Docker and Docker Compose are installed on your system

2. Place your iTunes XML library file in the project root directory (named "iTunes Music Library.xml")

3. Run the setup script:
   ```
   ./setup.sh
   ```
   
   This script will:
   - Start Elasticsearch and Kibana containers
   - Build a Python container with dependencies installed using `uv` (faster than pip)
   - Import your iTunes data into Elasticsearch

4. Open Kibana in your browser:
   ```
   http://localhost:5601
   ```

5. In Kibana, create an index pattern for "itunes" and start exploring your data

## Kibana Dashboard

The system automatically sets up a Kibana dashboard for you with the following visualizations:

1. Top Artists - Shows your most listened to artists
2. Top Genres - Displays distribution of music by genre
3. Music by Year - Timeline histogram showing when your music was released
4. Bit Rate Distribution - Analysis of audio quality across your library

Access your dashboard directly at:
```
http://localhost:5601/app/dashboards#/view/itunes-analysis
```

No manual setup required!

## Data Analysis Ideas

- Most played artists/albums
- Listening trends over time
- Skip rate for different genres
- Audio quality analysis (by bit rate)
- Year distribution of your music collection
- Average song length by genre or artist
- Advanced analysis using LLMs or vector embeddings

## Technical Details

- Uses `uv` for fast Python dependency management
- Docker containers for complete isolation and reproducibility
- Elasticsearch for efficient indexing and querying of music metadata
- Kibana for building interactive visualizations and dashboards

## Future Plans

The plan is to use some LLMs or vector embeddings to create more interesting analyses beyond basic statistics.

Claude is going to help.