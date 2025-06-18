from fastapi import APIRouter, HTTPException, Depends, Query, status, Body
from typing import List, Optional
from bson import ObjectId
from bson.errors import InvalidId

from models.expense_models import (
    ExpenseCreate, ExpenseUpdate, ExpenseResponse, GeneralResponse, PaginatedExpenseResponse,
    PyObjectId
)
from services import expense_service # Will be created later
from database import get_database
from motor.motor_asyncio import AsyncIOMotorDatabase

router = APIRouter()

@router.post("/", response_model=GeneralResponse, status_code=status.HTTP_201_CREATED)
async def create_expense_api(
    expense_data: ExpenseCreate,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    try:
        created_expense = await expense_service.create_expense(db, expense_data)
        return GeneralResponse(
            success=True,
            message="Expense added successfully",
            data=ExpenseResponse.from_db_model(created_expense)
        )
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        # Log the exception e
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred.")

@router.get("/", response_model=GeneralResponse)
async def list_expenses_api(
    db: AsyncIOMotorDatabase = Depends(get_database),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Number of expenses per page")
):
    try:
        skip = (page - 1) * size
        expenses_in_db, total_expenses = await expense_service.get_all_expenses(db, skip, size)
        
        expense_responses = [ExpenseResponse.from_db_model(exp) for exp in expenses_in_db]
        
        paginated_data = PaginatedExpenseResponse(
            total=total_expenses,
            expenses=expense_responses,
            page=page,
            size=size
        )
        return GeneralResponse(
            success=True,
            message="Expenses retrieved successfully",
            data=paginated_data
        )
    except Exception as e:
        # Log the exception e
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred while retrieving expenses.")

@router.get("/{expense_id}", response_model=GeneralResponse)
async def get_expense_api(
    expense_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    try:
        try:
            obj_expense_id = ObjectId(expense_id)
        except InvalidId:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid expense ID format")

        expense = await expense_service.get_expense_by_id(db, obj_expense_id)
        if not expense:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Expense with id {expense_id} not found")
        return GeneralResponse(
            success=True,
            message="Expense retrieved successfully",
            data=ExpenseResponse.from_db_model(expense)
        )
    except HTTPException:
        raise # Re-raise HTTPException to preserve status code and detail
    except Exception as e:
        # Log the exception e
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred.")

@router.put("/{expense_id}", response_model=GeneralResponse)
async def update_expense_api(
    expense_id: str,
    expense_data: ExpenseUpdate,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    try:
        try:
            obj_expense_id = ObjectId(expense_id)
        except InvalidId:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid expense ID format")

        updated_expense = await expense_service.update_expense(db, obj_expense_id, expense_data)
        if not updated_expense:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Expense with id {expense_id} not found or no changes made.")
        return GeneralResponse(
            success=True,
            message="Expense updated successfully",
            data=ExpenseResponse.from_db_model(updated_expense)
        )
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except HTTPException:
        raise
    except Exception as e:
        # Log the exception e
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred.")

@router.delete("/{expense_id}", response_model=GeneralResponse, status_code=status.HTTP_200_OK)
async def delete_expense_api(
    expense_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    try:
        try:
            obj_expense_id = ObjectId(expense_id)
        except InvalidId:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid expense ID format")

        deleted_count = await expense_service.delete_expense(db, obj_expense_id)
        if not deleted_count:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Expense with id {expense_id} not found")
        return GeneralResponse(success=True, message="Expense deleted successfully")
    except HTTPException:
        raise
    except Exception as e:
        # Log the exception e
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred.")