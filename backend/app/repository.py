from typing import List, Dict, Any
from sqlalchemy.orm import Session
from .models import Category, Skill, Level, Plan


def serialize_category(category: Category) -> Dict[str, Any]:
    return {
        "categoryId": category.category_id,
        "categoryName": category.name,
        "stage": category.stage,
        "topSkills": [serialize_skill(skill) for skill in category.skills],
    }


def serialize_skill(skill: Skill) -> Dict[str, Any]:
    return {
        "skillId": skill.skill_id,
        "skillName": skill.name,
        "summary": skill.summary,
        "levels": [serialize_level(level) for level in skill.levels],
    }


def serialize_level(level: Level) -> Dict[str, Any]:
    data = {
        "level": level.level,
        "title": level.title,
        "objective": level.objective,
        "points": level.points or [],
    }
    if level.micro_split:
        data["microSplit"] = level.micro_split
    return data


def load_categories(db: Session) -> List[Category]:
    return db.query(Category).order_by(Category.id.asc()).all()


def upsert_category(db: Session, payload: Dict[str, Any], source: str = "seed", subject: str | None = None) -> Category:
    category_id = payload["categoryId"]
    category = db.query(Category).filter(Category.category_id == category_id).first()
    if not category:
        category = Category(
            category_id=category_id,
            name=payload["categoryName"],
            stage=payload.get("stage", ""),
            source=source,
            subject=subject,
        )
        db.add(category)
        db.flush()
    else:
        category.name = payload["categoryName"]
        category.stage = payload.get("stage", category.stage)

    # Replace skills/levels for simplicity
    category.skills = []
    for skill_payload in payload.get("topSkills", []):
        skill = Skill(
            skill_id=skill_payload["skillId"],
            name=skill_payload["skillName"],
            summary=skill_payload.get("summary", ""),
        )
        for level_payload in skill_payload.get("levels", []):
            level = Level(
                level=level_payload["level"],
                title=level_payload.get("title", ""),
                objective=level_payload.get("objective", ""),
                points=level_payload.get("points", []),
                micro_split=level_payload.get("microSplit"),
            )
            skill.levels.append(level)
        category.skills.append(skill)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def persist_plan(
    db: Session,
    plan_id: str,
    skill_ref: str | None,
    daily_minutes: int,
    days_per_week: int,
    schedule: List[Dict[str, Any]],
    flat_tasks: List[Dict[str, Any]],
) -> Plan:
    plan = Plan(
        plan_id=plan_id,
        skill_ref=skill_ref,
        daily_minutes=daily_minutes,
        days_per_week=days_per_week,
        schedule=schedule,
        flat_tasks=flat_tasks,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan
