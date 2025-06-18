from pydantic import BaseModel, Field, validator
from typing import List, Optional, Union, Dict
from enum import Enum
from bson import ObjectId
import datetime

# Helper for ObjectId serialization
class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v, field_info=None):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, field_schema):
        field_schema.update(type="string")

class SplitMethodEnum(str, Enum):
    equal = "equal"
    exact = "exact"
    percentage = "percentage"
    shares = "shares"

class ParticipantShare(BaseModel):
    name: str = Field(..., min_length=1, description="Name of the participant.")
    # Share can be an amount (float), percentage (float), or number of shares (int/float)
    # It's optional because for 'equal' split, it's not needed or calculated.
    share: Optional[Union[float, int]] = Field(None, description="Share value (amount, percentage, or shares count). Depends on split_method.")

class ExpenseBase(BaseModel):
    amount: float = Field(..., gt=0, description="Total amount of the expense.")
    description: str = Field(..., min_length=1, max_length=255, description="Description of the expense.")
    paid_by: str = Field(..., min_length=1, description="Name of the person who paid the expense.")
    split_method: SplitMethodEnum = Field(..., description="Method used to split the expense.")
    participants: List[ParticipantShare] = Field(..., min_length=1, description="List of participants and their respective shares/contributions.")
    date: datetime.datetime = Field(default_factory=datetime.datetime.utcnow, description="Date and time of the expense creation.")

    @validator('participants')
    def paid_by_must_be_a_participant(cls, participants, values):
        if 'paid_by' in values:
            paid_by_name = values['paid_by']
            if not any(p.name == paid_by_name for p in participants):
                raise ValueError(f"The person who paid ('{paid_by_name}') must be in the participants list.")
        return participants

    @validator('participants')
    def validate_shares_based_on_split_method(cls, participants, values):
        split_method = values.get('split_method')
        amount = values.get('amount')

        if not split_method or amount is None:
            # Not enough info to validate yet, or other validators will catch it
            return participants

        if split_method == SplitMethodEnum.exact:
            total_shares_amount = sum(p.share for p in participants if p.share is not None)
            if not abs(total_shares_amount - amount) < 1e-9: # Using tolerance for float comparison
                raise ValueError(f"For 'exact' split, the sum of participant shares ({total_shares_amount}) must equal the total amount ({amount}).")
        
        elif split_method == SplitMethodEnum.percentage:
            total_percentage = sum(p.share for p in participants if p.share is not None)
            if not abs(total_percentage - 100.0) < 1e-9: # Using tolerance for float comparison
                raise ValueError(f"For 'percentage' split, the sum of participant percentages ({total_percentage}%) must be 100%.")
            for p in participants:
                if p.share is not None and (p.share <= 0 or p.share > 100):
                    raise ValueError("Percentages must be greater than 0 and at most 100.")

        elif split_method == SplitMethodEnum.shares:
            if not all(p.share is not None and p.share > 0 for p in participants):
                raise ValueError("For 'shares' split, all participants must have a positive share value.")
        
        elif split_method == SplitMethodEnum.equal:
            # For 'equal' split, individual shares might be None or not provided in input,
            # as they are calculated. If provided, they are typically ignored by the service layer.
            pass # No specific validation here, service layer handles division

        return participants

class ExpenseCreate(ExpenseBase):
    pass

class ExpenseUpdate(ExpenseBase):
    # All fields are optional for update, but if provided, they must be valid.
    amount: Optional[float] = Field(None, gt=0)
    description: Optional[str] = Field(None, min_length=1, max_length=255)
    paid_by: Optional[str] = Field(None, min_length=1)
    split_method: Optional[SplitMethodEnum] = None
    participants: Optional[List[ParticipantShare]] = Field(None, min_length=1)
    date: Optional[datetime.datetime] = None # Usually not updated, but can be allowed

    @validator('participants', pre=True, always=True)
    def check_participants_for_update(cls, participants, values):
        # This validator ensures that if other dependent fields (like paid_by, split_method, amount)
        # are also being updated, the participants list is valid in that new context.
        # The actual validation logic is complex if only partial fields are provided.
        # For simplicity, if participants are provided, they are validated against other *provided* fields.
        # If participants are NOT provided, existing ones are assumed to be used with other updated fields.
        # This might require more sophisticated handling in the service layer.
        if participants is None:
            return participants # No update to participants, skip validation here

        # Re-run base validators if participants are being updated
        # We need to construct a temporary 'values' dict with potentially updated fields
        # This is a simplified approach. A more robust way might involve a different model or service-level logic.
        temp_values = {}
        temp_values['split_method'] = values.get('split_method') if values.get('split_method') is not None else values.get('original_split_method') # original_split_method would need to be passed in context
        temp_values['amount'] = values.get('amount') if values.get('amount') is not None else values.get('original_amount')
        temp_values['paid_by'] = values.get('paid_by') if values.get('paid_by') is not None else values.get('original_paid_by')

        if 'paid_by' in temp_values and temp_values['paid_by'] is not None:
             if not any(p.name == temp_values['paid_by'] for p in participants):
                raise ValueError(f"The person who paid ('{temp_values['paid_by']}') must be in the updated participants list.")
        
        # Call the share validation logic
        # This is tricky because original values might be needed if not all fields are updated.
        # For now, we assume if participants are updated, related fields should be consistent or also updated.
        # A full re-validation like in ExpenseBase might be too strict if only description changes, for example.
        # This part highlights the complexity of partial updates with inter-dependent fields.
        # The service layer will need to handle this carefully.
        return participants

class ExpenseInDB(ExpenseBase):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    # calculated_shares: Optional[Dict[str, float]] = Field(None, description="Actual amount each participant owes/contributes for this expense after calculation.")

    class Config:
        json_encoders = {ObjectId: str}
        populate_by_name = True # Allows using '_id' from DB and 'id' in model
        # from_attributes = True # For Pydantic v2, if using ORM mode with objects

class ExpenseResponse(BaseModel):
    id: str
    amount: float
    description: str
    paid_by: str
    split_method: SplitMethodEnum
    participants: List[ParticipantShare]
    date: datetime.datetime
    # calculated_shares: Optional[Dict[str, float]] = None

    @classmethod
    def from_db_model(cls, expense_db: ExpenseInDB) -> 'ExpenseResponse':
        return cls(
            id=str(expense_db.id),
            amount=expense_db.amount,
            description=expense_db.description,
            paid_by=expense_db.paid_by,
            split_method=expense_db.split_method,
            participants=expense_db.participants,
            date=expense_db.date,
            # calculated_shares=expense_db.calculated_shares
        )

class PaginatedExpenseResponse(BaseModel):
    total: int
    expenses: List[ExpenseResponse]
    page: int
    size: int

# For API responses
class GeneralResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Union[ExpenseResponse, List[ExpenseResponse], PaginatedExpenseResponse, Dict, List[Dict]]] = None