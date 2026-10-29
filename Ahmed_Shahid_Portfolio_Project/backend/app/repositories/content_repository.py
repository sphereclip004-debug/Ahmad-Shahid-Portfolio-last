"""Database access helpers for portfolio content records."""
from sqlalchemy.orm import Session
from app.models import PortfolioItem


def list_items(db: Session, kind: str, *, include_unpublished: bool = True, approved_only: bool = False) -> list[PortfolioItem]:
    query = db.query(PortfolioItem).filter(PortfolioItem.kind == kind)
    if not include_unpublished:
        query = query.filter(PortfolioItem.published.is_(True))
    if approved_only:
        query = query.filter(PortfolioItem.moderation_status == "approved")
    return query.order_by(PortfolioItem.sort_order.asc(), PortfolioItem.id.asc()).all()


def get_item(db: Session, kind: str, item_id: int) -> PortfolioItem | None:
    return db.query(PortfolioItem).filter_by(kind=kind, id=item_id).first()


def create_item(db: Session, *, kind: str, data: dict, sort_order: int, published: bool, moderation_status: str) -> PortfolioItem:
    item = PortfolioItem(kind=kind, data=data, sort_order=sort_order, published=published, moderation_status=moderation_status)
    db.add(item)
    db.flush()
    return item
