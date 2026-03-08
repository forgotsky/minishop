from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Any
import os
import time

from sqlalchemy.orm import Session
from .db import Base, engine, get_db, SessionLocal
from .repository import load_categories, serialize_category, upsert_category, persist_plan
from .skills_seed import seed_skills

class Product(BaseModel):
    id: int
    name: str
    price: float


class CartItem(BaseModel):
    id: int
    qty: int = Field(gt=0)


class Address(BaseModel):
    full_name: str = Field(min_length=2)
    phone: str = Field(min_length=5)
    street: str = Field(min_length=3)
    city: str = Field(min_length=2)
    zip: str = Field(min_length=3)


class CheckoutRequest(BaseModel):
    cart_items: List[CartItem] = Field(min_length=1)
    address: Address
    payment_method: str


class CheckoutResponse(BaseModel):
    message: str
    order: dict


app = FastAPI(title="Skill Trainer API", version="1.0.0")

allowed_origins = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "*").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins if allowed_origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PRODUCTS = [
    Product(id=1, name="Wireless Headphones", price=49.99),
    Product(id=2, name="Smart Watch", price=89.0),
    Product(id=3, name="Bluetooth Speaker", price=35.5),
    Product(id=4, name="Backpack", price=28.75),
    Product(id=5, name="Running Shoes", price=64.2),
    Product(id=6, name="Power Bank", price=22.99),
]
DELIVERY_FEE = 5.0


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    # Seed once if empty
    db = SessionLocal()
    try:
        existing = load_categories(db)
        if not existing:
            seed_skills(db)
    finally:
        db.close()


# --- Skill Trainer API data and helpers ---


class TemplateRequest(BaseModel):
    subject: str = Field(min_length=1)


class PlanRequest(BaseModel):
    hour_tasks: List[Dict[str, Any]] = Field(min_length=1)
    daily_minutes: int = Field(ge=20, le=180)
    days_per_week: int = Field(ge=1, le=7)


def normalize_subject(subject: str) -> str:
    txt = subject.lower().strip()
    if "english" in txt or "英语" in txt:
        return "english"
    if "math" in txt or "数学" in txt:
        return "math"
    if "chinese" in txt or "语文" in txt:
        return "chinese"
    if "physics" in txt or "物理" in txt:
        return "physics"
    if "chemistry" in txt or "化学" in txt:
        return "chemistry"
    if "biology" in txt or "生物" in txt:
        return "biology"
    return "generic"


BASE_LEVELS = [
    {
        "level": "L1",
        "title": "基础识别",
        "objective": "建立最小可用词汇与句型。",
        "points": ["核心词汇", "基础句型", "输入-输出对照"],
    },
    {
        "level": "L2",
        "title": "稳定应用",
        "objective": "能在固定场景中稳定使用。",
        "points": ["词块积累", "句型替换", "主题表达"],
    },
    {
        "level": "L3",
        "title": "场景迁移",
        "objective": "可迁移到新场景并完成表达。",
        "points": ["扩展词汇", "表达变体", "理解与复述"],
    },
    {
        "level": "L4",
        "title": "结构化输出",
        "objective": "形成段落级输出能力。",
        "points": ["结构组织", "逻辑连接", "准确性检查"],
    },
    {
        "level": "L5",
        "title": "策略化提升",
        "objective": "可在任务中选择策略解决问题。",
        "points": ["任务拆解", "策略选择", "复盘修正"],
    },
    {
        "level": "L6",
        "title": "综合实战",
        "objective": "在复杂任务中保持质量与效率。",
        "points": ["综合应用", "限时完成", "质量评估"],
    },
]

SUBJECT_TOP_SKILLS = {
    "english": ["词汇与表达", "阅读理解", "写作输出"],
    "math": ["概念与公式", "题型策略", "综合建模"],
    "chinese": ["基础字词", "阅读分析", "写作表达"],
    "physics": ["核心概念", "公式推导", "实验与综合题"],
    "chemistry": ["基础理论", "方程式应用", "实验分析"],
    "biology": ["概念系统", "图表解读", "综合应用"],
}


def build_l1_micro(subject: str, skill_name: str) -> Dict[str, Any]:
    s = normalize_subject(subject)
    if s == "english":
        return {
            "dailyLoad": "40分钟/天",
            "hourlyLoad": "每小时 6词 + 2例句 + 1应用",
            "hourTasks": [
                {
                    "slot": "第1小时",
                    "words": ["book", "class", "teacher", "student", "read", "write"],
                    "wordsText": "book / class / teacher / student / read / write",
                    "sentence": "I read a book in class.",
                    "usage": "用学校场景说2句。",
                },
                {
                    "slot": "第2小时",
                    "words": ["happy", "busy", "early", "late", "always", "often"],
                    "wordsText": "happy / busy / early / late / always / often",
                    "sentence": "I am always early for class.",
                    "usage": "描述你的一天习惯。",
                },
                {
                    "slot": "第3小时",
                    "words": ["go", "come", "eat", "drink", "play", "study"],
                    "wordsText": "go / come / eat / drink / play / study",
                    "sentence": "I study English every day.",
                    "usage": "围绕放学后活动说3句。",
                },
            ],
            "dayTasks": [
                {"day": "Day 1", "target": "学校主题词汇+一般现在时", "deliverable": "掌握6词，输出2句。"},
                {"day": "Day 2", "target": "状态和频率副词", "deliverable": "掌握6词，输出2句。"},
                {"day": "Day 3", "target": "动作动词表达", "deliverable": "掌握6词，输出3句。"},
            ],
        }
    return {
        "dailyLoad": "40分钟/天",
        "hourlyLoad": f"每小时 3概念 + 2例子 + 1应用（{skill_name}）",
        "hourTasks": [
            {
                "slot": "第1小时",
                "words": ["概念A", "概念B", "概念C"],
                "wordsText": "概念A / 概念B / 概念C",
                "sentence": f"这是{skill_name}的基础定义。",
                "usage": "用自己的话复述定义。",
            },
            {
                "slot": "第2小时",
                "words": ["规则A", "规则B", "规则C"],
                "wordsText": "规则A / 规则B / 规则C",
                "sentence": f"在{skill_name}题目中应用规则A。",
                "usage": "做1道对应练习并讲解过程。",
            },
        ],
        "dayTasks": [
            {"day": "Day 1", "target": "基础定义", "deliverable": "复述3个核心概念。"},
            {"day": "Day 2", "target": "规则应用", "deliverable": "完成2道基础题。"},
        ],
    }


def build_levels(subject: str, skill_name: str) -> List[Dict[str, Any]]:
    levels = []
    for item in BASE_LEVELS:
        level = {
            "level": item["level"],
            "title": f"{item['title']}（{skill_name}）",
            "objective": item["objective"],
            "points": item["points"],
        }
        if item["level"] == "L1":
            level["microSplit"] = build_l1_micro(subject, skill_name)
        levels.append(level)
    return levels


def generate_template(subject: str) -> Dict[str, Any]:
    key = normalize_subject(subject)
    top_skills = SUBJECT_TOP_SKILLS.get(key, ["基础能力", "关键方法", "综合应用"])
    skills = []
    for idx, name in enumerate(top_skills):
        skills.append(
            {
                "skillId": f"tpl_{idx + 1}",
                "skillName": name,
                "summary": f"{subject} · {name}",
                "levels": build_levels(subject, name),
            }
        )
    return {
        "categoryId": f"tpl_{int(time.time() * 1000)}",
        "categoryName": f"{subject} 模板",
        "stage": "自动生成",
        "topSkills": skills,
    }


def build_plan(hour_tasks: List[Dict[str, Any]], daily_minutes: int, days_per_week: int) -> Dict[str, Any]:
    def to_minute_task(task: Dict[str, Any], idx: int) -> Dict[str, Any]:
        return {
            "id": f"task_{idx + 1}",
            "title": task.get("slot", f"任务{idx + 1}"),
            "wordsText": task.get("wordsText", ""),
            "sentence": task.get("sentence", ""),
            "usage": task.get("usage", ""),
            "estimateMin": 60,
        }

    def split_task(task: Dict[str, Any], target_min: int, segment_idx: int) -> Dict[str, Any]:
        return {
            "id": f"{task['id']}_seg_{segment_idx + 1}",
            "title": f"{task['title']}（切分{segment_idx + 1}）",
            "wordsText": task.get("wordsText", ""),
            "sentence": task.get("sentence", ""),
            "usage": task.get("usage", ""),
            "estimateMin": target_min,
        }

    tasks = [to_minute_task(task, idx) for idx, task in enumerate(hour_tasks)]
    expanded = []
    for task in tasks:
        if task["estimateMin"] <= daily_minutes:
            expanded.append(task)
            continue
        seg_count = (task["estimateMin"] + daily_minutes - 1) // daily_minutes
        seg_min = (task["estimateMin"] + seg_count - 1) // seg_count
        for i in range(seg_count):
            expanded.append(split_task(task, seg_min, i))

    schedule = []
    for i in range(days_per_week):
        schedule.append({"day": f"Day {i + 1}", "minutes": 0, "tasks": []})

    for idx, task in enumerate(expanded):
        day_index = idx % days_per_week
        schedule[day_index]["tasks"].append(task)
        schedule[day_index]["minutes"] += task["estimateMin"]

    plan_id = f"{int(time.time() * 1000)}"
    flat_tasks = [
        {"day": day["day"], **task}
        for day in schedule
        for task in day["tasks"]
    ]
    return {
        "planId": plan_id,
        "dailyMinutes": daily_minutes,
        "daysPerWeek": days_per_week,
        "totalTasks": len(flat_tasks),
        "schedule": schedule,
        "flatTasks": flat_tasks,
    }


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/products")
def get_products() -> dict:
    return {"products": PRODUCTS}


@app.post("/api/checkout", response_model=CheckoutResponse)
def checkout(payload: CheckoutRequest) -> CheckoutResponse:
    if payload.payment_method not in ["card", "cash"]:
        raise HTTPException(status_code=400, detail="Invalid payment method.")

    subtotal = 0.0
    for item in payload.cart_items:
        product = next((p for p in PRODUCTS if p.id == item.id), None)
        if not product:
            raise HTTPException(status_code=400, detail=f"Product {item.id} not found.")
        subtotal += product.price * item.qty

    total = subtotal + DELIVERY_FEE
    order = {
        "order_id": f"ORD-{int(time.time() * 1000)}",
        "subtotal": round(subtotal, 2),
        "delivery_fee": DELIVERY_FEE,
        "total": round(total, 2),
        "payment_method": payload.payment_method,
        "shipping_city": payload.address.city,
    }

    return CheckoutResponse(
        message="Payment successful. Your order has been placed.",
        order=order,
    )


# --- Skill Trainer API endpoints ---
@app.get("/api/skills")
def list_skills(db: Session = Depends(get_db)) -> dict:
    categories = load_categories(db)
    return {"categories": [serialize_category(c) for c in categories]}


@app.post("/api/template")
def create_template(payload: TemplateRequest, db: Session = Depends(get_db)) -> dict:
    category = generate_template(payload.subject)
    stored = upsert_category(db, category, source="template", subject=payload.subject)
    return {"category": serialize_category(stored)}


@app.post("/api/plan")
def create_plan(payload: PlanRequest, db: Session = Depends(get_db)) -> dict:
    plan = build_plan(payload.hour_tasks, payload.daily_minutes, payload.days_per_week)
    persist_plan(
        db,
        plan_id=plan["planId"],
        skill_ref=None,
        daily_minutes=plan["dailyMinutes"],
        days_per_week=plan["daysPerWeek"],
        schedule=plan["schedule"],
        flat_tasks=plan["flatTasks"],
    )
    return {"plan": plan}
