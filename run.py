import os
import uvicorn
from dotenv import load_dotenv

load_dotenv()

if __name__ == "__main__":
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", 8000))
    
    print("=" * 60)
    print("  🚀 Starting DreemFolio AI (ATS Resume & Cover Letter SaaS)")
    print(f"  🌐 Application URL: http://{host}:{port}")
    print("  📄 100% Single-Column ATS PDF Engine Ready")
    print("  🤖 Gemini Flash Structured Engine Active")
    print("=" * 60)
    
    uvicorn.run("app.main:app", host=host, port=port, reload=True)
