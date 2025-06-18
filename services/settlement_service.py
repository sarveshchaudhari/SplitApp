from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List, Dict, Tuple, Any
from collections import defaultdict
import math

from models.expense_models import ExpenseInDB, SplitMethodEnum
from services.expense_service import get_all_expenses, _calculate_individual_shares # Re-use for consistency

async def calculate_balances(db: AsyncIOMotorDatabase) -> Dict[str, float]:
    """Calculates the net balance for each person across all expenses."""
    balances: Dict[str, float] = defaultdict(float)
    all_expenses_in_db, _ = await get_all_expenses(db, limit=0) # Get all expenses, no pagination needed here

    # all_expenses_in_db is already a list of ExpenseInDB instances
    all_expenses = all_expenses_in_db

    for expense in all_expenses:
        # For each expense, determine how much each participant *should have paid*
        # This uses the same logic as _calculate_individual_shares from expense_service
        # but needs to be adapted to work with ExpenseInDB model if it doesn't store calculated shares.
        # For now, let's assume we re-calculate based on the stored expense details.
        
        # Construct a temporary ExpenseCreate-like object to pass to _calculate_individual_shares
        # This is a bit of a workaround. Ideally, ExpenseInDB might store these, or _calculate_individual_shares
        # would be more generic.
        temp_expense_data_for_calc = {
            "amount": expense.amount,
            "description": expense.description, # Not strictly needed for calc but good for context
            "paid_by": expense.paid_by,
            "split_method": expense.split_method,
            "participants": [p.model_dump() for p in expense.participants],
            "date": expense.date # Not strictly needed
        }
        # The _calculate_individual_shares expects an ExpenseCreate model instance.
        # We need to be careful here. Let's make a simplified version or adapt.
        # For simplicity, let's replicate the core logic here or make _calculate_individual_shares more flexible.

        # --- Replicating share calculation logic (simplified from _calculate_individual_shares) ---
        # This is not ideal due to duplication. A refactor of _calculate_individual_shares to accept
        # a more generic structure or ExpenseInDB would be better.
        
        num_participants = len(expense.participants)
        actual_contributions_for_this_expense: Dict[str, float] = {}

        if expense.split_method == SplitMethodEnum.equal:
            if num_participants == 0: continue # Should be caught by validation
            share_per_person = round(expense.amount / num_participants, 2)
            remainder = round(expense.amount - (share_per_person * num_participants), 2)
            for i, p_share_model in enumerate(expense.participants):
                actual_contributions_for_this_expense[p_share_model.name] = share_per_person
                if i == 0 and remainder != 0:
                    actual_contributions_for_this_expense[p_share_model.name] = round(share_per_person + remainder, 2)
        
        elif expense.split_method == SplitMethodEnum.exact:
            for p_share_model in expense.participants:
                if p_share_model.share is None: continue # Should be caught by validation
                actual_contributions_for_this_expense[p_share_model.name] = round(float(p_share_model.share), 2)
        
        elif expense.split_method == SplitMethodEnum.percentage:
            total_amount = expense.amount
            current_total_calculated = 0.0
            temp_calculated = {}
            for p_share_model in expense.participants:
                if p_share_model.share is None: continue
                individual_share = round(total_amount * (float(p_share_model.share) / 100.0), 2)
                temp_calculated[p_share_model.name] = individual_share
                current_total_calculated += individual_share
            diff = round(total_amount - current_total_calculated, 2)
            if diff != 0 and expense.participants:
                first_participant_name = expense.participants[0].name
                temp_calculated[first_participant_name] = round(temp_calculated.get(first_participant_name, 0) + diff, 2)
            actual_contributions_for_this_expense = temp_calculated

        elif expense.split_method == SplitMethodEnum.shares:
            total_shares_unit = sum(p.share for p in expense.participants if p.share is not None and p.share > 0)
            if total_shares_unit == 0: continue # Avoid division by zero if no valid shares
            
            total_amount = expense.amount
            calculated_sum_for_rounding_check = 0.0
            temp_calculated_shares: Dict[str, float] = {}

            for p_model in expense.participants:
                if p_model.share is None or p_model.share <= 0:
                    # Participants with no share or zero share effectively contribute 0 in this model
                    # Or handle as an error/skip if business logic dictates
                    temp_calculated_shares[p_model.name] = 0.0
                    continue
                
                # Calculate proportional share
                proportional_share = (total_amount * float(p_model.share)) / total_shares_unit
                # Round to 2 decimal places for currency
                individual_share = round(proportional_share, 2)
                temp_calculated_shares[p_model.name] = individual_share
                calculated_sum_for_rounding_check += individual_share

            # Distribute rounding difference to the first participant (or payer, or a defined participant)
            # to ensure the sum of shares equals the total expense amount.
            rounding_diff = round(total_amount - calculated_sum_for_rounding_check, 2)
            if rounding_diff != 0 and expense.participants:
                # Find the first participant who had a non-zero share to adjust
                # Or, more robustly, the participant with the largest share, or the payer if they are a participant.
                # For simplicity, let's try the first participant in the list who has a share.
                adjusted = False
                for p_model in expense.participants:
                    if p_model.share is not None and p_model.share > 0:
                        temp_calculated_shares[p_model.name] = round(temp_calculated_shares.get(p_model.name, 0) + rounding_diff, 2)
                        adjusted = True
                        break
                if not adjusted and expense.participants: # Fallback if no one had shares (edge case)
                    temp_calculated_shares[expense.participants[0].name] = round(temp_calculated_shares.get(expense.participants[0].name, 0) + rounding_diff, 2)

            actual_contributions_for_this_expense = temp_calculated_shares
        # --- End of replicated logic ---

        # Update balances:
        # Person who paid is credited the full amount
        balances[expense.paid_by] += expense.amount

        # Each participant (including the payer if they participated) is debited their share
        for person_name, share_amount in actual_contributions_for_this_expense.items():
            balances[person_name] -= share_amount
    
    # Round final balances to 2 decimal places to avoid floating point inaccuracies
    return {person: round(bal, 2) for person, bal in balances.items()}

async def calculate_simplified_settlements(db: AsyncIOMotorDatabase) -> List[Dict[str, Any]]:
    """Calculates the minimum number of transactions to settle all debts."""
    balances = await calculate_balances(db)
    
    debtors = defaultdict(float) # Who owes money (negative balance)
    creditors = defaultdict(float) # Who is owed money (positive balance)

    for person, balance in balances.items():
        if balance < -1e-9: # Owe money (use tolerance for float comparison)
            debtors[person] = -balance # Store as positive amount owed
        elif balance > 1e-9: # Is owed money
            creditors[person] = balance

    settlements: List[Dict[str, Any]] = []

    # Convert to lists for easier iteration and modification
    # Sort by amount to potentially optimize (e.g., largest debtor pays largest creditor)
    # However, a greedy approach matching any debtor to any creditor works.
    sorted_debtors = sorted(debtors.items(), key=lambda item: item[1], reverse=True)
    sorted_creditors = sorted(creditors.items(), key=lambda item: item[1], reverse=True)

    # Use iterators or manage indices for lists as they are modified
    debtor_idx = 0
    creditor_idx = 0

    while debtor_idx < len(sorted_debtors) and creditor_idx < len(sorted_creditors):
        debtor_name, debtor_amount = sorted_debtors[debtor_idx]
        creditor_name, creditor_amount = sorted_creditors[creditor_idx]

        payment_amount = min(debtor_amount, creditor_amount)

        if payment_amount > 1e-9: # Only record if payment is non-trivial
            settlements.append({
                "payer": debtor_name,
                "receiver": creditor_name,
                "amount": round(payment_amount, 2)
            })

            new_debtor_amount = debtor_amount - payment_amount
            new_creditor_amount = creditor_amount - payment_amount

            # Update amounts (or effectively move to next if one is settled)
            if new_debtor_amount < 1e-9:
                debtor_idx += 1
            else:
                sorted_debtors[debtor_idx] = (debtor_name, new_debtor_amount)
            
            if new_creditor_amount < 1e-9:
                creditor_idx += 1
            else:
                sorted_creditors[creditor_idx] = (creditor_name, new_creditor_amount)
        else:
            # If payment_amount is effectively zero, advance one of the pointers to avoid infinite loop
            # This case should ideally not happen if balances are non-zero and correctly categorized.
            if debtor_amount < creditor_amount:
                debtor_idx +=1
            else:
                creditor_idx +=1

    return settlements