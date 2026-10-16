"""Spec: booking-domain. Each test runs against the real migrated schema and is rolled back.

"Database rejects" scenarios insert with raw SQL where the ORM would stop the value first
(e.g. enum validation), so the test proves the *database* constraint, not just Python.
"""

import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.enums import Service, SizeClass, Species, Vaccine
from app.models import (
    BookingRequest,
    Facility,
    Kennel,
    Owner,
    Pet,
    Reservation,
    VaccineRecord,
    VaccineRule,
)

spec = pytest.mark.spec


async def make_facility(session) -> Facility:
    facility = Facility(name="Test Lodge", timezone="America/Chicago")
    session.add(facility)
    await session.flush()
    return facility


async def make_owner(session) -> Owner:
    owner = Owner(full_name="Test Owner", email=f"owner-{uuid.uuid4()}@example.test")
    session.add(owner)
    await session.flush()
    return owner


async def make_pet(session, species=Species.DOG, weight="40", owner=None) -> Pet:
    owner = owner or await make_owner(session)
    pet = Pet(owner_id=owner.id, name="Biscuit", species=species, weight_lb=Decimal(weight))
    session.add(pet)
    await session.flush()
    return pet


async def second_pet(session, pet) -> Pet:
    """Another dog of the same owner, for reservations that must not be the same pet's."""
    other = Pet(owner_id=pet.owner_id, name="Pepper", species=Species.DOG, weight_lb=Decimal(40))
    session.add(other)
    await session.flush()
    return other


async def make_kennel(session, facility, name="K1", size=SizeClass.MEDIUM) -> Kennel:
    kennel = Kennel(facility_id=facility.id, name=name, size_class=size)
    session.add(kennel)
    await session.flush()
    return kennel


async def reserve(session, kennel, pet, start, end, booking_request_id=None) -> Reservation:
    reservation = Reservation(
        kennel_id=kennel.id,
        pet_id=pet.id,
        start_date=start,
        end_date=end,
        booking_request_id=booking_request_id,
    )
    session.add(reservation)
    await session.flush()
    return reservation


# --- Pets belong to an owner and have a species ---------------------------------------


@spec("booking-domain", "Pets belong to an owner and have a species")
async def test_pet_without_owner_is_rejected(session):
    session.add(Pet(owner_id=None, name="Stray", species=Species.DOG, weight_lb=Decimal(30)))

    with pytest.raises(IntegrityError):
        await session.flush()


@spec("booking-domain", "Pets belong to an owner and have a species")
async def test_unsupported_species_is_rejected(session):
    owner = await make_owner(session)

    with pytest.raises(IntegrityError, match="ck_pets_species"):
        await session.execute(
            text(
                "INSERT INTO pets (owner_id, name, species, weight_lb) "
                "VALUES (:owner, 'Thumper', 'rabbit', 4)"
            ),
            {"owner": owner.id},
        )


@spec("booking-domain", "Pets belong to an owner and have a species")
async def test_non_positive_weight_is_rejected(session):
    with pytest.raises(IntegrityError, match="ck_pets_weight_positive"):
        await make_pet(session, weight="0")


# --- Size class is derived from species and weight ------------------------------------


@spec("booking-domain", "Size class is derived from species and weight")
@pytest.mark.parametrize(
    ("species", "weight", "expected"),
    [
        (Species.CAT, "14", SizeClass.CAT),
        (Species.CAT, "120", SizeClass.CAT),
        (Species.DOG, "19.9", SizeClass.SMALL),
        (Species.DOG, "20", SizeClass.MEDIUM),
        (Species.DOG, "49.9", SizeClass.MEDIUM),
        (Species.DOG, "50", SizeClass.LARGE),
        (Species.DOG, "89.9", SizeClass.LARGE),
        (Species.DOG, "90", SizeClass.XLARGE),
    ],
)
async def test_size_class_boundaries(session, species, weight, expected):
    pet = await make_pet(session, species=species, weight=weight)

    assert pet.size_class == expected


@spec("booking-domain", "Size class is derived from species and weight")
async def test_weight_change_moves_the_class(session):
    pet = await make_pet(session, weight="45")
    assert pet.size_class == SizeClass.MEDIUM

    pet.weight_lb = Decimal(52)
    await session.flush()

    assert pet.size_class == SizeClass.LARGE


@spec("booking-domain", "Size class is derived from species and weight")
async def test_size_class_cannot_be_written_directly(session):
    owner = await make_owner(session)

    with pytest.raises(DBAPIError, match="size_class"):
        await session.execute(
            text(
                "INSERT INTO pets (owner_id, name, species, weight_lb, size_class) "
                "VALUES (:owner, 'Biscuit', 'dog', 80, 'small')"
            ),
            {"owner": owner.id},
        )


# --- Facilities have a time zone ------------------------------------------------------


@spec("booking-domain", "Facilities have a time zone")
def test_invalid_time_zone_is_rejected():
    with pytest.raises(ValueError, match="Mars/Olympus"):
        Facility(name="Red Planet Kennels", timezone="Mars/Olympus")


@spec("booking-domain", "Facilities have a time zone")
def test_valid_time_zone_is_accepted():
    assert Facility(name="Test Lodge", timezone="America/Chicago").timezone == "America/Chicago"


# --- Vaccine rules are defined per facility, service, and species ---------------------


@spec("booking-domain", "Vaccine rules are defined per facility, service, and species")
async def test_rules_differ_per_service(session):
    facility = await make_facility(session)
    session.add_all(
        [
            VaccineRule(
                facility_id=facility.id,
                service=Service.DAYCARE,
                species=Species.DOG,
                vaccine=Vaccine.BORDETELLA,
            ),
            VaccineRule(
                facility_id=facility.id,
                service=Service.GROOMING,
                species=Species.DOG,
                vaccine=Vaccine.RABIES,
            ),
        ]
    )
    await session.flush()

    grooming = await session.scalars(
        select(VaccineRule.vaccine).where(
            VaccineRule.facility_id == facility.id,
            VaccineRule.service == Service.GROOMING,
            VaccineRule.species == Species.DOG,
        )
    )

    assert list(grooming) == [Vaccine.RABIES]


@spec("booking-domain", "Vaccine rules are defined per facility, service, and species")
async def test_duplicate_rule_is_rejected(session):
    facility = await make_facility(session)
    for _ in range(2):
        session.add(
            VaccineRule(
                facility_id=facility.id,
                service=Service.BOARDING,
                species=Species.DOG,
                vaccine=Vaccine.RABIES,
            )
        )

    with pytest.raises(IntegrityError, match="uq_vaccine_rules"):
        await session.flush()


# --- Vaccine records store dates, not flags -------------------------------------------


@spec("booking-domain", "Vaccine records store dates, not flags")
async def test_record_without_expiry_is_kept_as_unknown(session):
    pet = await make_pet(session)
    record = VaccineRecord(
        pet_id=pet.id, vaccine=Vaccine.RABIES, administered_on=date(2026, 1, 10), expires_on=None
    )
    session.add(record)
    await session.flush()

    stored = await session.scalar(
        select(VaccineRecord.expires_on).where(VaccineRecord.id == record.id)
    )

    assert stored is None


@spec("booking-domain", "Vaccine records store dates, not flags")
async def test_expiry_before_administration_is_rejected(session):
    pet = await make_pet(session)
    session.add(
        VaccineRecord(
            pet_id=pet.id,
            vaccine=Vaccine.RABIES,
            administered_on=date(2026, 1, 10),
            expires_on=date(2025, 1, 10),
        )
    )

    with pytest.raises(IntegrityError, match="ck_vaccine_records_expiry_not_before_given"):
        await session.flush()


# --- Kennels have a size class --------------------------------------------------------


@spec("booking-domain", "Kennels have a size class")
async def test_kennel_with_unknown_size_class_is_rejected(session):
    facility = await make_facility(session)

    with pytest.raises(IntegrityError, match="ck_kennels_size_class"):
        await session.execute(
            text("INSERT INTO kennels (facility_id, name, size_class) VALUES (:f, 'K9', 'huge')"),
            {"f": facility.id},
        )


# --- Reservations never overlap on the same kennel ------------------------------------


@spec("booking-domain", "Reservations never overlap on the same kennel")
async def test_overlapping_reservation_is_rejected(session):
    facility = await make_facility(session)
    kennel = await make_kennel(session, facility)
    pet = await make_pet(session)
    await reserve(session, kennel, pet, date(2027, 3, 6), date(2027, 3, 9))

    with pytest.raises(IntegrityError, match="ex_reservations_no_overlapping_stays"):
        await reserve(
            session, kennel, await second_pet(session, pet), date(2027, 3, 8), date(2027, 3, 10)
        )


@spec("booking-domain", "Reservations never overlap on the same kennel")
async def test_back_to_back_reservations_are_allowed(session):
    facility = await make_facility(session)
    kennel = await make_kennel(session, facility)
    pet = await make_pet(session)

    await reserve(session, kennel, pet, date(2027, 3, 6), date(2027, 3, 9))
    await reserve(session, kennel, pet, date(2027, 3, 9), date(2027, 3, 12))


@spec("booking-domain", "Reservations never overlap on the same kennel")
async def test_same_dates_on_different_kennels_are_allowed(session):
    facility = await make_facility(session)
    k1 = await make_kennel(session, facility, name="K1")
    k2 = await make_kennel(session, facility, name="K2")
    pet = await make_pet(session)
    other = await second_pet(session, pet)  # one pet holds one kennel per night

    await reserve(session, k1, pet, date(2027, 3, 6), date(2027, 3, 9))
    await reserve(session, k2, other, date(2027, 3, 6), date(2027, 3, 9))


@spec("booking-domain", "Reservations never overlap on the same kennel")
async def test_zero_night_reservation_is_rejected(session):
    facility = await make_facility(session)
    kennel = await make_kennel(session, facility)
    pet = await make_pet(session)

    with pytest.raises(IntegrityError, match="ck_reservations_at_least_one_night"):
        await reserve(session, kennel, pet, date(2027, 3, 6), date(2027, 3, 6))


# --- A booking request creates at most one reservation --------------------------------


@spec("booking-domain", "A booking request creates at most one reservation")
async def test_second_reservation_for_same_request_is_rejected(session):
    facility = await make_facility(session)
    k1 = await make_kennel(session, facility, name="K1")
    k2 = await make_kennel(session, facility, name="K2")
    owner = await make_owner(session)
    pet = await make_pet(session, owner=owner)
    request = BookingRequest(facility_id=facility.id, owner_id=owner.id, raw_message="Board?")
    session.add(request)
    await session.flush()
    request_id = request.id
    await reserve(session, k1, pet, date(2027, 3, 6), date(2027, 3, 9), request_id)

    with pytest.raises(IntegrityError, match="uq_reservations_booking_request_id"):
        await reserve(session, k2, pet, date(2027, 4, 6), date(2027, 4, 9), request_id)
