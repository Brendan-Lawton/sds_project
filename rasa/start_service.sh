#!/bin/bash

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

clear

echo ""
echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║${NC}              ${BLUE}RASA SPEECH SERVICE LAUNCHER${NC}                  ${CYAN}║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${YELLOW}Starting services...${NC}"
echo ""

# Start all services in parallel
echo -e "  ${GREEN}[1/4]${NC} Starting Rasa API Server (port 5005)..."
rasa run --enable-api --connector rest --cors "*" --port 5005 > /dev/null 2>&1 &

echo -e "  ${GREEN}[2/4]${NC} Starting Rasa Action Server..."
rasa run actions > /dev/null 2>&1 &

echo -e "  ${GREEN}[3/4]${NC} Starting ASR Server..."
python asr_server.py > /dev/null 2>&1 &

echo -e "  ${GREEN}[4/4]${NC} Starting HTTP Server (port 8080)..."
python -m http.server 8080 > /dev/null 2>&1 &

# Give services a moment to start
sleep 2

echo ""
echo -e "${CYAN}════════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${GREEN}  All services started successfully!${NC}"
echo ""
echo -e "${CYAN}════════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "  ${YELLOW}Open your browser at:${NC}"
echo ""
echo -e "       ${BLUE}http://localhost:8080/web/${NC}"
echo ""
echo -e "${CYAN}════════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "  ${YELLOW}Press Ctrl+C to stop all services${NC}"
echo ""

# Wait for all background processes
wait
