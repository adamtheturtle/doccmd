# Securing your application 🔐

Need to secure your FastAPI application and keep attackers and bots out of your API? Follow this guide!

## Background: Scopes and Roles

In the world of OAuth2, a [*scope*](https://www.oauth.com/oauth2-servers/scope/) is a unit of permission that authorises a client to take some action on a user's behalf. For example, a scope might be something like `proposal:create`. You can think of scopes as roughly analogous to the permissions that you grant when installing apps on your phone. As developers, you'll need to work with your stakeholders to define permissions for the various actions clients will be allowed to take using your service. Scopes are specific to your service, defined by you, and typically granted to clients by users themselves.

In contrast to scopes, the *roles* used in [role-based access control](https://www.redhat.com/en/topics/security/what-is-role-based-access-control) are [defined globally](https://confluence.skatelescope.org/display/SE/Draft%3A+AAA+Roles), and assigned to users by system administrators. Where scopes grant specific permissions to a client, roles are statements from the powers-that-be about what sort of user is making the request. Roles will usually be defined around job function, or the type of work people will be doing at the SKA Observatory. One user may have multiple roles simultaneously. For example, both a software engineer and a database admin.

In order to secure your API, you'll need to evaluate both scopes and roles – and potentially other considerations specific to the business logic of your own service – when deciding whether to reject or accept an incoming request. The [tools in Auth Helpers](components.md) are designed to make it easier to do that in a convenient, repeatable way.

## Step 1: Define your application's scopes

There's plenty of advice on the internet about how to define scopes: [I found this document to be helpful.](https://curity.io/resources/learn/scope-best-practices/) As a starting point, I'd suggest following a simple `{noun}:{verb}` pattern. Think about the different entities in your service and what actions clients will will need to take with them, then think about which combinations of these would ever be useful in isolation.

You want to make your scopes as small and granular as reasonable – but no smaller. In other words, scopes should define the smallest sensible unit of permission for your application. For example, in most cases, clients that are allowed to create an entity can probably also update that entity to make changes to it. It might make more sense to define a  `write` scope instead of separate `create` and `update` scopes. Resist the temptation to mechanically define a zillion different tiny CRUD scopes that will be overwhelming to our users.

In my experience, I've found it hard to define all my scopes up front in the abstract. If you're like me, you might find it easier to skip ahead to [Steps 3 and 4](#step-3-import-some-tools-and-do-a-bit-of-setup), implement the permissions first, and then come back to formalise them based on what you've learned. Ultimately, scopes are just some strings you make up, so you can experiment with them during development and figure out what makes sense in the context of your app.

## Step 2: Register your application with Entra ID

[You'll need to file a request with the OrbIT team](https://jira.skatelescope.org/servicedesk/customer/portal/1/create/991) and have them create a registration for you in Entra ID. At time of writing, the IT portal doesn't have all the necessary fields available to request registration for a service app. Do the best you can: explain in the free text fields that you want to register what Microsoft calls a ["Web API"](https://learn.microsoft.com/en-us/entra/identity-platform/quickstart-configure-app-expose-web-apis#register-the-web-api) and that it needs to expose a few scopes. At this stage, you might need a bit of back-and-forth discussion with the OrbIT team to settle on the correct setup for your app. Join the `#tmp-aaa-questions` channel to ask for help if you need it.

In addition to the scope itself, Entra ID will let you provide a display name and a description for each scope that helps users make an informed decision when granting consent to a client.

For example, you might ask to register some scopes that look like:

| Scope                            | Display name                  | Description                                                  |
| -------------------------------- | ----------------------------- | ------------------------------------------------------------ |
| `proposal:submit`                | Submit proposals              | Allows formally submitting proposals for review. This is the final step in the proposal preparation workflow. |
| `telescope-activity:low:execute` | Execute activities on SKA Low | Execute activities on SKA Low: This permission allows instructing hardware for the SKA Low telescope. |

Once your app is successfully registered, you'll get one or more API IDs (likely one for use in production and one for non-prod environments). These are UUIDs that identify your application in Entra ID. You'll need to save them somewhere and make them available as configuration data to your application. They are not confidential information, you don't have to protect them or keep them hidden in Vault. You might put them in Helm charts or read them from environment variables set in the deployment pipeline.

## Step 3: Import some tools and do a bit of setup

Start off by importing the tools that we'll be using:

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
