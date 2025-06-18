from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Dict
from pydantic import BaseModel

from models.expense_models import GeneralResponse # Assuming GeneralResponse can be used
# We might need specific response models for settlements and balances later.
from services import settlement_service # Will be created later
from database import get_database
from motor.motor_asyncio import AsyncIOMotorDatabase

router = APIRouter()

class BalanceResponse(BaseModel):
    person: str
    balance: float # Positive if owed to, negative if owes

class SettlementTransaction(BaseModel):
    payer: str
    receiver: str
    amount: float

@router.get("/balances", response_model=GeneralResponse)
async def get_balances_api(db: AsyncIOMotorDatabase = Depends(get_database)):
    """Show each person's overall balance (owes/owed)."""
    try:
        balances = await settlement_service.calculate_balances(db)
        # Format balances for response if needed, e.g., List[BalanceResponse]
        # For now, returning the raw dictionary from the service
        return GeneralResponse(
            success=True,
            message="Balances calculated successfully.",
            data=balances # data=[BalanceResponse(person=p, balance=b) for p, b in balances.items()]
        )
    except Exception as e:
        # Log the exception e
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error calculating balances: {str(e)}")

@router.get("/", response_model=GeneralResponse)
async def get_settlements_api(db: AsyncIOMotorDatabase = Depends(get_database)):
    """Get current settlement summary (simplified transactions)."""
    try:
        settlements = await settlement_service.calculate_simplified_settlements(db)
        # Format settlements for response if needed, e.g., List[SettlementTransaction]
        # For now, returning the raw list of transactions from the service
        return GeneralResponse(
            success=True,
            message="Settlements calculated successfully.",
            data=settlements # data=[SettlementTransaction(**s) for s in settlements]
        )
    except Exception as e:
        # Log the exception e
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error calculating settlements: {str(e)}")

# BaseModel is now imported at the top of the file