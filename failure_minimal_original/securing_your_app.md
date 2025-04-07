```python
# You get this value by registering in step 2:
MY_API = "api://3688e6c2-87c0-4584-a674-c11e63e9b442"

@app.get("/hello")
async def say_hello(
    auth: Annotated[
        AuthContext,
    ],
):
     return {"msg": f"Hello, user: {auth.user_id}"}
```

```python
@app.get("/goodbye", dependencies=[Requires(
        )])
async def say_goodbye():
     return {"msg": "Goodbye"}
```

```python
operators_only = Requires(
)
```
