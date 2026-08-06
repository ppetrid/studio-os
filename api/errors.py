from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from studio_midi.backend import AmbiguousPortError, PortNotFoundError
from studio_midi.router import ProcessedRouteNotImplementedError


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(PortNotFoundError)
    def _port_not_found(request: Request, exc: PortNotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(AmbiguousPortError)
    def _ambiguous_port(request: Request, exc: AmbiguousPortError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    @app.exception_handler(ProcessedRouteNotImplementedError)
    def _processed_not_implemented(
        request: Request, exc: ProcessedRouteNotImplementedError
    ) -> JSONResponse:
        return JSONResponse(status_code=501, content={"detail": str(exc)})

    @app.exception_handler(KeyError)
    def _unknown_scene(request: Request, exc: KeyError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})
