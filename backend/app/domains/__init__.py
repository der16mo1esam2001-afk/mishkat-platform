from .vitalis.routes import router as vitalis_router
from .aquanex.routes import router as aquanex_router
from .agronex.routes import router as agronex_router
from .energis.routes import router as energis_router
from .nexora.routes import router as nexora_router

__all__ = [
    "vitalis_router",
    "aquanex_router",
    "agronex_router",
    "energis_router",
    "nexora_router",
]
