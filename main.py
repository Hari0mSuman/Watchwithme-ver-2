import os
from app import app
import routes  # noqa: F401

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # use PORT from Render environment
    app.run(host="0.0.0.0", port=port, debug=True)
