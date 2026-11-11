from sqlalchemy import (
    Column,
    String,
    Integer,
    Numeric,
    Boolean,
    ForeignKey
)

from sqlalchemy.orm import relationship
from app.database import Base

class Customer(Base):
    __tablename__ = "customers"
    id = Column(String, primary_key=True)
    activities = relationship(
        "CustomerActivity",
        back_populates="customer"
    )

class CustomerActivity(Base):
    __tablename__ = "customer_activity"
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(
        String,
        ForeignKey("customers.id"),
        nullable=False,
        index=True
    )

    purchase_count = Column(Integer, nullable=False, default=0)
    total_spend = Column(Numeric(12, 2), nullable=False, default=0)

    customer = relationship(
        "Customer",
        back_populates="activities"
    )

class Promotion(Base):
    __tablename__ = "promotions"
    id = Column(String, primary_key=True)
    description = Column(String, nullable=False)
    discount_percent = Column(Integer, nullable=False)
    minimum_purchases = Column(Integer, nullable=False)
    minimum_spend = Column(Numeric(12, 2), nullable=False)
    active = Column(Boolean, nullable=False, default=True)