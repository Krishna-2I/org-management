from sqlalchemy import select

from app.core.exceptions import NotFoundError


def get_in_org(db, model, obj_id: int, org_id: int):
    obj = db.scalar(select(model).where(model.id == obj_id, model.org_id == org_id))
    if obj is None:
        raise NotFoundError(f"{model.__name__} not found")
    return obj
