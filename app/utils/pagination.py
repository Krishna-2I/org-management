from math import ceil
from typing import Literal

from fastapi import Query
from sqlalchemy import func, select

from app.core.exceptions import BadRequestError


class ListParams:
    def __init__(
        self,
        page: int = Query(1, ge=1),
        size: int = Query(20, ge=1, le=100),
        sort_by: str = Query("id"),
        order: Literal["asc", "desc"] = Query("asc"),
    ):
        self.page = page
        self.size = size
        self.sort_by = sort_by
        self.order = order


def paginate(db, stmt, params: ListParams, sort_columns: dict, tiebreaker, scalars: bool = True) -> dict:
    if params.sort_by not in sort_columns:
        raise BadRequestError("Invalid sort field", {"allowed": sorted(sort_columns)})

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0

    column = sort_columns[params.sort_by]
    direction = column.desc() if params.order == "desc" else column.asc()
    stmt = stmt.order_by(direction, tiebreaker)
    stmt = stmt.offset((params.page - 1) * params.size).limit(params.size)

    result = db.execute(stmt)
    items = result.scalars().all() if scalars else result.all()

    return {
        "items": items,
        "total": total,
        "page": params.page,
        "size": params.size,
        "pages": ceil(total / params.size) if total else 0,
    }
