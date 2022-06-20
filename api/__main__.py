from api import *

import uvicorn as uvicorn

from mongoengine import *
import os
import dotenv
from starlette.responses import RedirectResponse


from .routers import uptime

dotenv.load_dotenv()
connect(host=os.getenv("MONGO"), db="delegationdao")

app.include_router(uptime.router)





@app.get("/", include_in_schema=False)
def redirect():
    return RedirectResponse(url='/docs')

if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=5000, log_level="info")