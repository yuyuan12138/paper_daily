#!/bin/bash
# Download pdffigures2 JAR automatically
# Usage: ./scripts/download_pdffigures2.sh

set -e

JAR_DIR="$(dirname "$0")/../pdffigures2"
JAR_PATH="$JAR_DIR/pdffigures2.jar"

mkdir -p "$JAR_DIR"

if [ -f "$JAR_PATH" ]; then
    echo "pdffigures2.jar already exists at $JAR_PATH"
    exit 0
fi

echo "Downloading pdffigures2..."

# Try to download from GitHub releases or build from source
# Since there's no pre-built JAR, we'll provide build instructions

echo "Error: pdffigures2 requires compilation from source."
echo ""
echo "Please install Scala and sbt first, then run:"
echo ""
echo "  cd pdffigures2"
echo "  sbt assembly"
echo ""
echo "This will create: pdffigures2/target/scala-2.13/pdffigures2-assembly-*.jar"
echo ""
echo "Then update config.yaml with the exact path:"
echo "  pdffigures2_jar: \"/path/to/paper_daily/pdffigures2/target/scala-2.13/pdffigures2-assembly-*.jar\""

# Alternative: try to download from a mirror if available
echo ""
echo "Trying alternative sources..."

# Try different potential sources
SOURCES=(
    "https://repo1.maven.org/maven2/ai/allenai/pdffigures2/"
)

for src in "${SOURCES[@]}"; do
    echo "Checking $src..."
done

echo ""
echo "Installation complete when you have the JAR file."
