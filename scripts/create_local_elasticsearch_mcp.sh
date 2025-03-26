#!/bin/bash
set -e

# This script creates a local Elasticsearch MCP server from 

wget https://github.com/cr7258/elasticsearch-mcp-server/archive/refs/tags/v1.0.0.tar.gz
tar -xzf v1.0.0.tar.gz
rm v1.0.0.tar.gz

# set path variable
ELASTIC_MCP_PATH=$(pwd)/elasticsearch-mcp-server-1.0.0/src/elasticsearch_mcp_server

# set uvx path using which
UVX_PATH=$(which uvx)

# get elastic password from .env
PASSWORD=$(cat .env | grep ELASTIC_PASSWORD | cut -d '=' -f 2)

output_mcp_config_json=$(cat <<EOF
{
  "mcpServers": {
    "elasticsearch-local": {
      "command": "$UVX_PATH",
      "args": [
        "--directory",
        "$ELASTIC_MCP_PATH",
        "elasticsearch-mcp-server"
      ],
      "env": {
        "ELASTIC_HOST": "http://localhost:9200",
        "ELASTIC_USERNAME": "elastic",
        "ELASTIC_PASSWORD": "$PASSWORD"
      }
    }
  }
}
EOF)

echo "To register this, merge the following json into the claude_desktop_config.json file and restart the claude desktop app\n"
echo "$output_mcp_config_json"
echo "\n$output_mcp_config_json" > mcp.json
echo "\nA copy of the file has been saved to mcp.json in this directory"
echo "\nOnce installed, run \`claude mcp add-from-claude-desktop -s local|user|global\` to register the MCP"
echo "\n"
