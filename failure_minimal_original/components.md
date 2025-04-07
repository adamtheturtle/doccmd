# Components ⚙️

At first glance, this library might look like a grab bag of random bits and pieces. I swear, they're all carefully designed to work together to help you enforce authorisation rules in your FastAPI application. You aren't obliged to use these tools, but they are here to help make it easier to do the right thing and harder to accidentally do the wrong thing.

This page covers all the major public-facing components in this library, with information useful for both consumers looking to use this library and implementation details that may be relevant for developers working on the library itself.


## Watchdog 🐕‍🦺


The `auth_watchdog_lifespan()` is your faithful friend that will watch to make sure you haven't left any doors unlocked by mistake and bark if you have.


The first thing you should do is add it to your application like this:

```python
from fastapi import FastAPI

from ska_aaa_authhelpers import auth_watchdog_lifespan

app = FastAPI(lifespan=auth_watchdog_lifespan())
```

This introduces a [FastAPI lifespan](https://fastapi.tiangolo.com/advanced/events/#lifespan-events) event manager that runs once, at application startup time, and throws a class:`SecurityHoleError` exception if you have accidentally forgotten to secure any routes. In most cases, this is all you need and you can proceed from here.

If your app contains routes that absolutely must bypass any authorisation enforcement (this is discouraged, consider using [`Role.ANY`](#role) instead), you can pass the names of the route functions to `auth_watchdog_lifespan()` with the `allow_unsecured` parameter.

```python
from time import time

from fastapi import FastAPI
from ska_aaa_authhelpers import auth_watchdog_lifespan

app = FastAPI(
    # We want to bypass any security on the `get_time` route:
    lifespan=auth_watchdog_lifespan(allow_unsecured=['get_time'])
)

@app.get('/time')
def get_time():
    return time()
```

## Requires() 🔒

The `Requires()` utility allows you to specify in broad terms the authorisation needed for each path operation in your application. You'll need to pass one or more roles, one or more scopes, and the audience parameter expected – the audience should *always* be your own service's Application ID, [assigned at registration time by Microsoft Entra ID.](https://learn.microsoft.com/en-us/entra/identity-platform/quickstart-configure-app-expose-web-apis)

```python
from typing import Annotated
from ska_aaa_authhelpers import AuthContext, Requires, Role

from .my_app import app, execute_observation, MY_APP_ID
from .my_models import Observation
from .my_scopes import RUN_OBSERVATION


@app.post("/observation/new")
def new_observation(
    data: Observation,
    auth: Annotated[
        AuthContext,
        Requires(
            audience=MY_APP_ID,
            roles={Role.LOW_TELESCOPE_OPERATOR},
            scopes={RUN_OBSERVATION},
        ),
    ],
):
    results = execute_observation(data, owner=auth.user_id)
    return results
```

Under the hood, `Requires()`is a utility that automatically creates a [FastAPI Security()](https://fastapi.tiangolo.com/reference/dependencies/#fastapi.Security) dependency and also the [security scheme](https://fastapi.tiangolo.com/reference/security/) wrapped inside that dependency.

## AuthContext 🪪

The AuthContext provided to your view functions by `Requires()` is a [Pydantic model](https://docs.pydantic.com) that represents all the authorisation information we have about this request. Your application should further evaluate these parameters to make a decision about whether to accept or deny the request.

```{eval-rst}
.. autopydantic_model:: ska_aaa_authhelpers.auth_context.AuthContext
    :no-index: true
    :model-show-json: false
```

You may notice that many of the fields are are [frozensets](https://docs.python.org/3/library/stdtypes.html#frozenset). It's often a good approach to reason about authorisation in terms of [set operations](https://realpython.com/python-sets/#operating-on-a-set): is this user a member of a group? Is there an intersection between the scopes this client has been granted and the scopes required to perform an action? Is there an intersection between the [`principals`](https://en.wikipedia.org/wiki/Principal_%28computer_security%29) of this request and the owners of a resource?

## Role 👤

Conceptually, Roles are [globally-defined attributes](https://confluence.skatelescope.org/display/SE/Draft%3A+AAA+Roles) assigned to users based on the work they are doing at SKAO. In terms of this library `Role` is just an enum designed to be used in `Requires()` and your view functions.

```{eval-rst}
.. autoclass:: ska_aaa_authhelpers.roles.Role
    :no-index: true
    :members:
    :undoc-members:
```

As a matter of implementation, [Roles are managed as Entra Groups:](https://learn.microsoft.com/en-us/entra/identity-platform/custom-rbac-for-developers#choose-an-approach) Anyone who is in the software engineers group is assigned the `SW_ENGINEER` role. The point of this enum is basically to hardcode the special role-granting groups so that devs can work with nice enum names instead of opaque UUIDs. It's also used internally to populate the `AuthContext.roles` field after decoding the access token.

## AuthFailError() ⛔

Pretty much does what it says on the tin. This is raised by AuthHelpers itself when the access token claims fail to meet the application's policies as declared in `Requires()`. Applications may also raise it if the app's own internal authorisation logic is not satisfied, triggering an [HTTP 403: Forbidden](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status/403) response to the client.

```python
raise AuthFailError("Only authorised parties allowed.")
```

This is a subclass of FastAPI's [HTTPException](https://fastapi.tiangolo.com/tutorial/handling-errors/#use-httpexception) that adds a log entry to the audit log when requests are rejected.

## AuditLogFilter 📝

The `AuditLogFilter` is a [Python logging filter](https://docs.python.org/3/library/logging.html#filter-objects) designed to be used as part of the [ska-ser-logging infrastructure](https://gitlab.com/ska-telescope/ska-ser-logging).

```python
from ska_ser_logging import configure_logging
from ska_aaa_authhelpers import AuditLogFilter

configure_logging(level="WARNING", tags_filter=AuditLogFilter)
```

Despite its name, the `AuditLogFilter` doesn't actually filter out any log entries, instead it adds tags for the `user_id` and `trace` fields, allowing us to tie log records back to a specific user request and authorisation flow. [This is a standard recognised usage](https://docs.python.org/3/howto/logging-cookbook.html#filters-contextual) for filter objects in Python logging.

Internally, it relies on [starlette-context](https://starlette-context.readthedocs.io/en/latest/) to retrieve the `AuthContext` from a request-global context manager.

## mint_test_token() 🗝️

This is a utility for generating access tokens signed with built-in test keys provided by the library. Because Microsoft controls the private keys used to sign Entra ID access tokens, we can't simply generate our own tokens that will pass signature verification using the default MS Entra public keys. Instead, for testing purposes, we use our own private key to sign tokens. You can then pass these tokens in the HTTP Authorization header to your application under test.

``````python
from fastapi.testclient import TestClient
from ska_aaa_authhelpers.test_helpers import mint_test_token

token = mint_test_token()

client = TestClient(app, headers={"Authorization": f"Bearer {token}"})
``````

This function can be called without any arguments and it will create a token associated to a fake `TEST_USER`, issued for default `TEST_SCOPES`, `TEST_ROLES` and  `TEST_GROUPS` etc. You can pass specific arguments to override any of these token claims if your test scenarios rely on particular users or groups, and you'll likely need to include scopes and roles relevant for your own application.

Internally, `mint_test_token()` directly calls the [joserfc library](https://jose.authlib.org/en/) to encode and sign a [JWT](https://jwt.io/) access token with a similar set of claims to those issued by Microsoft.

See [Testing Your Applications](testing.md) for more usage examples.

## monkeypatch_auth_pubkeys 🙈

On the flip side, once we've been minting tokens signed with our own test private key, we'll need to verify them using our test public keys instead of Microsoft's pubkeys. `monkeypatch_auth_pubkeys` is intended to be used inside a pytest test fixture to monkeypatch all `Requires()` instances replacing the `DEFAULT_PUBLIC_KEYS` (i.e. Microsoft's keys) with `TEST_PUBLIC_KEYS`. You can put this in your `conftest.py`:

```python
import pytest
from ska_aaa_authhelpers.test_helpers import monkeypatch_auth_pubkeys

# put this in conftest.py
@pytest.fixture(scope="session", autouse=True)
def patch_pubkeys():
    monkeypatch_auth_pubkeys()
```

The guts of this implementation is really gnarly: it uses `gc.get_objects()` to fish every single live object in the Python interpreter out of memory, filters with `isinstance()` to find internal `TokenScheme()` instances that were generated  by `Requires()`and any `functools.partials` that could be used during a test session to create more. Then, it loops over everything replacing the `keys` attributes. It does not bother trying to restore the original keys, because the assumption is that this fixture will be enabled globally for the whole test session.
