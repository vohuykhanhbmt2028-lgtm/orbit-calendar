#!/bin/bash

echo "Building Weekly Scheduler App..."

# Activate virtual environment
source venv/bin/activate

# Clean previous builds
rm -rf build dist *.spec

# Build the app
pyinstaller --name="Weekly Scheduler" \
           --windowed \
           --onedir \
           --add-data=".env:." \
           --hidden-import=anthropic \
           --hidden-import=dotenv \
           scheduler_app.py

# Check if build succeeded
if [ -d "dist/Weekly Scheduler.app" ]; then
    echo "✅ App built successfully!"
    echo ""
    echo "📁 Your app is at: dist/Weekly Scheduler.app"
    echo ""
    echo "To install:"
    echo "  cp -r dist/Weekly\\ Scheduler.app /Applications/"
    echo ""
    echo "Or run it now:"
    echo "  open dist/Weekly\\ Scheduler.app"
else
    echo "❌ Build failed. Check the error messages above."
fi