from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from routers import expenses_router, settlements_router, people_router # Will be created later
from database import connect_to_mongo, close_mongo_connection # Will be created later
from config import settings # Will be created later

app = FastAPI(
    title="SplitEase API",
    description="A backend system to split expenses fairly and calculate settlements.",
    version="1.0.0"
)

@app.on_event("startup")
async def startup_event():
    await connect_to_mongo()

@app.on_event("shutdown")
async def shutdown_event():
    await close_mongo_connection()

# Include routers
app.include_router(expenses_router.router, prefix="/expenses", tags=["Expenses"])
app.include_router(settlements_router.router, prefix="/settlements", tags=["Settlements"])
app.include_router(people_router.router, prefix="/people", tags=["People"])

@app.get("/", tags=["Root"], response_class=HTMLResponse)
async def read_root():
    return """
    <html>
        <head>
            <title>SplitEase API</title>
        </head>
        <body>
            <h1>Welcome to SplitEase API</h1>
            <p>Navigate to <a href="/docs">/docs</a> for API documentation.</p>
            <p>Navigate to <a href="/redoc">/redoc</a> for alternative API documentation.</p>
            <p>Navigate to <a href="/api/docs">/api/docs</a> for custom API usage guide.</p>
        </body>
    </html>
    """

# Custom API docs endpoint
@app.get("/api/docs", tags=["API Documentation"], response_class=HTMLResponse)
async def custom_api_docs():
    # This will be a more detailed HTML page or structured JSON later
    return """
    <html>
        <head>
            <title>SplitEase API Usage Guide</title>
        </head>
        <body>
            <h1>SplitEase API - Usage Guide & Payloads</h1>
            
            <h2>Expense Management</h2>
            <h3><code>POST /expenses</code> - Add new expense</h3>
            <p><strong>Payload Example:</strong></p>
            <pre><code>{
    "amount": 60.00,
    "description": "Dinner at restaurant",
    "paid_by": "Shantanu",
    "split_method": "equal", // "equal", "exact", "percentage", "shares"
    "participants": [
        {"name": "Shantanu", "share": null}, // share is null for 'equal', or exact amount/percentage/share value
        {"name": "Divya", "share": null},
        {"name": "Ramesh", "share": null}
    ]
}</code></pre>
            <p><strong>Notes on <code>participants</code> and <code>split_method</code>:</strong></p>
            <ul>
                <li><strong>equal:</strong> <code>share</code> for each participant should be <code>null</code> or omitted. Amount is divided equally.</li>
                <li><strong>exact:</strong> <code>share</code> for each participant is their exact amount. Sum of shares must equal total amount.</li>
                <li><strong>percentage:</strong> <code>share</code> for each participant is their percentage (e.g., 30 for 30%). Sum of percentages must be 100.</li>
                <li><strong>shares:</strong> <code>share</code> for each participant is their number of shares (e.g., Shantanu: 2, Divya: 1). Amount is divided proportionally.</li>
            </ul>
            <p>The person in <code>paid_by</code> must be one of the <code>participants</code>.</p>

            <h3><code>GET /expenses</code> - List all expenses</h3>
            <p>No payload required.</p>

            <h3><code>PUT /expenses/{id}</code> - Update expense</h3>
            <p>Payload is the same as <code>POST /expenses</code>. The <code>id</code> is the MongoDB ObjectId of the expense.</p>

            <h3><code>DELETE /expenses/{id}</code> - Delete expense</h3>
            <p>No payload required. The <code>id</code> is the MongoDB ObjectId of the expense.</p>

            <h2>Settlement Calculations</h2>
            <h3><code>GET /settlements</code> - Get current settlement summary</h3>
            <p>No payload required.</p>

            <h3><code>GET /balances</code> - Show each person's balance</h3>
            <p>No payload required.</p>

            <h2>People</h2>
            <h3><code>GET /people</code> - List all people</h3>
            <p>No payload required. People are derived from expenses.</p>
            
            <hr/>
            <p><em>Note: For detailed interactive documentation, please visit <a href="/docs">/docs</a> (Swagger UI) or <a href="/redoc">/redoc</a>.</em></p>
        </body>
    </html>
    """

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)