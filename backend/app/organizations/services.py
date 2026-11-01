import re
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.auth.models import User
from app.forms.repositories import FormRepository
from app.organizations.errors import (
    CaseNotFoundError,
    InvalidInviteTokenError,
    OrganizationQuotaExceededError,
)
from app.organizations.models import Organization, OrganizationCase, OrganizationMember
from app.organizations.repositories import CaseRepository, OrganizationRepository
from app.organizations.schemas import (
    CandidateInviteRedemptionResponse,
    CaseCreateRequest,
    CaseRead,
    CaseUpdateRequest,
    OrganizationRead,
)
from app.sessions.models import FormSession
from app.sessions.repositories import SessionRepository
from app.sessions.security import generate_ownership_token, hash_ownership_token
from app.sessions.services import compute_session_progress_percentage

SLUG_CLEAN_REGEX = re.compile(r"[^a-z0-9]+")


class OrganizationService:
    def __init__(self, db: Session):
        self.db = db
        self.org_repo = OrganizationRepository(db)
        self.case_repo = CaseRepository(db)
        self.form_repo = FormRepository(db)
        self.session_repo = SessionRepository(db)

    def ensure_default_organization(
        self, user: User
    ) -> tuple[Organization, OrganizationMember]:
        membership = self.org_repo.get_user_membership(user.id)
        if membership:
            org = self.org_repo.get(membership.organization_id)
            if org:
                return org, membership

        # Generate unique workspace name and slug from user's email
        local_part = user.email.split("@")[0].lower()
        clean_slug = SLUG_CLEAN_REGEX.sub("-", local_part).strip("-") or "workspace"
        unique_slug = f"{clean_slug}-{secrets.token_hex(3)}"

        company_name = f"{local_part.capitalize()} Immigration & Relocation"
        org = self.org_repo.create(
            name=company_name,
            slug=unique_slug,
            billing_plan="agency_sandbox",
            allowed_cases_per_month=3,
        )
        member = self.org_repo.add_member(
            organization_id=org.id,
            user_id=user.id,
            role="owner",
        )
        self.db.commit()

        # Initialize billing subscription record
        from app.billing.services import BillingService

        BillingService(self.db).get_or_create_subscription(org.id)
        return org, member

    def get_user_organization(self, user: User) -> OrganizationRead:
        org, member = self.ensure_default_organization(user)
        return OrganizationRead(
            id=org.id,
            name=org.name,
            slug=org.slug,
            billing_plan=org.billing_plan,
            allowed_cases_per_month=org.allowed_cases_per_month,
            role=member.role,
            created_at=org.created_at,
        )

    def create_case(
        self,
        user: User,
        request: CaseCreateRequest,
    ) -> tuple[CaseRead, str]:
        org, _ = self.ensure_default_organization(user)

        # 1. Enforce monthly case quota
        from app.billing.services import BillingService

        can_create, reason = BillingService(self.db).can_create_case(org.id)
        if not can_create:
            raise OrganizationQuotaExceededError(
                reason
                or f"Monthly limit of {org.allowed_cases_per_month} cases reached. Upgrade your plan to create more cases."
            )

        # 2. Check form version
        version = self.form_repo.get_version(request.form_version_id)
        if not version or version.status != "published":
            raise ValueError(
                f"Published form version with ID '{request.form_version_id}' not found."
            )

        form_name = version.template.name if version.template else "Application"

        # 3. Generate candidate magic invite token & session token hash
        raw_invite_token = generate_ownership_token()
        token_hash = hash_ownership_token(raw_invite_token)

        # 4. Determine output language
        output_lang = (
            version.supported_output_languages[0]
            if version.supported_output_languages
            else version.source_language
        )
        total_required = sum(1 for f in version.fields if f.required)

        # 5. Create underlying candidate FormSession
        expires_at = datetime.now(UTC) + timedelta(days=30)
        session = self.session_repo.create_session(
            form_version_id=version.id,
            user_language=request.user_language,
            source_language=version.source_language,
            output_language=output_lang,
            total_required_fields=total_required,
            expires_at=expires_at,
            ownership_token_hash=token_hash,
            user_id=None,  # Anonymous candidate session bound by invite token
        )
        session.title = f"{request.candidate_name} - {form_name}"

        # 6. Create Case
        case = self.case_repo.create(
            organization_id=org.id,
            created_by_user_id=user.id,
            form_version_id=version.id,
            candidate_name=request.candidate_name,
            candidate_email=request.candidate_email,
            form_session_id=session.id,
            invite_token_hash=token_hash,
            invite_expires_at=expires_at,
            notes=request.notes,
        )
        self.db.commit()

        case_dto = self._map_case_to_dto(case, session, form_name, raw_invite_token)
        return case_dto, raw_invite_token

    def list_cases(self, user: User) -> list[CaseRead]:
        org, _ = self.ensure_default_organization(user)
        cases = self.case_repo.list_by_organization(org.id)

        result: list[CaseRead] = []
        for case in cases:
            session = (
                self.session_repo.get_session_by_id(case.form_session_id)
                if case.form_session_id
                else None
            )
            form_title = (
                session.version.template.name
                if session and session.version and session.version.template
                else None
            )
            # Update case status if session is completed / awaiting final confirmation
            if session:
                if (
                    session.status in ("ready_for_export", "completed")
                    and case.status != "completed"
                ):
                    case.status = "completed"
                    self.case_repo.save(case)
                elif (
                    session.status == "awaiting_final_confirmation"
                    and case.status == "in_progress"
                ):
                    case.status = "awaiting_review"
                    self.case_repo.save(case)
            result.append(self._map_case_to_dto(case, session, form_title))
        self.db.commit()
        return result

    def get_case(self, user: User, case_public_id: str) -> CaseRead:
        org, _ = self.ensure_default_organization(user)
        case = self.case_repo.get_by_public_id(case_public_id)
        if not case or case.organization_id != org.id:
            raise CaseNotFoundError(
                f"Case with public ID '{case_public_id}' not found."
            )

        session = (
            self.session_repo.get_session_by_id(case.form_session_id)
            if case.form_session_id
            else None
        )
        form_title = (
            session.version.template.name
            if session and session.version and session.version.template
            else None
        )
        return self._map_case_to_dto(case, session, form_title)

    def update_case(
        self, user: User, case_public_id: str, request: CaseUpdateRequest
    ) -> CaseRead:
        org, _ = self.ensure_default_organization(user)
        case = self.case_repo.get_by_public_id(case_public_id)
        if not case or case.organization_id != org.id:
            raise CaseNotFoundError(
                f"Case with public ID '{case_public_id}' not found."
            )

        if request.status is not None:
            case.status = request.status
        if request.notes is not None:
            case.notes = request.notes

        self.case_repo.save(case)
        self.db.commit()

        session = (
            self.session_repo.get_session_by_id(case.form_session_id)
            if case.form_session_id
            else None
        )
        form_title = (
            session.version.template.name
            if session and session.version and session.version.template
            else None
        )
        return self._map_case_to_dto(case, session, form_title)

    def redeem_candidate_invite(
        self, raw_token: str
    ) -> CandidateInviteRedemptionResponse:
        token_hash = hash_ownership_token(raw_token)
        case = self.case_repo.get_by_invite_token_hash(token_hash)
        if not case:
            raise InvalidInviteTokenError("Invalid or expired candidate invite link.")

        if case.invite_expires_at and case.invite_expires_at < datetime.now(UTC):
            raise InvalidInviteTokenError(
                "This candidate invite link has expired. Please contact your case manager."
            )

        if not case.form_session_id:
            raise InvalidInviteTokenError(
                "No active form session attached to this case."
            )

        session = self.session_repo.get_session_by_id(case.form_session_id)
        if not session:
            raise InvalidInviteTokenError(
                "Form session attached to this case was not found."
            )

        # Update case status to in_progress if still invited
        if case.status == "invited":
            case.status = "in_progress"
            self.case_repo.save(case)
            self.db.commit()

        form_title = (
            session.version.template.name
            if session.version and session.version.template
            else "Official Application"
        )

        return CandidateInviteRedemptionResponse(
            session_id=session.public_id,
            session_token=raw_token,
            case_public_id=case.public_id,
            candidate_name=case.candidate_name,
            candidate_email=case.candidate_email,
            form_title=form_title,
            form_version_id=session.form_version_id,
            user_language=session.user_language,
            source_language=session.source_language,
            status=case.status,
        )

    def _map_case_to_dto(
        self,
        case: OrganizationCase,
        session: FormSession | None,
        form_title: str | None,
        raw_invite_token: str | None = None,
    ) -> CaseRead:
        total_fields = 0
        answered_fields = 0
        progress_percent = 0
        session_public_id = None

        if session:
            session_public_id = session.public_id
            total_fields = len(session.version.fields) if session.version else 0
            dealt_with = {
                a.field_id
                for a in session.answers
                if a.status in ("confirmed", "skipped")
            }
            answered_fields = len(dealt_with)
            progress_percent = compute_session_progress_percentage(session)

        return CaseRead(
            id=case.id,
            public_id=case.public_id,
            organization_id=case.organization_id,
            candidate_name=case.candidate_name,
            candidate_email=case.candidate_email,
            status=case.status,
            form_version_id=case.form_version_id,
            form_title=form_title,
            form_session_id=case.form_session_id,
            session_public_id=session_public_id,
            notes=case.notes,
            created_at=case.created_at,
            updated_at=case.updated_at,
            invite_token=raw_invite_token,
            total_fields=total_fields,
            answered_fields=answered_fields,
            progress_percent=progress_percent,
        )
