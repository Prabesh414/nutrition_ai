"""Food catalogue search."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.database import FoodItem, get_db
from backend.schemas import FoodResponse

router = APIRouter(prefix="/foods", tags=["foods"])


@router.get("", response_model=list[FoodResponse])
def search_foods(
    query: str | None = Query(None, max_length=100, description="Case-insensitive name fragment"),
    vegetarian: bool | None = Query(None),
    vegan: bool | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Search the catalogue. Public: this is reference data, not user data."""
    statement = db.query(FoodItem)

    if query and query.strip():
        # ilike escapes nothing by default, so neutralise wildcards in user input.
        term = query.strip().lower().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        statement = statement.filter(FoodItem.name.ilike(f"%{term}%", escape="\\"))

    if vegetarian:
        statement = statement.filter(FoodItem.is_vegetarian.is_(True))
    if vegan:
        statement = statement.filter(FoodItem.is_vegan.is_(True))

    items = statement.order_by(FoodItem.name).limit(limit).all()
    return [
        FoodResponse(
            id=item.id,
            name=item.name.title(),
            serving_size=item.serving_size,
            region=item.region,
            calories=item.calories,
            fat=item.fat,
            carbohydrates=item.carbohydrates,
            protein=item.protein,
            fiber=item.fiber,
            sugars=item.sugars,
            is_vegetarian=item.is_vegetarian,
            is_vegan=item.is_vegan,
        )
        for item in items
    ]
