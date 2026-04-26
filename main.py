from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import Body, Depends, FastAPI, HTTPException
from fastapi import Path, Query
from pydantic import BaseModel, Field
from sqlalchemy import DateTime, Float, String, func, select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


# 路由分发 include_router
# app.include_router(shop, prefix="/shop", tags=["购物中心接口"])

# 1. 创建异步引擎
ASYNC_DATABASE_URL = (
    "mysql+aiomysql://root:wsd03160226@localhost:13307/fastapi_learn?charset=utf8mb4"
)
async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=True,  # 可选，输出日志
    pool_size=10,  # 设置连接池活跃的连接数
    max_overflow=20,  # 允许额外的连接数
)


# 2. 定义模型类
# 基类：创建时间、更新时间；书籍表：id、书名、作者、价格、出版社
class Base(DeclarativeBase):
    create_time: Mapped[datetime] = mapped_column(
        DateTime, insert_default=func.now(), default=func.now, comment="创建时间"
    )
    update_time: Mapped[datetime] = mapped_column(
        DateTime, insert_default=func.now(), default=func.now, comment="修改时间"
    )


class Book(Base):
    __tablename__ = "book"

    id: Mapped[int] = mapped_column(primary_key=True, comment="书籍ID")
    bookname: Mapped[str] = mapped_column(String(255), comment="书名")
    author: Mapped[str] = mapped_column(String(255), comment="作者")
    price: Mapped[float] = mapped_column(Float, comment="价格")
    publisher: Mapped[str] = mapped_column(String(255), comment="出版社")


# 3. 启动
async def create_tables():
    # 获取异步引擎，创建事务 -> 建表
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)  # Base 模型类的元数据创建


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()  # 启动阶段
    yield
    # 这里是关闭阶段（可选）


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def read_root():
    return {"message": "Hello, FastAPI!"}


# 需求：查询图书 -> 依赖注入：创建依赖项获取数据库会话 + Depends 注入路由处理函数
AsyncSessionLocal = async_sessionmaker[AsyncSession](
    bind=async_engine,  # 绑定数据库引擎
    class_=AsyncSession,  # 指定会话类
    expire_on_commit=False,  # 提交后会话不过期，不会重新查询数据库
)


async def get_database():
    async with AsyncSessionLocal() as session:
        try:
            yield session  # 返回数据库会话给路由处理函数
            await session.commit()
        except Exception:
            await session.rollback()  # 异常回滚
            raise
        finally:
            await session.close()  # 关闭会话


# 查询
@app.get("/book/books")
async def get_book_list(db: AsyncSession = Depends(get_database)):

    # scalars 查询
    result = await db.execute(select(Book))  # 查询 -> 返回一个 ORM 对象
    book = result.scalars().all()  # 获取所有
    # book = result.scalars().first() # 获取第一条

    # 主键查询
    # book = await db.get(Book, 2)
    return book


@app.get("/book/{book_id}")
async def get_book_list(book_id: int, db: AsyncSession = Depends(get_database)):
    # result = await db.execute(select(Book).where(Book.id == book_id))
    # book = result.scalar_one_or_none()

    # 主键查询
    book = await db.get(Book, book_id)
    return book


class BookBase(BaseModel):
    bookname: str
    author: str
    price: float
    publisher: str


# 新增
@app.post("/book/add_book")
async def add_book(book: BookBase, db: AsyncSession = Depends(get_database)):
    # ORM 对象 -> add -> commit
    book_obj = Book(**book.__dict__)
    db.add(book_obj)
    await db.commit()
    await db.refresh(book_obj)
    return book_obj


# 更新
@app.put("/book/update_book/{book_id}")
async def update_book(
    book_id: int, data: BookBase, db: AsyncSession = Depends(get_database)
):
    db_book = await db.get(Book, book_id)
    if db_book is None:
        raise HTTPException(status_code=404, detail="查无此书")

    # update
    db_book.bookname = data.bookname
    db_book.author = data.author
    db_book.price = data.price
    db_book.publisher = data.publisher

    await db.commit()
    await db.refresh(db_book)
    return db_book


# 删除
@app.delete("/book/delete_book/{book_id}")
async def delete_book(book_id: int, db: AsyncSession = Depends(get_database)):
    db_book = await db.get(Book, book_id)

    if db_book is None:
        raise HTTPException(status_code=404, detail="查无此书")

    await db.delete(db_book)
    await db.commit()
    return {"message": "删除图书成功！"}


# # 中间件
# @app.middleware("http")
# async def middleware(request, call_next):
#     print("中间件1 开始请求")
#     response = await call_next(request)
#     print("中间件1 结束请求")
#     return response


# @app.middleware("http")
# async def middleware2(request, call_next):
#     print("中间件2 开始请求")
#     response = await call_next(request)
#     print("中间件2 结束请求")
#     return response


# @app.get("/")
# async def read_root():
#     return {"message": "Hello, FastAPI!"}


# @app.get("/test", tags=["test"], description="This is a test 接口", summary="测试接口")
# async def test():
#     return {"message": "一个测试接口"}


# # 路径参数
# @app.get(
#     "/testpath/{path}",
#     tags=["路径参数"],
#     description="This is a test2 接口",
#     summary="测试2接口",
# )
# async def testpath(path: str = Path(description="path参数", ge=1, le=100)):
#     return {"message": f"一个测试2接口, path: {path}"}


# # 查询参数
# @app.get(
#     "/testquery",
#     tags=["查询参数"],
#     description="This is a test3 接口",
#     summary="测试3接口",
# )
# async def testquery(query: str = Query(default=0, description="query参数")):
#     return {"message": f"一个测试3接口, query: {query}"}


# # 请求体
# class User(BaseModel):
#     id: int = Field(description="用户ID", ge=1, le=100)
#     name: str = Field(default="张三", description="姓名")
#     age: int = Field(description="年龄", ge=0, le=100)
#     email: str = Field(description="邮箱")


# @app.post(
#     "/testbody",
#     tags=["请求体"],
#     description="This is a test4 接口",
#     summary="测试4接口",
# )
# async def testbody(user: User = Body(description="请求体参数")):
#     return {"message": f"一个测试4接口, user: {user}"}


# # response_model
# @app.get(
#     "/testresponse/{id}",
#     tags=["response_model"],
#     description="This is a test5 接口",
#     summary="测试5接口",
#     response_model=User,
# )
# async def testresponse(id: int = Path(description="用户ID", ge=1, le=100)):
#     return User(
#         id=id,
#         name="王思迪",
#         age=18,
#         email="wsd04@example.com",
#     )


# # 异常
# @app.get(
#     "/testexception/{id}",
#     tags=["异常"],
#     description="This is a test6 接口",
#     summary="测试6接口",
# )
# async def testexception(id: int = Path(description="用户ID", ge=1, le=100)):
#     id_list = [1, 2, 3, 4, 5]
#     if id not in id_list:
#         raise HTTPException(status_code=404, detail="这是一个异常,不存在！")
#     return {"message": f"success, id: {id}"}


# # 依赖注入
# async def common_parameters(
#     skip: int = Query(default=0, ge=0),
#     limit: int = Query(default=10, ge=1, le=100),
# ):
#     return {"message": "这是一个依赖注入", "skip": skip, "limit": limit}


# @app.get(
#     "/testdependency",
#     tags=["依赖注入"],
#     description="This is a test7 接口",
#     summary="测试7接口",
# )
# async def testdependency(common=Depends(common_parameters)):
#     return common
