"""Run the public web service behind the hosting provider's HTTPS proxy."""

import os

from waitress import serve

from server import application


if __name__ == "__main__":
    serve(application, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)),
          threads=8, max_request_body_size=4096)
