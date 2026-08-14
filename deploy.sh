#!/bin/bash
# deploy.sh — Simple deployment script for Harvest Hero

set -e

echo "🌾 Harvest Hero - Deployment Script"
echo "===================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running on destination device
if [ "$1" == "client" ]; then
    echo -e "${BLUE}Setting up Harvest Hero on client device...${NC}"
    
    # Create application directory
    APP_DIR="${HOME}/HarvestHero"
    mkdir -p "$APP_DIR"
    cd "$APP_DIR"
    
    # Clone or pull from GitHub
    if [ -d ".git" ]; then
        echo -e "${YELLOW}Updating existing installation...${NC}"
        git pull origin main
    else
        echo -e "${YELLOW}Cloning from GitHub...${NC}"
        git clone https://github.com/oclemons/HarvestHero.git .
    fi
    
    # Install dependencies
    echo -e "${YELLOW}Installing dependencies...${NC}"
    pip install -r requirements.txt
    
    # Create data directory if needed
    mkdir -p data
    
    echo -e "${GREEN}✓ Installation complete!${NC}"
    echo ""
    echo "To start the application, run:"
    echo "  cd $APP_DIR"
    echo "  python main.py"
    echo ""
    
elif [ "$1" == "dev" ]; then
    echo -e "${BLUE}Building development package...${NC}"
    
    # Ensure everything is committed
    if [ -n "$(git status --porcelain)" ]; then
        echo -e "${YELLOW}Warning: Uncommitted changes detected${NC}"
        echo "Commit changes before building for production"
        exit 1
    fi
    
    # Update VERSION.json
    echo -e "${YELLOW}Updating version information...${NC}"
    CURRENT_DATE=$(date -u +"%Y-%m-%dT%H:%M:%S")
    
    # Create a simple version update (you may want to customize this)
    echo "Current version in VERSION.json:"
    cat VERSION.json | grep version
    
    echo -e "${GREEN}✓ Development package ready${NC}"
    echo ""
    echo "To deploy:"
    echo "  1. Commit all changes: git add -A && git commit -m 'message'"
    echo "  2. Push to GitHub: git push origin main"
    echo "  3. Create a release on GitHub"
    echo "  4. Run on client: ./deploy.sh client"
    echo ""
    
elif [ "$1" == "release" ]; then
    echo -e "${BLUE}Creating release package...${NC}"
    
    # Check for uncommitted changes
    if [ -n "$(git status --porcelain)" ]; then
        echo -e "${YELLOW}Error: Uncommitted changes detected${NC}"
        echo "Please commit all changes first"
        exit 1
    fi
    
    # Get version from VERSION.json
    VERSION=$(grep '"version"' VERSION.json | head -1 | sed 's/.*"version": "\([^"]*\)".*/\1/')
    
    echo -e "${YELLOW}Creating release for version $VERSION...${NC}"
    
    # Create zip file
    ZIP_FILE="HarvestHero-v${VERSION}.zip"
    zip -r "$ZIP_FILE" . \
        -x "*.git*" \
        "*.pyc" \
        "__pycache__/*" \
        "*.egg-info/*" \
        "build/*" \
        "dist/*" \
        "data/inventory.db" \
        ".DS_Store" \
        "*.env"
    
    echo -e "${GREEN}✓ Release package created: $ZIP_FILE${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Go to GitHub: https://github.com/oclemons/HarvestHero/releases"
    echo "  2. Create new release for tag v${VERSION}"
    echo "  3. Upload $ZIP_FILE as asset"
    echo "  4. Publish release"
    echo ""
    
else
    echo "Usage: ./deploy.sh [command]"
    echo ""
    echo "Commands:"
    echo "  client   - Deploy to client device (downloads from GitHub)"
    echo "  dev      - Prepare development build"
    echo "  release  - Create release package for GitHub"
    echo ""
    echo "Examples:"
    echo "  ./deploy.sh client    # Install on client device"
    echo "  ./deploy.sh dev       # Prepare for development"
    echo "  ./deploy.sh release   # Create release package"
    echo ""
fi
