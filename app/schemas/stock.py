from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class ExportStock(BaseModel):
    item_code: str = Field(..., description="Item code for export")
    quantity: float = Field(..., description="Quantity of the exported item")
    unit_of_measure: str = Field(..., description="Unit of measure for the quantity")

class ImportStock(BaseModel):
    item_code: str = Field(..., description="Item code for import")
    quantity: float = Field(..., description="Quantity of the imported item")
    unit_of_measure: str = Field(..., description="Unit of measure for the quantity")

class EmptyContainer(BaseModel):
    container_id: str = Field(..., description="ID of the empty container")
    container_type: str = Field(..., description="Type of the container")

class StockTransmitRequest(BaseModel):
    transaction_id: str = Field(..., description="Unique transaction ID for tracking")
    customs_code: str = Field(..., description="Customs code")
    operative_place_code: str = Field(..., description="Operative place code")
    stock_date: datetime = Field(..., description="Date of the stock transaction")

    export_stock: List[ExportStock] = Field(default_factory=list, description="List of Export entries")
    import_stock: List[ImportStock] = Field(default_factory=list, description="List of Import entries")
    empty_containers: List[EmptyContainer] = Field(default_factory=list, description="List of Empty Containers")

class StockTransmitResponse(BaseModel):
    transaction_id: str
    status: str
    afip_response: dict
