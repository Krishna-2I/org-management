import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.security import hash_password
from app.db.session import Base, SessionLocal, engine
from app.models.department import Department
from app.models.organization import Organization
from app.models.task import Task, TaskPriority, TaskStatus
from app.models.user import Role, User

DEPARTMENT_NAMES = ["Engineering", "Sales", "Support", "Marketing", "Finance"]
FIRST_NAMES = ["Aarav", "Vihaan", "Ishaan", "Riya", "Ananya", "Diya", "Kabir", "Sara", "Arjun", "Neha"]
LAST_NAMES = ["Sharma", "Verma", "Gupta", "Reddy", "Khan", "Singh", "Mehta", "Rao", "Kapoor", "Nair"]


def random_name() -> str:
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"


def main(user_count: int = 10_000, task_count: int = 30_000) -> None:
    Base.metadata.create_all(engine)
    db = SessionLocal()

    org = Organization(name="Seed Corp", slug="seed-corp")
    db.add(org)
    db.flush()

    owner = User(
        org_id=org.id,
        email="owner@seedcorp.io",
        full_name="Seed Owner",
        role=Role.OWNER,
        hashed_password=hash_password("ownerpass123"),
    )
    db.add(owner)
    db.flush()

    departments = []
    for name in DEPARTMENT_NAMES:
        department = Department(org_id=org.id, name=name)
        db.add(department)
        departments.append(department)
    db.flush()

    managers = []
    for department in departments:
        manager = User(
            org_id=org.id,
            email=f"manager.{department.name.lower()}@seedcorp.io",
            full_name=random_name(),
            role=Role.MANAGER,
            department_id=department.id,
            hashed_password=hash_password("managerpass123"),
        )
        db.add(manager)
        managers.append(manager)
    db.flush()

    employees = []
    for i in range(user_count):
        department = random.choice(departments)
        employee = User(
            org_id=org.id,
            email=f"user{i}@seedcorp.io",
            full_name=random_name(),
            role=Role.EMPLOYEE,
            department_id=department.id,
            manager_id=next(m.id for m in managers if m.department_id == department.id),
            hashed_password=hash_password("employeepass123"),
        )
        db.add(employee)
        employees.append(employee)
        if i % 500 == 0:
            db.flush()
    db.flush()

    statuses = list(TaskStatus)
    priorities = list(TaskPriority)
    for i in range(task_count):
        task = Task(
            org_id=org.id,
            title=f"Task {i}",
            status=random.choice(statuses),
            priority=random.choice(priorities),
            assignee_id=random.choice(employees).id,
            created_by_id=random.choice(managers).id,
        )
        db.add(task)
        if i % 1000 == 0:
            db.flush()

    db.commit()
    db.close()
    print(f"Seeded org 'seed-corp' with {user_count} users and {task_count} tasks.")
    print("Login as owner@seedcorp.io / ownerpass123")


if __name__ == "__main__":
    main()
