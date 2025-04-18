# Copyright 2024 Marimo. All rights reserved.
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Optional

from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

from marimo import _loggers
from marimo._server.api.auth import (
    RANDOM_SECRET,
    CustomAuthenticationMiddleware,
    CustomSessionMiddleware,
    on_auth_error,
)
from marimo._server.api.middleware import (
    AuthBackend,
    OpenTelemetryMiddleware,
    ProxyMiddleware,
    SkewProtectionMiddleware,
)
from marimo._server.api.router import build_routes
from marimo._server.api.status import (
    HTTPException as MarimoHTTPException,
)
from marimo._server.errors import handle_error
from marimo._server.lsp import LspServer

if TYPE_CHECKING:
    from starlette.types import Lifespan

LOGGER = _loggers.marimo_logger()


@dataclass
class LspPorts:
    pylsp: Optional[int]
    copilot: Optional[int]


# Create app
def create_starlette_app(
    *,
    base_url: str,
    host: Optional[str] = None,
    middleware: Optional[list[Middleware]] = None,
    lifespan: Optional[Lifespan[Starlette]] = None,
    enable_auth: bool = True,
    allow_origins: Optional[tuple[str, ...]] = None,
    lsp_servers: Optional[list[LspServer]] = None,
) -> Starlette:
    # --- BEGIN ADDED LOGGING ---
    LOGGER.info("create_starlette_app called with enable_auth=%s", enable_auth)
    LOGGER.info(
        "create_starlette_app called with allow_origins=%s", allow_origins
    )
    # --- END ADDED LOGGING ---

    final_middlewares: list[Middleware] = []

    effective_allow_origins = allow_origins  # Store original arg value
    if allow_origins is None:
        effective_allow_origins = ("localhost", "127.0.0.1") + (
            (host,) if host is not None else ()
        )
        # --- BEGIN ADDED LOGGING ---
        LOGGER.info(
            "create_starlette_app: allow_origins was None, using default: %s",
            effective_allow_origins,
        )
        # --- END ADDED LOGGING ---

    if enable_auth:
        # --- BEGIN ADDED LOGGING ---
        LOGGER.info(
            "create_starlette_app: Adding CustomSessionMiddleware (enable_auth=True)"
        )
        # --- END ADDED LOGGING ---
        final_middlewares.extend(
            [
                Middleware(
                    CustomSessionMiddleware,
                    secret_key=RANDOM_SECRET,
                ),
            ]
        )
    else:
        # --- BEGIN ADDED LOGGING ---
        LOGGER.info(
            "create_starlette_app: Skipping CustomSessionMiddleware (enable_auth=False)"
        )
        # --- END ADDED LOGGING ---

    # --- BEGIN ADDED LOGGING ---
    LOGGER.info(
        "create_starlette_app: Initializing AuthBackend with should_authenticate=%s",
        enable_auth,
    )
    LOGGER.info(
        "create_starlette_app: Adding CORSMiddleware with allow_origins=%s",
        effective_allow_origins,
    )
    # --- END ADDED LOGGING ---

    final_middlewares.extend(
        [
            Middleware(OpenTelemetryMiddleware),
            Middleware(
                CustomAuthenticationMiddleware,
                # Pass the received enable_auth value here
                backend=AuthBackend(should_authenticate=enable_auth),
                on_error=on_auth_error,
            ),
            Middleware(
                CORSMiddleware,
                # Pass the calculated allow_origins tuple here
                allow_origins=effective_allow_origins,
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            ),
            Middleware(SkewProtectionMiddleware),
            _create_mpl_proxy_middleware(),
        ]
    )

    if lsp_servers is not None:
        final_middlewares.extend(
            _create_lsps_proxy_middleware(servers=lsp_servers)
        )

    if middleware:
        final_middlewares.extend(middleware)

    # --- BEGIN ADDED LOGGING ---
    LOGGER.info("create_starlette_app: Creating Starlette app instance.")
    # --- END ADDED LOGGING ---

    return Starlette(
        routes=build_routes(base_url=base_url),
        middleware=final_middlewares,
        lifespan=lifespan,
        exception_handlers={
            Exception: handle_error,
            HTTPException: handle_error,
            MarimoHTTPException: handle_error,
        },
    )


def _create_mpl_proxy_middleware() -> Middleware:
    # MPL proxy logic
    def mpl_target_url(path: str) -> str:
        # Path format: /mpl/<port>/rest/of/path
        port = path.split("/", 3)[2]
        return f"http://localhost:{port}"

    def mpl_path_rewrite(path: str) -> str:
        # Remove the /mpl/<port>/ prefix
        rest = path.split("/", 3)[3]
        return f"/{rest}"

    return Middleware(
        ProxyMiddleware,
        proxy_path="/mpl",
        target_url=mpl_target_url,
        path_rewrite=mpl_path_rewrite,
    )


def _create_lsps_proxy_middleware(
    *, servers: list[LspServer]
) -> list[Middleware]:
    middlewares: list[Middleware] = []
    for server in servers:

        def path_rewrite(server_id: str) -> Callable[[str], str]:
            to_replace = (
                "/copilot" if server_id == "copilot" else f"/lsp/{server_id}"
            )
            return lambda _: to_replace

        middlewares.append(
            Middleware(
                ProxyMiddleware,
                proxy_path=f"/lsp/{server.id}",
                target_url=f"http://localhost:{server.port}",
                path_rewrite=path_rewrite(server.id),
            )
        )
    return middlewares
