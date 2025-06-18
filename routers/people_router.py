from fastapi import APIRouter, HTTPException, Depends, status
from typing import List

from models.expense_models import GeneralResponse # Reusing GeneralResponse
from services import expense_service # People are derived from expenses
from database import get_database
from motor.motor_asyncio import AsyncIOMotorDatabase

router = APIRouter()

@router.get("/", response_model=GeneralResponse)
async def list_people_api(db: AsyncIOMotorDatabase = Depends(get_database)):
    """List all unique people derived from expenses."""
    try:
        people = await expense_service.get_all_people(db)
        return GeneralResponse(
            success=True,
            message="People listed successfully.",
            data={"people": people}
        )
    except Exception as e:
        # Log the exception e
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error listing people: {str(e)}")