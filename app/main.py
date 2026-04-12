from fastapi import FastAPI
from app.api.v1.endpoints import router as stock_router
from app.core.exceptions import AFIPException, afip_exception_handler, global_exception_handler

app = FastAPI(
    title="AFIP Middleware Service",
    description="Microservice to communicate with AFIP Web Services (wgesStockDepositosFiscales)",
    version="1.0.0"
)

# Exception handlers
app.add_exception_handler(AFIPException, afip_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)

# Include routers
app.include_router(stock_router, prefix="/api/v1/stock", tags=["Stock"])

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
