from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.answers.models import FormAnswer


class AnswerRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_answer(self, session_id: str, field_id: str) -> FormAnswer | None:
        stmt = (
            select(FormAnswer)
            .where(FormAnswer.session_id == session_id, FormAnswer.field_id == field_id)
            .options(joinedload(FormAnswer.field))
        )
        return self.db.scalars(stmt).first()

    def get_answer_by_id(self, answer_id: str) -> FormAnswer | None:
        stmt = (
            select(FormAnswer)
            .where(FormAnswer.id == answer_id)
            .options(joinedload(FormAnswer.field))
        )
        return self.db.scalars(stmt).first()

    def save_answer(self, answer: FormAnswer) -> FormAnswer:
        self.db.add(answer)
        self.db.commit()
        self.db.refresh(answer)
        return answer

    def get_answers_for_session(self, session_id: str) -> list[FormAnswer]:
        stmt = (
            select(FormAnswer)
            .where(FormAnswer.session_id == session_id)
            .options(joinedload(FormAnswer.field))
        )
        return list(self.db.scalars(stmt).all())
