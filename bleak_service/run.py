import uvicorn

# If run.py is inside bleak_service, and main.py is also in bleak_service,
# we can use a relative import for the app from .main
from .main import app 

if __name__ == "__main__":
    # You can configure host, port, log_level etc. here
    # These will be the defaults when running the compiled executable
    uvicorn.run(app, host="0.0.0.0", port=8081, log_level="info") 