from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from studio_midi.backend import AmbiguousPortError, PortNotFoundError
from studio_midi.router import ProcessedRouteNotImplementedError
from studio_midi.scenes import SceneNotFoundError


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

    @app.exception_handler(SceneNotFoundError)
    def _scene_not_found(request: Request, exc: SceneNotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})
