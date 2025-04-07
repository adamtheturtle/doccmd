# Developing Authhelpers 🛠️

## Environment setup

Clone the repository, install dependencies

```bash
git clone git@gitlab.com:ska-telescope/ska-aaa-authhelpers.git
cd ska-aaa-auth-helpers
poetry install --with=dev,docs -E scripts
```

Install/update the .make submodule:

```
git submodule update --recursive --remote
git submodule update --init --recursive
```

**Autoformat:**

```bash
poetry run make python-format
```

**Lint/type check**

Linting is [Ruff](https://docs.astral.sh/ruff/), type checking with [pyright](https://microsoft.github.io/pyright/)

``````
poetry run make python-lint
``````

:::{tip}
This repository uses [Ruff](https://docs.astral.sh/ruff/) for linting and formatting, in place of the default tools pylint/black.

When running make commands you will see warnings like `Makefile:18: warning: overriding recipe for target 'python-do-format'`

These are expected and don't indicate any problem in your code.
:::

**Test:**

```bash
poetry run make python-test
```

**Docs**
Documentation (except for the README) is located in `docs/src/` and can be built with...

```bash
poetry run make docs-build html
```

...this will put output in `docs/build/html`

## Orientation

:::{seealso}
You may want to check out [Components](components.md) for more details on the public API of this library.
:::

To understand the implementation of Authhelpers, start with `security.Requires()` This is a utility function that automatically creates a FastAPI [Security()](https://fastapi.tiangolo.com/reference/dependencies/#fastapi.Security) subclass that wraps a `TokenScheme()`instance as its callable. TokenScheme itself has a child-dependency on an HTTP Authorization header, which it uses to obtain the JWT access token, decode and verify it, and finally create and return an  `AuthContext` object for the application to work with.

We're using [joserfc](https://jose.authlib.org/en/) to deal with all the JWT-decoding mechanics, which in turn uses [cryptography](https://cryptography.io/en/latest/) for the nitty-gritty details of signature verification.

Other slightly magical or weird bits:

- We're relying on [Starlette Context](https://starlette-context.readthedocs.io/en/latest/fastapi.html) to set a per-request global context so we can access the auth context inside `AuditLogFilter` without explicitly passing it all the way into the logger.
- auth_watchdog_lifespan() is a [Starlette lifespan](https://fastapi.tiangolo.com/advanced/events/#lifespan-events) – a kind of context manager used to run events before the application starts.
- `test_helpers.monkeypatch_auth_pubkeys()` goes fishing through the garbage collector to find live objects carrying references to `DEFAULT_PUBLIC_KEYS` and replace them with `TEST_PUBLIC_KEYS`. This is kind of ugly, but it means the application code doesn't have to change to accommodate tests.
