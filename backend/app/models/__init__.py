# Import models so Base.metadata is fully populated before create_all runs.
from app.models.resource import Resource  # noqa: F401
from app.models.standard import Standard  # noqa: F401
from app.models.tag import Tag  # noqa: F401
from app.models.udl import UdlPrinciple  # noqa: F401
