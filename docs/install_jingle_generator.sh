#!/bin/bash
# 🎤 Jingle Generator - Quick Install Script
# Run this script to install all required dependencies

set -e  # Exit on error

echo "🎵 Music Bingo - Jingle Generator Installation"
echo "================================================"
echo ""

# Check if we're in the right directory
if [ ! -d "backend" ]; then
    echo "❌ Error: Please run this script from the Music_Bingo root directory"
    exit 1
fi

# 1. Install Python dependencies
echo "📦 Installing Python dependencies..."
cd backend
pip install -r requirements.txt
cd ..
echo "✅ Python dependencies installed"
echo ""

# 2. Check FFmpeg installation
echo "🔍 Checking FFmpeg installation..."
if command -v ffmpeg &> /dev/null; then
    echo "✅ FFmpeg is already installed:"
    ffmpeg -version | head -n 1
else
    echo "⚠️  FFmpeg not found. Installing..."
    
    # Detect OS and install
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        echo "📱 Detected macOS - Installing via Homebrew..."
        if command -v brew &> /dev/null; then
            brew install ffmpeg
        else
            echo "❌ Homebrew not found. Please install from: https://brew.sh"
            echo "   Then run: brew install ffmpeg"
            exit 1
        fi
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        echo "🐧 Detected Linux - Installing via apt..."
        sudo apt-get update
        sudo apt-get install -y ffmpeg
    else
        echo "❌ Unsupported OS: $OSTYPE"
        echo "   Please install FFmpeg manually from: https://ffmpeg.org/download.html"
        exit 1
    fi
    
    echo "✅ FFmpeg installed successfully"
fi
echo ""

# 3. Create jingles directory
echo "📁 Creating jingles directory..."
mkdir -p data/jingles
echo "✅ Directory created: data/jingles"
echo ""

# 4. Check environment variables
echo "🔐 Checking environment configuration..."
if [ -f ".env" ]; then
    if grep -q "ELEVENLABS_API_KEY" .env; then
        echo "✅ ElevenLabs API key found in .env"
    else
        echo "⚠️  Warning: ELEVENLABS_API_KEY not found in .env"
        echo "   Please add your API key to continue"
    fi
else
    echo "⚠️  Warning: .env file not found"
    echo "   Please create .env file with your ELEVENLABS_API_KEY"
fi
echo ""

# 5. Test installation
echo "🧪 Testing installation..."
python3 << 'EOF'
try:
    from pydub import AudioSegment
    from pydub.generators import Sine
    import io
    print("✅ pydub is working correctly")
    
    # Quick test of audio generation
    tone = Sine(440).to_audio_segment(duration=1000)
    output = io.BytesIO()
    tone.export(output, format="mp3")
    print("✅ Audio export is working")
    
except ImportError as e:
    print(f"❌ Error: {e}")
    exit(1)
except Exception as e:
    print(f"❌ Error during test: {e}")
    exit(1)
EOF

if [ $? -eq 0 ]; then
    echo ""
    echo "================================================"
    echo "✨ Installation Complete!"
    echo "================================================"
    echo ""
    echo "Next steps:"
    echo "1. Make sure your .env file has ELEVENLABS_API_KEY"
    echo "2. Start the backend: cd backend && python manage.py runserver 0.0.0.0:8080"
    echo "3. Open http://localhost:8080/game.html"
    echo "4. Click 'Create Jingle' to test the feature"
    echo ""
    echo "📖 Full documentation: docs/JINGLE_GENERATOR_GUIDE.md"
    echo ""
else
    echo ""
    echo "❌ Installation test failed. Please check the errors above."
    exit 1
fi
