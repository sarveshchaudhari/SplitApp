from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from typing import List, Tuple, Dict, Any, Optional
import datetime

from models.expense_models import (
    ExpenseCreate, ExpenseUpdate, ExpenseInDB, SplitMethodEnum, ParticipantShare
)

EXPENSE_COLLECTION = "expenses"

async def _calculate_individual_shares(expense_data: ExpenseCreate) -> Dict[str, float]:
    """Helper function to calculate actual monetary share for each participant based on split method."""
    calculated_shares: Dict[str, float] = {}
    num_participants = len(expense_data.participants)
    
    if expense_data.split_method == SplitMethodEnum.equal:
        if num_participants == 0:
            raise ValueError("Cannot split equally among zero participants.")
        share_per_person = round(expense_data.amount / num_participants, 2)
        # Distribute any rounding remainder to the first participant or payer
        remainder = round(expense_data.amount - (share_per_person * num_participants), 2)
        
        for i, p_share in enumerate(expense_data.participants):
            calculated_shares[p_share.name] = share_per_person
            if i == 0 and remainder != 0: # Add remainder to the first person
                 calculated_shares[p_share.name] = round(share_per_person + remainder, 2)

    elif expense_data.split_method == SplitMethodEnum.exact:
        for p_share in expense_data.participants:
            if p_share.share is None:
                raise ValueError(f"Exact share not provided for participant {p_share.name}.")
            calculated_shares[p_share.name] = round(float(p_share.share), 2)
        # Validation that sum of shares equals amount is in Pydantic model

    elif expense_data.split_method == SplitMethodEnum.percentage:
        total_amount = expense_data.amount
        current_total_calculated = 0.0
        for i, p_share in enumerate(expense_data.participants):
            if p_share.share is None:
                raise ValueError(f"Percentage share not provided for participant {p_share.name}.")
            # Calculate share for this participant
            individual_share = round(total_amount * (float(p_share.share) / 100.0), 2)
            calculated_shares[p_share.name] = individual_share
            current_total_calculated += individual_share
        
        # Distribute rounding differences if any
        # This ensures the sum of calculated shares matches the total amount
        diff = round(total_amount - current_total_calculated, 2)
        if diff != 0 and expense_data.participants: # if there's a difference and participants exist
            # Add the difference to the first participant's share
            # A more sophisticated distribution could be to the payer or largest share holder
            first_participant_name = expense_data.participants[0].name
            calculated_shares[first_participant_name] = round(calculated_shares[first_participant_name] + diff, 2)

    elif expense_data.split_method == SplitMethodEnum.shares:
        total_shares_unit = sum(p.share for p in expense_data.participants if p.share is not None)
        if total_shares_unit == 0:
            raise ValueError("Total shares cannot be zero for 'shares' split method.")
        total_amount = expense_data.amount
        current_total_calculated = 0.0
        # Calculate shares for all but the last participant
        for i in range(len(expense_data.participants) -1):
            p_share = expense_data.participants[i]
            individual_share = round(total_amount * (float(p_share.share) / total_shares_unit), 2)
            calculated_shares[p_share.name] = individual_share
            current_total_calculated += individual_share
        # Assign the remainder to the last participant to ensure sum matches total amount
        last_participant = expense_data.participants[-1]
        calculated_shares[last_participant.name] = round(total_amount - current_total_calculated, 2)

    else:
        raise ValueError(f"Unsupported split method: {expense_data.split_method}")

    # Final check: sum of calculated shares should match total amount
    if abs(sum(calculated_shares.values()) - expense_data.amount) > 1e-5: # tolerance for float sums
        # This indicates a potential logic error in share calculation or distribution of remainder
        # For now, we'll raise an error, but could also try to adjust further
        # print(f"DEBUG: Calculated shares sum {sum(calculated_shares.values())} vs amount {expense_data.amount}")
        # Re-distribute any tiny remainder to the payer to ensure sum matches
        payer_name = expense_data.paid_by
        if payer_name in calculated_shares:
            diff_to_distribute = round(expense_data.amount - sum(calculated_shares.values()), 2)
            if diff_to_distribute != 0:
                 calculated_shares[payer_name] = round(calculated_shares[payer_name] + diff_to_distribute, 2)
        # If sum is still off, then it's a bigger issue
        if abs(sum(calculated_shares.values()) - expense_data.amount) > 1e-5:
            raise ValueError("Internal error: Calculated shares sum does not match total expense amount after distribution.")

    return calculated_shares

async def create_expense(db: AsyncIOMotorDatabase, expense_data: ExpenseCreate) -> ExpenseInDB:
    # Pydantic model already validates structure and basic rules (e.g., paid_by in participants)
    # The _calculate_individual_shares can be called here if we decide to store them directly
    # For now, settlements will calculate them on the fly. 
    # However, for auditing or display, storing them might be useful.
    # Let's assume for now we don't store calculated_shares directly on the expense document
    # to keep the settlement logic more dynamic.

    expense_dict = expense_data.model_dump(exclude_unset=True)
    expense_dict["date"] = expense_data.date # Ensure datetime object is used
    
    result = await db[EXPENSE_COLLECTION].insert_one(expense_dict)
    created_expense = await db[EXPENSE_COLLECTION].find_one({"_id": result.inserted_id})
    if not created_expense:
        raise ValueError("Failed to create expense in database.") # Should not happen
    return ExpenseInDB(**created_expense)

async def get_all_expenses(db: AsyncIOMotorDatabase, skip: int = 0, limit: int = 10) -> Tuple[List[ExpenseInDB], int]:
    total_expenses = await db[EXPENSE_COLLECTION].count_documents({})
    cursor = db[EXPENSE_COLLECTION].find().skip(skip).limit(limit).sort("date", -1) # Sort by date descending
    expenses = await cursor.to_list(length=limit)
    return [ExpenseInDB(**exp) for exp in expenses], total_expenses

async def get_expense_by_id(db: AsyncIOMotorDatabase, expense_id: ObjectId) -> Optional[ExpenseInDB]:
    expense = await db[EXPENSE_COLLECTION].find_one({"_id": expense_id})
    if expense:
        return ExpenseInDB(**expense)
    return None

async def update_expense(db: AsyncIOMotorDatabase, expense_id: ObjectId, expense_data: ExpenseUpdate) -> Optional[ExpenseInDB]:
    existing_expense = await get_expense_by_id(db, expense_id)
    if not existing_expense:
        return None

    update_data = expense_data.model_dump(exclude_unset=True)

    # If critical fields for share calculation are updated, we might need to re-validate/re-calculate.
    # Pydantic models for ExpenseUpdate should handle validation of provided fields.
    # The main concern is consistency if, e.g., amount changes but participant shares don't, or vice-versa.
    # The ExpenseUpdate model's validators attempt to catch some of this, but complex cases might need service logic.
    
    # For example, if 'amount', 'split_method', or 'participants' change, ensure consistency.
    # We can construct a temporary ExpenseCreate-like object from existing + update_data to re-validate.
    # This is a simplified approach; a full merge and re-validation can be complex.
    if any(key in update_data for key in ['amount', 'split_method', 'participants']):
        # Create a merged view of the expense for validation
        merged_data_dict = existing_expense.model_dump()
        merged_data_dict.update(update_data)
        try:
            # Validate the merged data as if it were a new expense creation
            # This requires careful handling of participant shares if they are not being updated explicitly
            # For now, we rely on the ExpenseUpdate model's validators and the inherent validation in ExpenseBase
            # when Pydantic tries to create the model instance from merged_data_dict.
            # This is a point that might need refinement for robustness.
            ExpenseCreate(**merged_data_dict) # This will run validators on the combined data
        except ValueError as ve:
            raise ValueError(f"Validation error during update: {ve}")

    if not update_data:
        return existing_expense # No actual changes

    result = await db[EXPENSE_COLLECTION].update_one(
        {"_id": expense_id},
        {"$set": update_data}
    )

    if result.modified_count == 1:
        updated_expense_doc = await db[EXPENSE_COLLECTION].find_one({"_id": expense_id})
        return ExpenseInDB(**updated_expense_doc) if updated_expense_doc else None
    elif result.matched_count == 1 and result.modified_count == 0:
        # Matched but no changes made (e.g. update data was same as existing)
        return existing_expense
    return None # Should not happen if matched_count was 0, as existing_expense check would fail

async def delete_expense(db: AsyncIOMotorDatabase, expense_id: ObjectId) -> int:
    result = await db[EXPENSE_COLLECTION].delete_one({"_id": expense_id})
    return result.deleted_count

async def get_all_people(db: AsyncIOMotorDatabase) -> List[str]:
    """Retrieves a list of all unique people names from all expenses."""
    # This can be done by aggregating distinct names from 'paid_by' and 'participants.name'
    # Using an aggregation pipeline for more robust extraction
    pipeline = [
        {
            "$project": {
                "people": {
                    "$concatArrays": [
                        ["$paid_by"],
                        {
                            "$map": {
                                "input": "$participants",
                                "as": "participant",
                                "in": "$$participant.name"
                            }
                        }
                    ]
                }
            }
        },
        {
            "$unwind": "$people"
        },
        {
            "$group": {
                "_id": "$people"
            }
        },
        {
            "$sort": {"_id": 1} # Sort names alphabetically
        },
        {
            "$project": {
                "_id": 0,
                "name": "$_id"
            }
        }
    ]
    
    cursor = db[EXPENSE_COLLECTION].aggregate(pipeline)
    people_docs = await cursor.to_list(length=None) # Get all results
    return [doc['name'] for doc in people_docs if doc['name'] is not None]