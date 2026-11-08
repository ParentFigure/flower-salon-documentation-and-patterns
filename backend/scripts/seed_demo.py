from decimal import Decimal

import app.models  # noqa: F401 - registers all SQLAlchemy models
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models import Bouquet, BouquetItem, DeliveryMethod, Flower, Occasion, Packaging, Salon


def get_or_create(db, model, defaults=None, **lookup):
    instance = db.query(model).filter_by(**lookup).first()
    if instance is not None:
        return instance, False
    values = dict(defaults or {})
    values.update(lookup)
    instance = model(**values)
    db.add(instance)
    db.flush()
    return instance, True


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        flowers = {}
        flower_data = [
            ("Троянда червона", "95.00", 60),
            ("Троянда біла", "90.00", 50),
            ("Тюльпан рожевий", "65.00", 80),
            ("Еустома біла", "110.00", 35),
            ("Хризантема", "75.00", 45),
            ("Гіпсофіла", "55.00", 70),
        ]
        for name, price, stock in flower_data:
            flower, _ = get_or_create(
                db,
                Flower,
                name=name,
                defaults={"unit_price": Decimal(price), "stock_qty": stock},
            )
            flowers[name] = flower

        occasions = {}
        occasion_data = [
            ("День народження", "birthday", "Яскраві букети для привітання."),
            ("Весілля", "wedding", "Світлі та ніжні композиції."),
            ("День закоханих", "valentine", "Романтичні букети для особливих моментів."),
            ("Співчуття", "funeral", "Стримані композиції."),
        ]
        for name, slug, description in occasion_data:
            occasion, _ = get_or_create(
                db,
                Occasion,
                slug=slug,
                defaults={"name": name, "description": description, "is_active": True},
            )
            occasions[slug] = occasion

        packaging_data = [
            ("Крафт", "Крафтовий папір", "35.00"),
            ("Преміум папір", "Матове декоративне пакування", "70.00"),
            ("Кошик", "Невеликий декоративний кошик", "180.00"),
        ]
        for name, description, price in packaging_data:
            get_or_create(
                db,
                Packaging,
                name=name,
                defaults={"description": description, "price": Decimal(price), "is_active": True},
            )

        salon_data = [
            ("Bloom Center", "м. Львів, просп. Свободи, 10", "+380670000001"),
            ("Bloom South", "м. Львів, вул. Стрийська, 45", "+380670000002"),
        ]
        for name, address, phone in salon_data:
            get_or_create(
                db,
                Salon,
                name=name,
                defaults={"address": address, "phone": phone, "is_active": True},
            )

        delivery_data = [
            ("pickup", "Самовивіз", "0.00", False),
            ("courier", "Кур'єрська доставка", "120.00", True),
            ("express", "Експрес-доставка", "220.00", True),
        ]
        for code, name, price, requires_address in delivery_data:
            get_or_create(
                db,
                DeliveryMethod,
                code=code,
                defaults={
                    "name": name,
                    "base_price": Decimal(price),
                    "requires_address": requires_address,
                    "is_active": True,
                },
            )

        bouquet_data = [
            (
                "Романтичний вечір",
                "Класичний букет із червоних троянд та гіпсофіли.",
                "980.00",
                ["valentine", "birthday"],
                [("Троянда червона", 9), ("Гіпсофіла", 2)],
            ),
            (
                "Ніжний ранок",
                "Легкий букет із рожевих тюльпанів та білої еустоми.",
                "760.00",
                ["birthday", "wedding"],
                [("Тюльпан рожевий", 8), ("Еустома біла", 2)],
            ),
            (
                "Білий акцент",
                "Стримана композиція з білих троянд і хризантем.",
                "890.00",
                ["wedding", "funeral"],
                [("Троянда біла", 7), ("Хризантема", 3)],
            ),
        ]

        for name, description, price, occasion_slugs, composition in bouquet_data:
            bouquet = db.query(Bouquet).filter_by(name=name).first()
            if bouquet is None:
                bouquet = Bouquet(
                    name=name,
                    description=description,
                    base_price=Decimal(price),
                    is_custom=False,
                )
                bouquet.occasions = [occasions[slug] for slug in occasion_slugs]
                db.add(bouquet)
                db.flush()
                for flower_name, quantity in composition:
                    db.add(
                        BouquetItem(
                            bouquet_id=bouquet.id,
                            flower_id=flowers[flower_name].id,
                            quantity=quantity,
                        )
                    )

        db.commit()
        print("Demo data seeded successfully.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
