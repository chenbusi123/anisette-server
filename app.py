"""
FastAPI HTTP server for authentication/provisioning microservice.
Implements Anisette-like architecture with v1 (shared) and v3 (per-client) endpoints.
"""

import asyncio
import logging
import os
from typing import Optional

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse

from config import Config
from models import HealthResponse, ProvisioningRequest, ProvisioningResponse
from provisioning import ProvisioningManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Anisette Provisioning Server",
    description="Authentication/provisioning microservice server",
    version="1.0.0",
)

config = Config.from_env()
provisioning_manager = ProvisioningManager(config)


@app.on_event("startup")
async def startup_event() -> None:
    """Initialize provisioning manager on startup."""
    logger.info(f"Starting Anisette server on {config.hostname}:{config.port}")
    logger.info(f"Storage path: {config.storage_path}")
    logger.info(f"TLS enabled: {config.tls_enabled}")
    provisioning_manager.initialize()


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Clean up resources on shutdown."""
    logger.info("Shutting down Anisette server")
    provisioning_manager.cleanup()


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Health check endpoint for load balancers and orchestration platforms.
    
    Returns:
        HealthResponse: Server health status and version information.
    """
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        timestamp=provisioning_manager.get_timestamp(),
    )


@app.post("/1")
async def provisioning_v1(request: Request) -> JSONResponse:
    """
    V1 provisioning endpoint with shared device state.
    
    All requests share the same device state and ADI data.
    Less secure but compatible with legacy clients.
    
    Args:
        request: Raw HTTP request.
        
    Returns:
        JSONResponse: Provisioning data including device state and ADI.
        
    Raises:
        HTTPException: On validation or processing errors.
    """
    try:
        body = await request.json()
        logger.debug(f"V1 request received from {request.client}")
        
        provisioning_request = ProvisioningRequest(**body)
        response_data = await asyncio.to_thread(
            provisioning_manager.get_v1_data,
            provisioning_request,
        )
        
        logger.info(f"V1 request processed successfully")
        return JSONResponse(content=response_data.model_dump())
        
    except ValueError as e:
        logger.warning(f"Invalid request data: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(f"V1 provisioning error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error") from e


@app.post("/3")
async def provisioning_v3(request: Request) -> JSONResponse:
    """
    V3 provisioning endpoint with per-client unique device state.
    
    Each request generates unique device data for that specific client.
    More secure and suitable for modern authentication flows.
    
    Args:
        request: Raw HTTP request.
        
    Returns:
        JSONResponse: Unique provisioning data for the requesting client.
        
    Raises:
        HTTPException: On validation or processing errors.
    """
    try:
        body = await request.json()
        client_info = (
            f"{request.client.host}:{request.client.port}"
            if request.client
            else "unknown"
        )
        logger.debug(f"V3 request received from {client_info}")
        
        provisioning_request = ProvisioningRequest(**body)
        response_data = await asyncio.to_thread(
            provisioning_manager.get_v3_data,
            provisioning_request,
            client_info,
        )
        
        logger.info(f"V3 request processed successfully for {client_info}")
        return JSONResponse(content=response_data.model_dump())
        
    except ValueError as e:
        logger.warning(f"Invalid request data: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(f"V3 provisioning error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error") from e


@app.get("/")
async def root() -> JSONResponse:
    """Root endpoint with API information."""
    return JSONResponse(
        content={
            "name": "Anisette Provisioning Server",
            "version": "1.0.0",
            "endpoints": {
                "health": "/health",
                "provisioning_v1": "/1 (POST)",
                "provisioning_v3": "/3 (POST)",
            },
        }
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=config.hostname,
        port=config.port,
        log_level="info",
        ssl_keyfile=config.tls_key_path if config.tls_enabled else None,
        ssl_certfile=config.tls_cert_path if config.tls_enabled else None,
    )
