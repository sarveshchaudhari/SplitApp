# SplitEase API

SplitEase is a backend system designed to help groups of people split expenses fairly and calculate who owes money to whom. It's built with FastAPI and MongoDB.

## Features

- **Expense Tracking**: Add, view, edit, and delete expenses. Supports various splitting methods (equal, exact amount, percentage, shares).
- **Automatic Person Creation**: People are automatically added to the system when they are mentioned in an expense.
- **Settlement Calculations**: Automatically calculates who owes whom to simplify payments.
- **Data Validation**: Ensures data integrity with input validation and clear error messages.
- **API Documentation**: Interactive API documentation available via Swagger UI (`/docs`) and ReDoc (`/redoc`), plus a custom guide at (`/api/docs`).

## Tech Stack

- **FastAPI**: For building the API.
- **MongoDB**: As the database, using Motor for asynchronous access.
- **Pydantic**: For data validation.
- **Uvicorn**: As the ASGI server.

## Getting Started

### How to Install

1. If on windows run the run.bat file
2. If on linux run the following commands:
    ```bash
    python -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    uvicorn main:app --reload
    ```

### Core Endpoints:

**Expense Management**
*   `GET /expenses`: List all expenses.
*   `POST /expenses`: Add a new expense.
*   `PUT /expenses/:id`: Update an existing expense.
*   `DELETE /expenses/:id`: Delete an expense.

**Settlement Calculations**
*   `GET /settlements`: Get the current settlement summary (who owes whom).
*   `GET /balances`: Show each person's overall balance (total owed or to be received).

**People Management**
*   `GET /people`: List all people involved in expenses.

## Example `POST /expenses` Payload

```json
{
    "amount": 100.00,
    "description": "Groceries for the week",
    "paid_by": "Alice",
    "split_method": "equal", // Options: "equal", "exact", "percentage", "shares"
    "participants": [
        {"name": "Alice", "share": null}, // 'share' value depends on 'split_method'
        {"name": "Bob", "share": null},
        {"name": "Charlie", "share": null}
    ]
}
```

**Split Methods & `participants.share`:**

*   **`equal`**: `share` is `null` or omitted. Amount is divided equally.
*   **`exact`**: `share` is the exact amount for that participant. Sum of shares must equal total expense amount.
*   **`percentage`**: `share` is the percentage (e.g., `30` for 30%). Sum of percentages must be `100`.
*   **`shares`**: `share` is the number of shares (e.g., Alice: 2 shares, Bob: 1 share). Amount is divided proportionally.

The person specified in `paid_by` must be included in the `participants` list.

## Project Structure (Planned)

```
/DevDynamics
|-- main.py             # Main FastAPI application
|-- requirements.txt    # Project dependencies
|-- README.md           # This file
|-- .env                # Environment variables (MongoDB URL, etc.) - (You need to create this)
|-- config.py           # Application settings (Pydantic BaseSettings)
|-- database.py         # MongoDB connection and utility functions
|-- models/
|   |-- __init__.py
|   |-- expense_models.py # Pydantic models for expenses
|   |-- user_models.py    # Pydantic models for users/people (if needed beyond simple names)
|-- routers/
|   |-- __init__.py
|   |-- expenses_router.py  # Router for expense-related endpoints
|   |-- settlements_router.py # Router for settlement calculations
|   |-- people_router.py    # Router for listing people
|-- services/
|   |-- __init__.py
|   |-- expense_service.py  # Business logic for expenses
|   |-- settlement_service.py # Logic for calculating settlements
|-- utils/
    |-- __init__.py
    |-- error_handlers.py # Custom error handlers (if needed)
    |-- helpers.py        # General helper functions
```

This structure helps in organizing the code logically as the application grows.