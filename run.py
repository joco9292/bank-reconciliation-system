#!/usr/bin/env python3
"""
Simple launcher script for the Bank Reconciliation System
"""

import subprocess
import sys
import os

def main():
    """Launch the Streamlit application"""
    try:
        # Check if streamlit is installed
        import streamlit
        print("🚀 Starting Bank Reconciliation System...")
        print("📱 Open your browser to http://localhost:8501")
        print("⏹️  Press Ctrl+C to stop the application")
        print("-" * 50)
        
        # Run the streamlit app
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", "app.py",
            "--server.headless", "false",
            "--server.runOnSave", "true"
        ])
        
    except ImportError:
        print("❌ Streamlit is not installed!")
        print("📦 Please install dependencies first:")
        print("   pip install -r requirements.txt")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n👋 Application stopped by user")
    except Exception as e:
        print(f"❌ Error starting application: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
