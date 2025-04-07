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

## Step 5: (Optionally) Implement any granular, application-specific authorisation logic

However, in most cases, developers will need to implement at least some application-specific logic to decide whether to allow or deny a request. The library can't make these choices for you, but the `AuthContext` model provides easy access to the information needed to inform your decisions.

```{eval-rst}
.. autopydantic_model:: ska_aaa_authhelpers.auth_context.AuthContext
    :no-index: true
    :model-show-json: false
```

The two fields you'll most commonly be interested in are the `user_id` and the `principals` –  a set containing all the [security principals](https://github.com/amih90/techtrain-handson-azure-development/blob/main/docs/4-security-principals.md) associated with this request (i.e. the `user_id`, plus the IDs of all the groups where this user is a member). You might also need to re-examine `roles`: `Requires()` guarantees that users hold at least one of the roles you've specified, but in some cases your logic might be more complex, with different roles granted or denied access to particular entities in your app.

Let's imagine we're working on part of a service that allows updating proposals for the SKAO. We want to ensure that astronomers can update their own proposals (or proposals belonging to a group that they're a member of), but they aren't allowed to edit other people's proposals. However, SKAO Staff can make changes to any proposal in the system.

Here's a fake example showing how you might encode that logic in your views:

```python
from .proposal_app import app, db_conn, ProposalData

@app.put("/proposal/{id}/")
async def modify_proposal(
    proposal_id: int,
    updated_data: ProposalData,
    db: Depends(db_conn),
    auth: Annotated[
        AuthContext,
        Permissions(roles={Role.ASTRONOMER, Role.SKAO_STAFF}, scopes={"proposal:write"}),
    ],
) -> ProposalData:
    metadata = db.get_metadata(proposal_id)
    if auth.principals.intersection(metadata.owners) or Role.SKAO_STAFF in auth.roles:
        return db.update(updated_data)
    else:
        msg = f"Only SKAO staff, or the owners of proposal id={proposal_id}, {metadata.owners} can modify it."
        raise AuthFailError(msg)
```

Whew, that's about it! In theory, you've now got everything you need to secure your application. You may want to go back to [Step 1](#step-1-define-your-application-s-scopes) to revisit your scopes, or move on to [Testing Your Applications](testing.md) to verify the rules you've written actually behave the way you expect.
