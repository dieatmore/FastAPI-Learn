from fastapi import FastAPI


app = FastAPI(title="FastAPI Learn")


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "Hello, FastAPI!"}