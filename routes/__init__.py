
from .ui import router as ui_router
from .retell import router as retell_router
from .notifications import router as notifications_router
from .retell_check_in import router as retell_check_in_router
from .prompt_config import router as prompt_config_router
from .forms import router as forms_router
from .auth import router as auth_router
from .webhook_route import router as webhook_router
from .shipments import router as shipments_router

# Import from file with hyphen in name
import importlib
checkin_module = importlib.import_module('.check-in', package='routes')
checkin_router = checkin_module.router

__all__ = ['conversation_router', 'ui_router', 'retell_router', 'notifications_router', 'checkin_router', 'retell_call_router', 'prompt_config_router', 'retell_check_in_router', 'forms_router', 'auth_router', 'webhook_router', 'shipments_router']