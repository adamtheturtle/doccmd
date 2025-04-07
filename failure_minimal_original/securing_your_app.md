```python
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
pass
```
