``` python
from ska_aaa_authhelpers import (
    AuditLogFilter,
    AuthContext,
    AuthFailError,
    Requires,
    Role,
    auth_watchdog_lifespan,
)
# You probably already have this somewhere:
from ska_ser_logging import configure_logging
```

### Configure audit logging

Wherever your app sets up logging, add the `AuditLogFilter`

```python
configure_logging(level="WARNING", tags_filter=AuditLogFilter)
```

This will automatically annotate log entries with a `user_id` and a `trace` to help us tie together log entries for auditing purposes.

### Unleash the watchdog

When creating your FastAPI app instance, add the `auth_watchdog_lifespan()` [lifespan:](https://fastapi.tiangolo.com/advanced/events/#lifespan-events)

```python
app = FastAPI(lifespan=auth_watchdog_lifespan())
```

This runs once when your app starts up and double-checks that all your routes are secured. Now, if you try to run your app, you should see the watchdog barking about security holes, and preventing it from starting...

```
ska_aaa_authhelpers.watchdog.SecurityHoleError: Route...does not have a Requires() dependency that defines scopes and roles to control access.
```

## Step 4: Add Requires() to all your routes

The `Requires()`utility leverages FastAPI's native [dependency-injection system](https://fastapi.tiangolo.com/tutorial/dependencies/) to create a [Security](https://fastapi.tiangolo.com/reference/security/) dependency that gets called on every request in order to automatically enforce authorisation restrictions. It will return an HTTP 403 error unless the request is accompanied by a signed access token valid for a certain audience, plus particular scopes and roles. If you've registered your app in [step 2](#step-2-register-your-application-with-entra-id), you'll already know what value you need for the `audience` but if not, that's fine and you can use a dummy value to get started developing and testing.

### Example: `AuthContext`  passed into your view

If you're experienced with FastAPI and its use of `Depends()` then this should look pretty familiar to you:

```python
# You get this value by registering in step 2:
MY_API = "api://3688e6c2-87c0-4584-a674-c11e63e9b442"

@app.get("/hello")
async def say_hello(
    auth: Annotated[
        AuthContext,
        Requires(
            audience=MY_API,
            roles={Role.SW_ENGINEER},
            scopes={"hello:listen"},
        ),
    ],
):
     return {"msg": f"Hello, user: {auth.user_id}"}
```

On every request, FastAPI will automatically attempt to satisfy the dependency by providing an `AuthContext` object that meets your requirements and passing it as a parameter for use in your view function.

### Example: Using `Requires()` without accessing `AuthContext`

For some simple cases, you might not need to use the `auth` object in your view function, but you can still use `Requires()` to secure your routes by passing it as one of the dependencies directly in [the FastAPI path operation decorator.](https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-in-path-operation-decorators/) For example:

```python
@app.get("/goodbye", dependencies=[Requires(
            audience=MY_API,
            roles={Role.SW_ENGINEER},
            scopes={"hello:listen"},
        )])
async def say_goodbye():
     return {"msg": "Goodbye"}
```

### Example: DRY out your audience with functools.partial

The audience field is always going to be the same for a single deployment of your app, so if you have many views, passing the same value can quickly get repetitive. I've found using Python's [functools.partial](https://docs.python.org/3/library/functools.html#functools.partial) to set it one time is a nice trick for removing duplication from your code:

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
