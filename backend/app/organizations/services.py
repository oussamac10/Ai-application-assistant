import re
import secrets
import tempfile
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.auth.models import User
from app.auth.repositories import UserRepository
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
    OrganizationMemberInvite,
    OrganizationMemberRead,
    OrganizationMemberRoleUpdate,
    OrganizationProfileUpdate,
    OrganizationRead,
    OrganizationVerificationRequest,
)
from app.sessions.repositories import SessionRepository
from app.sessions.security import generate_ownership_token, hash_ownership_token
from app.sessions.services import compute_session_progress_percentage
from app.storage.factory import get_storage_provider

SLUG_CLEAN_REGEX = re.compile(r"[^a-z0-9]+")


class OrganizationService:
    def __init__(self, db: Session):
        self.db = db
        self.org_repo = OrganizationRepository(db)
        self.case_repo = CaseRepository(db)
        self.form_repo = FormRepository(db)
        self.session_repo = SessionRepository(db)
        self.user_repo = UserRepository(db)

    def create_organization_for_user(
        self,
        user: User,
        name: str,
        organization_type: str = "government",
        official_website_url: str | None = None,
    ) -> tuple[Organization, OrganizationMember]:
        clean_name = name.strip() if name and name.strip() else (
            "Official Public Administration" if organization_type == "government" else "Private Consulting Partners"
        )
        local_slug = SLUG_CLEAN_REGEX.sub("-", clean_name.lower()).strip("-") or "org"
        unique_slug = f"{local_slug}-{secrets.token_hex(3)}"

        billing_plan = "enterprise" if organization_type == "government" else "agency_pro"
        allowed_cases = 100 if organization_type == "government" else 50
        org = self.org_repo.create(
            name=clean_name,
            slug=unique_slug,
            billing_plan=billing_plan,
            allowed_cases_per_month=allowed_cases,
            organization_type=organization_type,
            official_website_url=official_website_url.strip() if official_website_url else None,
        )
        member = self.org_repo.add_member(
            organization_id=org.id,
            user_id=user.id,
            role="owner",
        )
        self.db.commit()

        from app.billing.services import BillingService

        billing_service = BillingService(self.db)
        billing_service.get_or_create_subscription(org.id)

        return org, member

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

        company_name = f"{local_part.capitalize()} Administration"
        org = self.org_repo.create(
            name=company_name,
            slug=unique_slug,
            billing_plan="agency_sandbox",
            allowed_cases_per_month=3,
            organization_type="government",
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

    def _to_org_read(self, org: Organization, member_role: str) -> OrganizationRead:
        return OrganizationRead(
            id=org.id,
            name=org.name,
            slug=org.slug,
            billing_plan=org.billing_plan,
            allowed_cases_per_month=org.allowed_cases_per_month,
            role=member_role,
            organization_type=getattr(org, "organization_type", "government"),
            verification_status=org.verification_status,
            is_verified_government=org.is_verified_government,
            verification_details=org.verification_details,
            description=org.description,
            logo_storage_path=org.logo_storage_path,
            cover_image_storage_path=org.cover_image_storage_path,
            office_address=org.office_address,
            contact_email=org.contact_email,
            contact_phone=org.contact_phone,
            official_website_url=org.official_website_url,
            supported_languages=org.supported_languages or ["de", "en"],
            created_at=org.created_at,
        )

    def get_user_organization(self, user: User) -> OrganizationRead:
        org, member = self.ensure_default_organization(user)
        return self._to_org_read(org, member.role)

    def update_profile(
        self, user: User, updates: OrganizationProfileUpdate
    ) -> OrganizationRead:
        org, member = self.ensure_default_organization(user)
        if member.role not in ("owner", "admin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only organization owners and administrators can edit workspace settings.",
            )

        if updates.name is not None and updates.name.strip():
            org.name = updates.name.strip()
        if updates.description is not None:
            org.description = updates.description.strip() or None
        if updates.office_address is not None:
            org.office_address = updates.office_address.strip() or None
        if updates.contact_email is not None:
            org.contact_email = str(updates.contact_email).lower()
        if updates.contact_phone is not None:
            org.contact_phone = updates.contact_phone.strip() or None
        if updates.official_website_url is not None:
            org.official_website_url = updates.official_website_url.strip() or None
        if updates.supported_languages is not None:
            org.supported_languages = updates.supported_languages

        self.org_repo.save(org)
        self.db.commit()
        return self._to_org_read(org, member.role)

    def submit_verification(
        self, user: User, req: OrganizationVerificationRequest
    ) -> OrganizationRead:
        org, member = self.ensure_default_organization(user)
        if member.role not in ("owner", "admin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only organization owners and administrators can submit verification requests.",
            )

        org.verification_status = "pending_review"
        org.verification_details = req.model_dump()
        self.org_repo.save(org)
        self.db.commit()
        return self._to_org_read(org, member.role)

    def upload_branding_image(
        self, user: User, file_bytes: bytes, filename: str, image_type: str
    ) -> OrganizationRead:
        org, member = self.ensure_default_organization(user)
        if member.role not in ("owner", "admin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only organization owners and administrators can upload branding assets.",
            )

        if len(file_bytes) > 5 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Image exceeds maximum size limit of 5MB.",
            )

        ext = "png"
        lower_name = filename.lower()
        if lower_name.endswith((".jpg", ".jpeg")):
            ext = "jpg"
        elif lower_name.endswith(".webp"):
            ext = "webp"
        elif lower_name.endswith(".svg"):
            ext = "svg"

        content_type = "image/png"
        if ext == "jpg":
            content_type = "image/jpeg"
        elif ext == "webp":
            content_type = "image/webp"
        elif ext == "svg":
            content_type = "image/svg+xml"

        storage = get_storage_provider()
        with tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = Path(tmp.name)

        try:
            stored_filename = f"{image_type}-{uuid.uuid4().hex[:8]}.{ext}"
            ref = storage.save_file(
                "documents",
                stored_filename,
                tmp_path,
                content_type=content_type,
            )
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

        if image_type == "logo":
            org.logo_storage_path = ref
        else:
            org.cover_image_storage_path = ref

        self.org_repo.save(org)
        self.db.commit()
        return self._to_org_read(org, member.role)

    def list_members(self, user: User) -> list[OrganizationMemberRead]:
        org, _ = self.ensure_default_organization(user)
        members = self.org_repo.list_members(org.id)
        return [
            OrganizationMemberRead(
                id=m.id,
                user_id=m.user_id,
                email=m.user.email if m.user else "user@workspace",
                role=m.role,
                created_at=m.created_at,
            )
            for m in members
        ]

    def invite_member(
        self, user: User, req: OrganizationMemberInvite
    ) -> OrganizationMemberRead:
        org, current_member = self.ensure_default_organization(user)
        if current_member.role not in ("owner", "admin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only organization owners and administrators can invite team members.",
            )

        norm_email = str(req.email).lower()
        target_user = self.user_repo.get_by_normalized_email(norm_email)
        if not target_user:
            from app.auth.security import hash_password

            temp_password = secrets.token_urlsafe(16)
            target_user = self.user_repo.create_user(
                email=str(req.email),
                normalized_email=norm_email,
                password_hash=hash_password(temp_password),
                role="user",
            )

        existing = self.org_repo.get_member(org.id, target_user.id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already a member of this organization workspace.",
            )

        new_member = self.org_repo.add_member(
            organization_id=org.id,
            user_id=target_user.id,
            role=req.role,
        )
        self.db.commit()
        return OrganizationMemberRead(
            id=new_member.id,
            user_id=target_user.id,
            email=target_user.email,
            role=new_member.role,
            created_at=new_member.created_at,
        )

    def update_member_role(
        self, user: User, target_user_id: str, req: OrganizationMemberRoleUpdate
    ) -> OrganizationMemberRead:
        org, current_member = self.ensure_default_organization(user)
        if current_member.role not in ("owner", "admin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only organization owners and administrators can change member roles.",
            )

        target_member = self.org_repo.get_member(org.id, target_user_id)
        if not target_member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization member not found.",
            )

        # Cannot demote the last owner
        if target_member.role == "owner" and req.role != "owner":
            if self.org_repo.count_owners(org.id) <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot change role of the sole organization owner. Assign another owner first.",
                )

        target_member.role = req.role
        self.db.commit()
        return OrganizationMemberRead(
            id=target_member.id,
            user_id=target_member.user_id,
            email=target_member.user.email if target_member.user else "user@workspace",
            role=target_member.role,
            created_at=target_member.created_at,
        )

    def remove_member(self, user: User, target_user_id: str) -> None:
        org, current_member = self.ensure_default_organization(user)
        if current_member.role not in ("owner", "admin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only organization owners and administrators can remove members.",
            )

        target_member = self.org_repo.get_member(org.id, target_user_id)
        if not target_member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization member not found.",
            )

        if target_member.role == "owner" and self.org_repo.count_owners(org.id) <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove the sole organization owner.",
            )

        self.org_repo.remove_member(org.id, target_user_id)
        self.db.commit()

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

        output_lang = (
            version.supported_output_languages[0]
            if version.supported_output_languages
            else version.source_language
        )
        total_required = sum(1 for f in version.fields if f.required)

        # 4. Create underlying candidate FormSession
        expires_at = datetime.now(UTC) + timedelta(days=30)
        form_session = self.session_repo.create_session(
            form_version_id=version.id,
            user_language=request.user_language,
            source_language=version.source_language,
            output_language=output_lang,
            total_required_fields=total_required,
            expires_at=expires_at,
            ownership_token_hash=token_hash,
            user_id=None,
        )

        case = self.case_repo.create(
            organization_id=org.id,
            created_by_user_id=user.id,
            form_version_id=version.id,
            candidate_name=request.candidate_name,
            candidate_email=str(request.candidate_email),
            form_session_id=form_session.id,
            invite_token_hash=token_hash,
            invite_expires_at=datetime.now(UTC) + timedelta(days=14),
            notes=request.notes,
        )
        self.db.commit()

        case_dto = self._enrich_case(case, version_title=form_name)
        case_dto.invite_token = raw_invite_token
        return case_dto, raw_invite_token

    def list_cases(self, user: User) -> list[CaseRead]:
        org, _ = self.ensure_default_organization(user)
        cases = self.case_repo.list_by_organization(org.id)
        return [self._enrich_case(c) for c in cases]

    def get_case(self, user: User, public_id: str) -> CaseRead:
        org, _ = self.ensure_default_organization(user)
        case = self.case_repo.get_by_public_id(public_id)
        if not case or case.organization_id != org.id:
            raise CaseNotFoundError(f"Case with ID '{public_id}' not found.")
        return self._enrich_case(case)

    def update_case(
        self, user: User, public_id: str, updates: CaseUpdateRequest
    ) -> CaseRead:
        org, _ = self.ensure_default_organization(user)
        case = self.case_repo.get_by_public_id(public_id)
        if not case or case.organization_id != org.id:
            raise CaseNotFoundError(f"Case with ID '{public_id}' not found.")

        if updates.status is not None:
            case.status = updates.status
        if updates.notes is not None:
            case.notes = updates.notes

        self.case_repo.save(case)
        self.db.commit()
        return self._enrich_case(case)

    def redeem_candidate_invite(
        self, raw_token: str
    ) -> CandidateInviteRedemptionResponse:
        token_hash = hash_ownership_token(raw_token)
        case = self.case_repo.get_by_invite_token_hash(token_hash)
        if not case:
            raise InvalidInviteTokenError("Invalid or expired candidate invite link.")

        if case.invite_expires_at and case.invite_expires_at < datetime.now(UTC):
            raise InvalidInviteTokenError("This invitation link has expired.")

        session = self.session_repo.get_session_by_id(case.form_session_id or "")
        if not session:
            raise InvalidInviteTokenError("Associated form session is not available.")

        if case.status == "invited":
            case.status = "in_progress"
            self.case_repo.save(case)
            self.db.commit()

        version = self.form_repo.get_version(case.form_version_id)
        title = (
            version.template.name
            if version and version.template
            else "Official Administrative Form"
        )

        return CandidateInviteRedemptionResponse(
            session_id=session.public_id,
            session_token=raw_token,
            case_public_id=case.public_id,
            candidate_name=case.candidate_name,
            candidate_email=case.candidate_email,
            form_title=title,
            form_version_id=case.form_version_id,
            user_language=session.user_language,
            source_language=session.source_language,
            status=case.status,
        )

    def _enrich_case(
        self, case: OrganizationCase, version_title: str | None = None
    ) -> CaseRead:
        title = version_title
        version = None
        if not title:
            version = self.form_repo.get_version(case.form_version_id)
            title = (
                version.template.name
                if version and version.template
                else "Application Form"
            )

        progress = 0
        total_fields = 0
        answered_fields = 0
        session_public_id = None
        if case.form_session_id:
            session = self.session_repo.get_session_by_id(case.form_session_id)
            if session:
                session_public_id = session.public_id
                progress = compute_session_progress_percentage(session)
                answered_fields = len(session.answers)
                if not version:
                    version = self.form_repo.get_version(case.form_version_id)
                total_fields = len(version.fields) if version else 0

        return CaseRead(
            id=case.id,
            public_id=case.public_id,
            organization_id=case.organization_id,
            candidate_name=case.candidate_name,
            candidate_email=case.candidate_email,
            status=case.status,
            form_version_id=case.form_version_id,
            form_title=title,
            form_session_id=case.form_session_id,
            session_public_id=session_public_id,
            notes=case.notes,
            created_at=case.created_at,
            updated_at=case.updated_at,
            total_fields=total_fields,
            answered_fields=answered_fields,
            progress_percent=progress,
        )
