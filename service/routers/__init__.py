"""REST API routers for Amarisoft services."""

from .enb import router as enb_router
from .ims import router as ims_router
from .mme import router as mme_router
from .system import router as system_router
from .ue import router as ue_router

__all__ = [
    "system_router",
    "enb_router",
    "mme_router",
    "ims_router",
    "ue_router",
]
