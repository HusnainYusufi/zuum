from fastapi import APIRouter
import sys
from pathlib import Path

from db_models import get_db
from db_models import Journey

# Add the services directory to Python path for importing test modules
current_dir = Path(__file__).parent
backend_dir = current_dir.parent
services_dir = backend_dir / "services"
if str(services_dir) not in sys.path:
    sys.path.append(str(services_dir))

from langrapghs.tests.run_all_tests import run_all_tests as execute_all_tests

router = APIRouter(
    prefix="/tests",
    tags=["tests"],
    responses={404: {"description": "Not found"}},
)

db = next(get_db())

@router.get("/run_all_tests")
async def run_all_tests():
    """
    Run all LangGraph tests and return results as JSON
    """
    try:
        test_results = execute_all_tests()
        return {
            "status": "completed",
            "results": test_results
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "results": {}
        }





