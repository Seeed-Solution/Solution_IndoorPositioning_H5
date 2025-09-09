from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
import httpx

app = FastAPI()

BACKEND_URL = "http://127.0.0.1:8022"  # 你真正的后端服务地址

@app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy(path: str, request: Request):
    print("aaa")
    async with httpx.AsyncClient() as client:
        response = await client.request(
            request.method,
            f"{BACKEND_URL}/api/{path}",
            headers={k: v for k, v in request.headers.items() if k.lower() != "host"},
            content=await request.body()
        )
    return Response(content=response.content, status_code=response.status_code, headers=dict(response.headers))


app.mount("/", StaticFiles(directory="dist", html=True), name="static")
