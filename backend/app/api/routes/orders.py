from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import ensure_client_access, get_current_user, require_admin, require_client
from app.db.session import get_db
from app.models.client import Client
from app.models.delivery_method import DeliveryMethod
from app.models.order import OrderStatus
from app.models.order_item import OrderItem
from app.models.user import User
from app.patterns.state.order_state import InvalidOrderStateTransition
from app.patterns.strategy.delivery import (
    CourierDelivery,
    DeliveryStrategy,
    ExpressDelivery,
    PickupDelivery,
)
from app.patterns.strategy.discount import (
    BonusDiscount,
    DiscountStrategy,
    EventDiscount,
    GoldDiscount,
    NoDiscount,
    SocialDiscount,
)
from app.repositories.bouquet_repository import BouquetRepository
from app.repositories.delivery_method_repository import DeliveryMethodRepository
from app.repositories.notification_repository import NotificationRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.salon_repository import SalonRepository
from app.schemas.order import (
    DeliveryType,
    DiscountType,
    OrderCreate,
    OrderRead,
    OrderStatusUpdate,
)
from app.services.order_service import OrderNotFoundError, OrderService

router = APIRouter(prefix="/orders", tags=["orders"])


def _delivery_strategy(delivery_type: DeliveryType) -> DeliveryStrategy:
    strategies: dict[DeliveryType, DeliveryStrategy] = {
        DeliveryType.PICKUP: PickupDelivery(),
        DeliveryType.COURIER: CourierDelivery(),
        DeliveryType.EXPRESS: ExpressDelivery(),
    }
    return strategies[delivery_type]


def _configured_delivery_strategy(method: DeliveryMethod) -> DeliveryStrategy:
    if method.code == DeliveryType.PICKUP.value:
        return PickupDelivery()
    if method.code == DeliveryType.COURIER.value:
        return CourierDelivery(method.base_price)
    if method.code == DeliveryType.EXPRESS.value:
        return ExpressDelivery(method.base_price)

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Unsupported delivery method code: {method.code}",
    )


def _resolve_delivery(
    payload: OrderCreate,
    db: Session,
) -> tuple[DeliveryStrategy, int | None, int | None]:
    method_id: int | None = None
    pickup_salon_id = payload.pickup_salon_id

    if payload.delivery_method_id is not None:
        method = DeliveryMethodRepository(db).get_by_id(payload.delivery_method_id)
        if method is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Delivery method not found",
            )
        if not method.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Delivery method is inactive",
            )
        strategy = _configured_delivery_strategy(method)
        method_id = method.id
    else:
        strategy = _delivery_strategy(payload.delivery_type)

    if strategy.name == DeliveryType.PICKUP.value:
        if method_id is not None and pickup_salon_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Pickup salon is required for pickup",
            )
        if pickup_salon_id is not None:
            salon = SalonRepository(db).get_by_id(pickup_salon_id)
            if salon is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Salon not found",
                )
            if not salon.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Pickup salon is inactive",
                )
    elif pickup_salon_id is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pickup salon can only be selected for pickup delivery",
        )

    return strategy, method_id, pickup_salon_id


def _discount_strategy(payload: OrderCreate) -> DiscountStrategy:
    percent = payload.discount_percent

    if payload.discount_type == DiscountType.NONE:
        return NoDiscount()
    if payload.discount_type == DiscountType.GOLD:
        return GoldDiscount(percent or Decimal("10.00"))
    if payload.discount_type == DiscountType.SOCIAL:
        return SocialDiscount(percent or Decimal("15.00"))
    if payload.discount_type == DiscountType.EVENT:
        if not payload.event_name or not payload.event_name.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Event name is required for event discount",
            )
        return EventDiscount(
            payload.event_name,
            percent or Decimal("10.00"),
        )
    if payload.discount_type == DiscountType.BONUS:
        if payload.bonuses_to_use is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="bonuses_to_use is required for bonus discount",
            )
        return BonusDiscount(payload.bonuses_to_use)

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Unsupported discount type",
    )


def _order_service(db: Session) -> OrderService:
    return OrderService(
        OrderRepository(db),
        notification_repository=NotificationRepository(db),
    )


@router.post("", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
def create_order(
    payload: OrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_client),
):
    ensure_client_access(current_user, payload.client_id)

    if db.get(Client, payload.client_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        )

    bouquet_repository = BouquetRepository(db)
    items: list[OrderItem] = []

    for requested_item in payload.items:
        bouquet = bouquet_repository.get_by_id(requested_item.bouquet_id)
        if bouquet is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Bouquet #{requested_item.bouquet_id} not found",
            )

        items.append(
            OrderItem(
                bouquet_id=bouquet.id,
                quantity=requested_item.quantity,
                unit_price=bouquet.base_price,
            )
        )

    service = _order_service(db)
    delivery_strategy, delivery_method_id, pickup_salon_id = _resolve_delivery(
        payload, db
    )

    try:
        return service.create_order(
            client_id=payload.client_id,
            items=items,
            delivery_strategy=delivery_strategy,
            discount_strategy=_discount_strategy(payload),
            delivery_address=payload.delivery_address,
            delivery_method_id=delivery_method_id,
            pickup_salon_id=pickup_salon_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get("/client/{client_id}", response_model=list[OrderRead])
def list_client_orders(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_client_access(current_user, client_id)

    if db.get(Client, client_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        )

    try:
        return _order_service(db).list_client_orders(client_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get("/{order_id}", response_model=OrderRead)
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        order = _order_service(db).get_order(order_id)
        ensure_client_access(current_user, order.client_id)
        return order
    except OrderNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.patch("/{order_id}/status", response_model=OrderRead)
def update_order_status(
    order_id: int,
    payload: OrderStatusUpdate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    service = _order_service(db)

    transitions = {
        OrderStatus.CONFIRMED: service.confirm_order,
        OrderStatus.PREPARING: service.start_preparing,
        OrderStatus.READY: service.mark_ready,
        OrderStatus.DELIVERING: service.start_delivery,
        OrderStatus.COMPLETED: service.complete_order,
        OrderStatus.CANCELLED: service.cancel_order,
    }

    transition = transitions.get(payload.status)
    if transition is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order status cannot be changed back to created",
        )

    try:
        return transition(order_id)
    except OrderNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except InvalidOrderStateTransition as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
