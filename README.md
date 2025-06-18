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

### Prerequisites

- Python 3.8+
- MongoDB Atlas account (or a local MongoDB instance)
- Pip (Python package installer)

### Setup

1.  **Clone the repository (if applicable) or create the project files.**

2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables:**
    Create a `.env` file in the project root directory and add your MongoDB connection string:
    ```env
    MONGODB_URL="your_mongodb_atlas_connection_string_here"
    DATABASE_NAME="split_ease_db"
    ```
    Replace `your_mongodb_atlas_connection_string_here` with your actual MongoDB Atlas connection string. Make sure your IP address is whitelisted in MongoDB Atlas network access settings.

5.  **Run the application:**
    ```bash
    uvicorn main:app --reload
    ```
    The API will be available at `http://127.0.0.1:8000`.

## API Endpoints

Refer to the interactive documentation for detailed information on request/response formats:

-   **Swagger UI**: `http://127.0.0.1:8000/docs`
-   **ReDoc**: `http://127.0.0.1:8000/redoc`
-   **Custom API Guide**: `http://127.0.0.1:8000/api/docs`

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