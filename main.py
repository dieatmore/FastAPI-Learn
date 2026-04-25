from fastapi import FastAPI


app = FastAPI()

# 路由分发 include_router
# app.include_router(shop, prefix="/shop", tags=["购物中心接口"])

@app.get("/")
async def read_root():
    return {"message": "Hello, FastAPI!"}


@app.get("/test", tags=["test"], description="This is a test 接口", summary="测试接口")
async def test():
    return {"message": "一个测试接口"}