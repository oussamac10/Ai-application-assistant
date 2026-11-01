from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.organizations.models import Organization, OrganizationCase, OrganizationMember


class OrganizationRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, organization_id: str) -> Organization | None:
        stmt = select(Organization).where(Organization.id == organization_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_slug(self, slug: str) -> Organization | None:
        stmt = select(Organization).where(Organization.slug == slug)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_user_membership(self, user_id: str) -> OrganizationMember | None:
        stmt = (
            select(OrganizationMember)
            .where(OrganizationMember.user_id == user_id)
            .order_by(OrganizationMember.created_at.asc())
        )
        return self.db.execute(stmt).scalars().first()

    def create(
        self,
        name: str,
        slug: str,
        billing_plan: str = "agency_pro",
        allowed_cases_per_month: int = 50,
    ) -> Organization:
        org = Organization(
            name=name,
            slug=slug,
            billing_plan=billing_plan,
            allowed_cases_per_month=allowed_cases_per_month,
        )
        self.db.add(org)
        self.db.flush()
        return org

    def save(self, org: Organization) -> Organization:
        self.db.add(org)
        self.db.flush()
        return org

    def add_member(
        self, organization_id: str, user_id: str, role: str = "case_manager"
    ) -> OrganizationMember:
        member = OrganizationMember(
            organization_id=organization_id,
            user_id=user_id,
            role=role,
        )
        self.db.add(member)
        self.db.flush()
        return member

    def list_members(self, organization_id: str) -> list[OrganizationMember]:
        stmt = (
            select(OrganizationMember)
            .options(joinedload(OrganizationMember.user))
            .where(OrganizationMember.organization_id == organization_id)
            .order_by(OrganizationMember.created_at.asc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def get_member(
        self, organization_id: str, user_id: str
    ) -> OrganizationMember | None:
        stmt = (
            select(OrganizationMember)
            .options(joinedload(OrganizationMember.user))
            .where(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.user_id == user_id,
            )
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def count_owners(self, organization_id: str) -> int:
        stmt = select(func.count(OrganizationMember.id)).where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.role == "owner",
        )
        return int(self.db.execute(stmt).scalar() or 0)

    def remove_member(self, organization_id: str, user_id: str) -> bool:
        member = self.get_member(organization_id, user_id)
        if member:
            self.db.delete(member)
            self.db.flush()
            return True
        return False


class CaseRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        organization_id: str,
        created_by_user_id: str,
        form_version_id: str,
        candidate_name: str,
        candidate_email: str,
        form_session_id: str | None = None,
        invite_token_hash: str | None = None,
        invite_expires_at: datetime | None = None,
        notes: str | None = None,
    ) -> OrganizationCase:
        case = OrganizationCase(
            organization_id=organization_id,
            created_by_user_id=created_by_user_id,
            form_version_id=form_version_id,
            candidate_name=candidate_name,
            candidate_email=candidate_email,
            form_session_id=form_session_id,
            invite_token_hash=invite_token_hash,
            invite_expires_at=invite_expires_at,
            notes=notes,
            status="invited",
        )
        self.db.add(case)
        self.db.flush()
        return case

    def get_by_public_id(self, public_id: str) -> OrganizationCase | None:
        stmt = select(OrganizationCase).where(OrganizationCase.public_id == public_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_id(self, case_id: str) -> OrganizationCase | None:
        stmt = select(OrganizationCase).where(OrganizationCase.id == case_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_invite_token_hash(self, token_hash: str) -> OrganizationCase | None:
        stmt = select(OrganizationCase).where(
            OrganizationCase.invite_token_hash == token_hash
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def list_by_organization(self, organization_id: str) -> list[OrganizationCase]:
        stmt = (
            select(OrganizationCase)
            .where(OrganizationCase.organization_id == organization_id)
            .order_by(OrganizationCase.created_at.desc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def count_cases_this_month(self, organization_id: str) -> int:
        now = datetime.now(UTC)
        first_of_month = datetime(now.year, now.month, 1, tzinfo=UTC)
        stmt = select(func.count(OrganizationCase.id)).where(
            OrganizationCase.organization_id == organization_id,
            OrganizationCase.created_at >= first_of_month,
        )
        return int(self.db.execute(stmt).scalar() or 0)

    def save(self, case: OrganizationCase) -> OrganizationCase:
        self.db.add(case)
        self.db.flush()
        return case
