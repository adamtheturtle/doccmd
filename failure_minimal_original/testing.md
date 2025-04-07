# Testing your applications 🗹

If you're using `ska-aaa-authhelpers` to secure your app, then it will reject unauthorised API calls with a 403 error. However, that can make it harder to write integration tests to verify application behaviour.

## Integration testing

In your tests, you can use `mint_test_token` to generate an access token, and set up a [TestClient](https://fastapi.tiangolo.com/reference/testclient/) that passes that token in an HTTP Authorization header, just as client apps will do in a deployed environment.

### Sample integration tests


```python
from fastapi.testclient import TestClient
from ska_aaa_authhelpers import Role
from ska_aaa_authhelpers.test_helpers import mint_test_token

from my_app import MY_SCOPES, MY_SERVICE_ID, app

# If you want the same authorisation, you can share one client instance
# across multiple tests...
token = mint_test_token(audience=MY_SERVICE_ID, scopes=MY_SCOPES, roles=Role.SW_ENGINEER)
client = TestClient(app, headers={"Authorization": f"Bearer {token}"})


def test_get_item1():
    response = client.get("/item/1")
    assert response.status_code == 200
    assert response.json() == {"expected": "result1"}


def test_get_item2():
    response = client.get("/item/2")
    assert response.status_code == 200
    assert response.json() == {"expected": "result2"}


def test_other_user():
    # Or you can create and pass separate tokens for different test scenarios:
    tkn = mint_test_token(
        user_id="Different user", audience=MY_SERVICE_ID, scopes=MY_SCOPES, roles=Role.SW_ENGINEER
    )
    with TestClient(my_app) as client:
        resp = client.get("/item/1", headers={"Authorization": f"Bearer {tkn}"})
        assert resp.status_code == 403
```


:::{tip}
If you have installed [`fastapi[standard]`](https://fastapi.tiangolo.com/fastapi-cli/) or if you install this library with the optional scripts dependency, as `ska_aaa_authhelpers[scripts]` then you also have `mint_test_token` available as a CLI tool...

```bash
$ mint_test_token --help
```

...you can use this to generate tokens to copy-paste for development, testing or use in continuous integration environments.
:::




### Replacing the public keys

However, requests made with these tokens will still fail because they are signed with our own test private key, rather than the Entra ID private key controlled by Microsoft. Tokens we sign can't be validated with Microsoft's public keys, and we can't issue a token with their private key, so the only option is to replace the default public keys with test public keys that match our test private key.

One way to make this work without any changes to your application code is by enabling a [Pytest fixture](https://docs.pytest.org/en/7.1.x/how-to/fixtures.html#autouse-fixtures-fixtures-you-don-t-have-to-request) that automatically replaces `ska_aaa_authhelpers.jwt.DEFAULT_PUBLIC_KEYS` with `ska_aaa_authhelpers.test_helpers.TEST_PUBLIC_KEYS`. For example:

```python
import pytest
from ska_aaa_authhelpers.test_helpers import monkeypatch_auth_pubkeys

# put this in conftest.py
@pytest.fixture(scope="session", autouse=True)
def patch_pubkeys():
    monkeypatch_auth_pubkeys()
```

If you run into any issues or find global patching won't work for you, speak to the Auth Helpers authors or start a discussion on `#tmp-aaa-questions` .
## Unit testing custom authorisation logic

As discussed in [Securing Your App](securing_your_app.md#step-5-optionally-implement-any-granular-application-specific-authorisation-logic) most apps will involve some amount of custom authorisation logic.

If you structure the core of your authorisation logic as simple combinations of ["pure" functions](https://dev.to/alexkhismatulin/pure-functions-explained-for-humans-1j3c), it becomes much easier to unit test in a quick, deterministic way. For example, let's imagine we were trying to define some rules around who can edit proposals...

```python
from ska_aaa_authhelpers import AuthContext, Role

def owner_of_proposal(ctx: AuthContext, owners_group_id: GroupID) -> bool:
    return owners_group_id in ctx.principals

def is_skao_staff(ctx: AuthContext) -> bool:
    return Role.SKAO_STAFF in ctx.roles

def orphan_proposal(proposal: Proposal) -> bool:
    return proposal.owners_group.is_empty()

def allowed_to_edit_proposal(ctx: AuthContext, proposal: Proposal) -> (bool, str):
    if (
        is_skao_staff(ctx)
        or owner_of_proposal(ctx, proposal.owners_group.id)
        or orphan_proposal(proposal)
    ):
        return True, ""
    return False, "Only staff or owners may update proposals, except in the case of orphaned proposals with no owners."
```

Because these functions are so simple and depend entirely on their arguments, it becomes easier to make sure you've exhaustively covered all the cases you need:
```python
@pytest.mark.parameterize(
    ("auth", "expected"),
    (
        (AuthContext(roles={Role.SKAO_STAFF}), True),
        (AuthContext(roles={Role.SW_ENGINEER}), False),
        (AuthContext(roles={Role.TELESCOPE_OPERATOR}), False),
    ),
)
def test_is_skao_staff(auth, expected):
    assert is_skao_staff(auth)
```

Your view function might look something like this, but you won't need to worry as much about about exercising authorisation behaviour in your integration tests because you already have confidence in the logic from your comprehensive unit tests.

```python
@app.put("/proposal/{id}")
def update_proposal(
    id: str,
    data: ProposalData,
    auth: Annotated[
        AuthContext, Requires(scopes={"proposal:write"}, roles={Role.SKAO_STAFF, Role.ASTRONOMER})
    ],
):
    proposal = database.get_proposal(id)
    allowed, msg = allowed_to_edit_proposal(ctx, proposal)
    if allowed:
        return database.update_proposal(data)
    else:
        raise AuthFailError(msg)
```
