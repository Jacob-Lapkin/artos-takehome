#!/usr/bin/env python3
"""
Simple script to test Google Gemini embeddings with LangChain.
Run this to verify your API key and embedding setup are working.
"""

import os
import sys
from dotenv import load_dotenv

# Load .env file if it exists
load_dotenv()

def test_embeddings():
    # Check for API key
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("❌ ERROR: GOOGLE_API_KEY environment variable not set!")
        print("\nTo fix this:")
        print("1. Get your API key from: https://makersuite.google.com/app/apikey")
        print("2. Set it as an environment variable:")
        print("   export GOOGLE_API_KEY='your-key-here'")
        print("   OR create a .env file with: GOOGLE_API_KEY=your-key-here")
        sys.exit(1)
    
    print(f"✅ Found API key: {api_key[:10]}...")
    
    # Try to import and use the embeddings
    try:
        from langchain_google_genai import GoogleGenerativeAIEmbeddings
        print("✅ Successfully imported langchain_google_genai")
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("\nInstall with: pip install langchain-google-genai")
        sys.exit(1)
    
    # Test creating embeddings instance
    try:
        print("\n🔄 Creating embeddings instance...")
        embeddings = GoogleGenerativeAIEmbeddings(
            model="models/gemini-embedding-001",
            google_api_key=api_key
        )
        print("✅ Embeddings instance created")
    except Exception as e:
        print(f"❌ Failed to create embeddings: {e}")
        sys.exit(1)
    
    # Test single embedding
    try:
        print("\n🔄 Testing single text embedding...")
        test_text = "Hello, this is a test of the Google Gemini embeddings!"
        vector = embeddings.embed_query(test_text)
        print(f"✅ Single embedding successful!")
        print(f"   Vector length: {len(vector)}")
        print(f"   First 5 values: {vector[:5]}")
    except Exception as e:
        print(f"❌ Failed to embed single text: {e}")
        sys.exit(1)
    
    # Test batch embeddings
    try:
        print("\n🔄 Testing batch embeddings...")
        test_texts = [
            "This is the first document.",
            "Here's another piece of text.",
            "And a third one for good measure."
        ]
        vectors = embeddings.embed_documents(test_texts)
        print(f"✅ Batch embedding successful!")
        print(f"   Number of vectors: {len(vectors)}")
        print(f"   Each vector length: {len(vectors[0])}")
    except Exception as e:
        print(f"❌ Failed to embed batch: {e}")
        sys.exit(1)
    
    print("\n🎉 All tests passed! Your embeddings setup is working correctly.")
    print(f"\nConfiguration:")
    print(f"  Model: models/gemini-embedding-001")
    print(f"  Vector dimension: {len(vector)}")
    print(f"  API Key: {api_key[:10]}...")

if __name__ == "__main__":
    test_embeddings()