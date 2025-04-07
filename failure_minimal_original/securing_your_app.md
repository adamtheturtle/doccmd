```python
import functools

# The name 'Permissions' is arbitrary here, pick whatever name you like.
Permissions = functools.partial(Requires, audience=MY_API)

@app.get("/hi")
async def say_hi(
    auth: Annotated[
        AuthContext,
        Permissions(
            roles={Role.SW_ENGINEER},
            scopes={"hello:listen",},
        ),
    ],
):
    return {"msg": f"Hi, user: {auth.user_id}"}
```

Going further, if you have a bunch of views that all require the same roles and scopes, you can simply pass the exact same object to multiple views.

```python
operators_only = Requires(
    audience=MY_API,
    scopes={"telescope:operate"},
    roles={Role.LOW_OPERATOR, Role.MID_OPERATOR}
)

app.get('/array/')
async def get_arrays(auth: Annotated[AuthContext, operators_only]):
    return {"arrays": ["array1", "array2"]}

app.get('/calibration/')
async def get_calibration(auth: Annotated[AuthContext, operators_only]):
    return {"calibration": "good"}
```

For some applications, you might be done here! If your app doesn't have any authorisation requirements more granular than controlling access to entire views based on scopes and roles, then you're all set. You can move on to [testing your application](testing.md).
