import hmac
import logging
import re
import secrets
import tempfile
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.email_provider import EmailProvider, get_email_provider
from app.auth.models import User
from app.auth.repositories import UserRepository
from app.forms.models import FormTemplate, FormVersion
from app.forms.repositories import FormRepository
from app.organizations.errors import (
    CaseNotFoundError,
    InvalidInviteTokenError,
    OrganizationQuotaExceededError,
)
from app.organizations.models import Organization, OrganizationCase, OrganizationMember
from app.organizations.repositories import (
    CaseRepository,
    CategoryRepository,
    OrganizationRepository,
)
from app.organizations.schemas import (
    CandidateInviteInspectResponse,
    CandidateInviteOrganizationBranding,
    CandidateInviteOtpSendResponse,
    CandidateInviteRedemptionResponse,
    CaseCreateRequest,
    CaseRead,
    CaseUpdateRequest,
    OrganizationCategoryCreate,
    OrganizationCategoryRead,
    OrganizationCategoryUpdate,
    OrganizationMemberInvite,
    OrganizationMemberRead,
    OrganizationMemberRoleUpdate,
    OrganizationProfileUpdate,
    OrganizationRead,
    OrganizationVerificationRequest,
    PublicCategoryItem,
    PublicOrganizationDetail,
    PublicOrganizationSummary,
    PublicPublishedFormItem,
)
from app.sessions.repositories import SessionRepository
from app.sessions.security import generate_ownership_token, hash_ownership_token
from app.sessions.services import compute_session_progress_percentage
from app.storage.factory import get_storage_provider

logger = logging.getLogger(__name__)
SLUG_CLEAN_REGEX = re.compile(r"[^a-z0-9]+")
_OTP_TTL_SECONDS = 600
_OTP_MAX_ATTEMPTS = 5


def _mask_email(email: str) -> str:
    """Mask email local part for unauthenticated invite inspection."""
    raw = (email or "").strip()
    if "@" not in raw:
        return "***"
    local, domain = raw.split("@", 1)
    if len(local) <= 2:
        masked_local = f"{local[0]}***" if local else "***"
    else:
        masked_local = f"{local[0]}***{local[-1]}"
    return f"{masked_local}@{domain}"


class OrganizationService:
    def __init__(self, db: Session, email_provider: EmailProvider | None = None):
        self.db = db
        self.org_repo = OrganizationRepository(db)
        self.case_repo = CaseRepository(db)
        self.form_repo = FormRepository(db)
        self.session_repo = SessionRepository(db)
        self.user_repo = UserRepository(db)
        self.cat_repo = CategoryRepository(db)
        self.email_provider: EmailProvider = (
            email_provider if email_provider is not None else get_email_provider()
        )

    def create_organization_for_user(
        self,
        user: User,
        name: str,
        organization_type: str = "government",
        official_website_url: str | None = None,
    ) -> tuple[Organization, OrganizationMember]:
        clean_name = (
            name.strip()
            if name and name.strip()
            else (
                "Official Public Administration"
                if organization_type == "government"
                else "Private Consulting Partners"
            )
        )
        local_slug = SLUG_CLEAN_REGEX.sub("-", clean_name.lower()).strip("-") or "org"
        unique_slug = f"{local_slug}-{secrets.token_hex(3)}"

        billing_plan = (
            "enterprise" if organization_type == "government" else "agency_pro"
        )
        allowed_cases = 100 if organization_type == "government" else 50
        org = self.org_repo.create(
            name=clean_name,
            slug=unique_slug,
            billing_plan=billing_plan,
            allowed_cases_per_month=allowed_cases,
            organization_type=organization_type,
            official_website_url=official_website_url.strip()
            if official_website_url
            else None,
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
            ui_theme_config=getattr(org, "ui_theme_config", None),
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
        if updates.ui_theme_config is not None:
            org.ui_theme_config = updates.ui_theme_config

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

        lower_name = filename.lower()
        is_svg = (
            lower_name.endswith(".svg")
            or file_bytes.lstrip().startswith(b"<svg")
            or file_bytes.lstrip().startswith(b"<?xml")
        )
        if is_svg:
            ext = "svg"
            content_type = "image/svg+xml"
        elif lower_name.endswith((".jpg", ".jpeg")):
            ext = "jpg"
            content_type = "image/jpeg"
        elif lower_name.endswith(".webp"):
            ext = "webp"
            content_type = "image/webp"
        else:
            ext = "png"
            content_type = "image/png"

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

    def get_branding_image(
        self, organization_id: str, image_type: str = "logo"
    ) -> tuple[bytes, str]:
        org = self.org_repo.get(organization_id)
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found.",
            )

        ref = (
            org.logo_storage_path
            if image_type == "logo"
            else org.cover_image_storage_path
        )
        if not ref:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Organization {image_type} not set.",
            )

        storage = get_storage_provider()
        if not storage.exists(ref):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Stored {image_type} file missing on disk.",
            )

        file_bytes = storage.get_bytes(ref)
        lower_ref = ref.lower()
        if lower_ref.endswith(".svg") or file_bytes.lstrip().startswith(
            (b"<svg", b"<?xml")
        ):
            content_type = "image/svg+xml"
        elif lower_ref.endswith((".jpg", ".jpeg")):
            content_type = "image/jpeg"
        elif lower_ref.endswith(".webp"):
            content_type = "image/webp"
        else:
            content_type = "image/png"

        return file_bytes, content_type

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

        # 3. Generate candidate invite token separately from the initial session ownership token
        # so the raw URL invite token can NEVER unlock /api/form-sessions/* directly before OTP.
        raw_invite_token = generate_ownership_token()
        invite_hash = hash_ownership_token(raw_invite_token)
        initial_session_hash = hash_ownership_token(generate_ownership_token())

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
            ownership_token_hash=initial_session_hash,
            user_id=None,
        )

        case = self.case_repo.create(
            organization_id=org.id,
            created_by_user_id=user.id,
            form_version_id=version.id,
            candidate_name=request.candidate_name,
            candidate_email=str(request.candidate_email),
            form_session_id=form_session.id,
            invite_token_hash=invite_hash,
            invite_expires_at=datetime.now(UTC) + timedelta(days=14),
            notes=request.notes,
        )
        self.db.commit()

        try:
            self.email_provider.send_candidate_invite(
                recipient=case.candidate_email,
                invite_token=raw_invite_token,
                organization_name=org.name,
                form_title=form_name,
            )
        except Exception as exc:
            logger.warning(
                "Candidate invite email dispatch failed (%s); case=%s",
                type(exc).__name__,
                case.public_id,
            )

        self._log_case_audit("invite_created", case, actor_user_id=user.id)

        case_dto = self._enrich_case(case, version_title=form_name)
        case_dto.invite_token = raw_invite_token
        return case_dto, raw_invite_token

    def _log_case_audit(
        self,
        action: str,
        case: OrganizationCase,
        actor_user_id: str | None = None,
    ) -> None:
        """Emit a zero-PII audit log entry for invite & OTP lifecycle events."""
        logger.info(
            "case_audit action=%s case_public_id=%s org_id=%s status=%s actor_user_id=%s",
            action,
            case.public_id,
            case.organization_id,
            case.status,
            actor_user_id or "candidate",
        )

    @staticmethod
    def _build_invite_branding(
        org: Organization,
    ) -> CandidateInviteOrganizationBranding:
        return CandidateInviteOrganizationBranding(
            id=org.id,
            name=org.name,
            slug=org.slug,
            organization_type=org.organization_type,
            verification_status=org.verification_status,
            is_verified_government=org.is_verified_government,
            description=org.description,
            has_logo=bool(org.logo_storage_path),
            office_address=org.office_address,
            contact_email=org.contact_email,
            contact_phone=org.contact_phone,
            official_website_url=org.official_website_url,
            ui_theme_config=org.ui_theme_config,
        )

    @staticmethod
    def _extract_template_metadata(
        version: FormVersion | None,
    ) -> tuple[str, str | None, list[str], str, str | None]:
        template = version.template if version else None
        if not template:
            return (
                "Official Administrative Form",
                None,
                [],
                "print_and_sign",
                None,
            )
        return (
            template.name,
            template.description,
            list(template.required_documents or []),
            template.submission_method or "print_and_sign",
            template.instructions,
        )

    def _get_active_invite_case(self, raw_token: str) -> OrganizationCase:
        cleaned = (raw_token or "").strip()
        if not cleaned:
            raise InvalidInviteTokenError("Invalid or expired candidate invite link.")
        token_hash = hash_ownership_token(cleaned)
        case = self.case_repo.get_by_invite_token_hash(token_hash)
        if not case:
            raise InvalidInviteTokenError("Invalid or expired candidate invite link.")
        if case.status == "revoked" or case.revoked_at is not None:
            raise InvalidInviteTokenError(
                "This invitation link has been revoked by your case coordinator."
            )
        if case.invite_expires_at and case.invite_expires_at < datetime.now(UTC):
            raise InvalidInviteTokenError("This invitation link has expired.")
        return case

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
            if updates.status == "completed" and case.completed_at is None:
                case.completed_at = datetime.now(UTC)
            elif updates.status == "revoked" and case.revoked_at is None:
                case.revoked_at = datetime.now(UTC)
                case.invite_token_hash = None
                case.otp_code_hash = None
                case.otp_expires_at = None
        if updates.notes is not None:
            case.notes = updates.notes

        self.case_repo.save(case)
        self.db.commit()
        return self._enrich_case(case)

    def inspect_candidate_invite(
        self, raw_token: str
    ) -> CandidateInviteInspectResponse:
        case = self._get_active_invite_case(raw_token)
        session = self.session_repo.get_session_by_id(case.form_session_id or "")
        if not session:
            raise InvalidInviteTokenError("Associated form session is not available.")
        org = self.org_repo.get(case.organization_id)
        if not org:
            raise InvalidInviteTokenError("Associated organization is not available.")

        case.last_accessed_at = datetime.now(UTC)
        self.case_repo.save(case)
        self.db.commit()
        self._log_case_audit("invite_inspected", case)

        version = self.form_repo.get_version(case.form_version_id)
        title, description, req_docs, sub_method, instructions = (
            self._extract_template_metadata(version)
        )
        return CandidateInviteInspectResponse(
            case_public_id=case.public_id,
            candidate_name=case.candidate_name,
            masked_email=_mask_email(case.candidate_email),
            form_title=title,
            form_description=description,
            form_version_id=case.form_version_id,
            user_language=session.user_language,
            source_language=session.source_language,
            status=case.status,
            otp_verified=case.otp_verified_at is not None,
            required_documents=req_docs,
            submission_method=sub_method,
            instructions=instructions,
            organization=self._build_invite_branding(org),
        )

    def send_candidate_invite_otp(
        self, raw_token: str
    ) -> CandidateInviteOtpSendResponse:
        case = self._get_active_invite_case(raw_token)
        org = self.org_repo.get(case.organization_id)
        if not org:
            raise InvalidInviteTokenError("Associated organization is not available.")
        version = self.form_repo.get_version(case.form_version_id)
        title, _, _, _, _ = self._extract_template_metadata(version)

        otp_code = f"{secrets.randbelow(1_000_000):06d}"
        case.otp_code_hash = hash_ownership_token(f"{case.id}:{otp_code}")
        case.otp_expires_at = datetime.now(UTC) + timedelta(seconds=_OTP_TTL_SECONDS)
        case.otp_attempts = 0
        self.case_repo.save(case)
        self.db.commit()

        self.email_provider.send_candidate_otp(
            recipient=case.candidate_email,
            otp_code=otp_code,
            organization_name=org.name,
            form_title=title,
        )
        self._log_case_audit("invite_otp_sent", case)

        return CandidateInviteOtpSendResponse(
            sent=True,
            masked_email=_mask_email(case.candidate_email),
            expires_in_seconds=_OTP_TTL_SECONDS,
        )

    def verify_candidate_invite_otp(
        self, raw_token: str, otp_code: str
    ) -> CandidateInviteRedemptionResponse:
        case = self._get_active_invite_case(raw_token)
        session = self.session_repo.get_session_by_id(case.form_session_id or "")
        if not session:
            raise InvalidInviteTokenError("Associated form session is not available.")
        org = self.org_repo.get(case.organization_id)
        if not org:
            raise InvalidInviteTokenError("Associated organization is not available.")

        now = datetime.now(UTC)
        if (
            not case.otp_code_hash
            or not case.otp_expires_at
            or case.otp_expires_at < now
        ):
            raise InvalidInviteTokenError(
                "Verification code expired or not requested. Please request a new code."
            )

        if (case.otp_attempts or 0) >= _OTP_MAX_ATTEMPTS:
            case.otp_code_hash = None
            self.case_repo.save(case)
            self.db.commit()
            raise InvalidInviteTokenError(
                "Too many incorrect verification attempts. Please request a new code."
            )

        candidate_hash = hash_ownership_token(f"{case.id}:{otp_code.strip()}")
        if not hmac.compare_digest(candidate_hash, case.otp_code_hash):
            case.otp_attempts = (case.otp_attempts or 0) + 1
            if case.otp_attempts >= _OTP_MAX_ATTEMPTS:
                case.otp_code_hash = None
            self.case_repo.save(case)
            # Commit BEFORE raising so brute-force counter persists across HTTP requests.
            self.db.commit()
            self._log_case_audit("invite_otp_failed", case)
            raise InvalidInviteTokenError(
                "Invalid verification code. Please check your email and try again."
            )

        raw_session_token = generate_ownership_token()
        session.ownership_token_hash = hash_ownership_token(raw_session_token)
        if session.status == "cancelled":
            session.status = "in_progress" if session.answers else "session_created"
            session.cancelled_at = None

        case.otp_code_hash = None
        case.otp_expires_at = None
        case.otp_attempts = 0
        case.otp_verified_at = now
        case.last_accessed_at = now
        if case.status == "invited":
            case.status = "in_progress"

        self.case_repo.save(case)
        self.db.add(session)
        self.db.commit()
        self._log_case_audit("invite_otp_verified", case)

        version = self.form_repo.get_version(case.form_version_id)
        title, _, req_docs, sub_method, instructions = self._extract_template_metadata(
            version
        )

        return CandidateInviteRedemptionResponse(
            session_id=session.public_id,
            session_token=raw_session_token,
            case_public_id=case.public_id,
            candidate_name=case.candidate_name,
            candidate_email=case.candidate_email,
            form_title=title,
            form_version_id=case.form_version_id,
            user_language=session.user_language,
            source_language=session.source_language,
            status=case.status,
            required_documents=req_docs,
            submission_method=sub_method,
            instructions=instructions,
            organization=self._build_invite_branding(org),
        )

    def revoke_case_invite(self, user: User, public_id: str) -> CaseRead:
        org, member = self.ensure_default_organization(user)
        if member.role not in ("owner", "admin", "case_manager"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only case managers and admins can revoke candidate invites.",
            )

        case = self.case_repo.get_by_public_id(public_id)
        if not case or case.organization_id != org.id:
            raise CaseNotFoundError(f"Case with ID '{public_id}' not found.")
        if case.status == "completed":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Completed cases cannot be revoked.",
            )

        now = datetime.now(UTC)
        case.invite_token_hash = None
        case.otp_code_hash = None
        case.otp_expires_at = None
        case.otp_attempts = 0
        case.revoked_at = now
        case.status = "revoked"

        if case.form_session_id:
            session = self.session_repo.get_session_by_id(case.form_session_id)
            if session and session.user_id is None and session.status != "completed":
                session.ownership_token_hash = None
                session.status = "cancelled"
                session.cancelled_at = now
                self.db.add(session)

        self.case_repo.save(case)
        self.db.commit()
        self._log_case_audit("invite_revoked", case, actor_user_id=user.id)
        return self._enrich_case(case)

    def resend_case_invite(self, user: User, public_id: str) -> tuple[CaseRead, str]:
        org, member = self.ensure_default_organization(user)
        if member.role not in ("owner", "admin", "case_manager"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only case managers and admins can resend candidate invites.",
            )

        case = self.case_repo.get_by_public_id(public_id)
        if not case or case.organization_id != org.id:
            raise CaseNotFoundError(f"Case with ID '{public_id}' not found.")
        if case.status == "completed":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Completed cases cannot be resent.",
            )

        now = datetime.now(UTC)
        raw_invite_token = generate_ownership_token()
        case.invite_token_hash = hash_ownership_token(raw_invite_token)
        case.invite_expires_at = now + timedelta(days=14)
        case.revoked_at = None
        case.otp_code_hash = None
        case.otp_expires_at = None
        case.otp_attempts = 0
        case.otp_verified_at = None
        case.resend_count = (case.resend_count or 0) + 1
        case.last_resent_at = now

        session = (
            self.session_repo.get_session_by_id(case.form_session_id)
            if case.form_session_id
            else None
        )
        if session and session.user_id is None:
            session.ownership_token_hash = hash_ownership_token(
                generate_ownership_token()
            )
            session.expires_at = now + timedelta(days=30)
            if session.status in ("cancelled", "expired"):
                session.status = "in_progress" if session.answers else "session_created"
                session.cancelled_at = None
            self.db.add(session)

        case.status = "in_progress" if (session and session.answers) else "invited"
        self.case_repo.save(case)
        self.db.commit()

        version = self.form_repo.get_version(case.form_version_id)
        form_name, _, _, _, _ = self._extract_template_metadata(version)
        try:
            self.email_provider.send_candidate_invite(
                recipient=case.candidate_email,
                invite_token=raw_invite_token,
                organization_name=org.name,
                form_title=form_name,
            )
        except Exception as exc:
            logger.warning(
                "Candidate invite resend email failed (%s); case=%s",
                type(exc).__name__,
                case.public_id,
            )

        self._log_case_audit("invite_resent", case, actor_user_id=user.id)
        case_dto = self._enrich_case(case, version_title=form_name)
        case_dto.invite_token = raw_invite_token
        return case_dto, raw_invite_token

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
            invite_expires_at=case.invite_expires_at,
            otp_verified_at=case.otp_verified_at,
            last_accessed_at=case.last_accessed_at,
            revoked_at=case.revoked_at,
            resend_count=case.resend_count or 0,
            last_resent_at=case.last_resent_at,
            completed_at=case.completed_at,
            total_fields=total_fields,
            answered_fields=answered_fields,
            progress_percent=progress,
        )

    # Public Portals & Citizen Discovery (Phase G3)
    def list_public_organizations(
        self, search: str | None = None, organization_type: str | None = None
    ) -> list[PublicOrganizationSummary]:
        orgs = self.org_repo.list_public(
            search=search, organization_type=organization_type
        )
        results: list[PublicOrganizationSummary] = []
        for org in orgs:
            stmt = (
                select(func.count(FormTemplate.id))
                .join(FormVersion, FormVersion.form_template_id == FormTemplate.id)
                .where(
                    FormTemplate.organization_id == org.id,
                    FormVersion.status == "published",
                )
            )
            count = int(self.db.execute(stmt).scalar() or 0)
            results.append(
                PublicOrganizationSummary(
                    id=org.id,
                    name=org.name,
                    slug=org.slug,
                    organization_type=org.organization_type,
                    verification_status=org.verification_status,
                    is_verified_government=org.is_verified_government,
                    description=org.description,
                    office_address=org.office_address,
                    official_website_url=org.official_website_url,
                    has_logo=bool(org.logo_storage_path),
                    published_forms_count=count,
                    supported_languages=org.supported_languages or ["de", "en"],
                )
            )
        return results

    # Category Taxonomy Service Methods (TYPO3-Inspired)
    def list_categories(
        self, user: User, only_active: bool = False
    ) -> list[OrganizationCategoryRead]:
        org, _ = self.ensure_default_organization(user)
        cat_repo = CategoryRepository(self.db)
        categories = cat_repo.list_by_organization(org.id, only_active=only_active)
        counts = cat_repo.count_all_forms(org.id)
        return [
            OrganizationCategoryRead(
                id=c.id,
                organization_id=c.organization_id,
                name=c.name,
                slug=c.slug,
                icon=c.icon,
                description=c.description,
                parent_id=c.parent_id,
                translations=c.translations or {},
                sort_order=c.sort_order,
                is_active=c.is_active,
                forms_count=counts.get(c.id, 0),
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
            for c in categories
        ]

    def create_category(
        self, user: User, req: OrganizationCategoryCreate
    ) -> OrganizationCategoryRead:
        org, member = self.ensure_default_organization(user)
        if member.role not in ("owner", "admin", "form_editor"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only organization owners, admins, and form editors can create categories.",
            )
        cat_repo = CategoryRepository(self.db)
        clean_name = req.name.strip()
        slug = (
            req.slug.strip()
            if req.slug
            else SLUG_CLEAN_REGEX.sub("-", clean_name.lower()).strip("-")
        )
        existing = cat_repo.get_by_slug(org.id, slug)
        if existing:
            slug = f"{slug}-{str(uuid.uuid4())[:4]}"

        category = cat_repo.create(
            organization_id=org.id,
            name=clean_name,
            slug=slug,
            icon=req.icon.strip() if req.icon else None,
            description=req.description.strip() if req.description else None,
            parent_id=req.parent_id if req.parent_id else None,
            translations=req.translations or {},
            sort_order=req.sort_order,
            is_active=req.is_active,
        )
        self.db.commit()
        return OrganizationCategoryRead(
            id=category.id,
            organization_id=category.organization_id,
            name=category.name,
            slug=category.slug,
            icon=category.icon,
            description=category.description,
            parent_id=category.parent_id,
            translations=category.translations or {},
            sort_order=category.sort_order,
            is_active=category.is_active,
            forms_count=0,
            created_at=category.created_at,
            updated_at=category.updated_at,
        )

    def update_category(
        self, user: User, category_id: str, req: OrganizationCategoryUpdate
    ) -> OrganizationCategoryRead:
        org, member = self.ensure_default_organization(user)
        if member.role not in ("owner", "admin", "form_editor"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only organization owners, admins, and form editors can edit categories.",
            )
        cat_repo = CategoryRepository(self.db)
        category = cat_repo.get_by_id(org.id, category_id)
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Category '{category_id}' not found.",
            )

        if req.name is not None and req.name.strip():
            category.name = req.name.strip()
        if req.slug is not None and req.slug.strip():
            category.slug = SLUG_CLEAN_REGEX.sub("-", req.slug.strip().lower()).strip(
                "-"
            )
        if req.icon is not None:
            category.icon = req.icon.strip() or None
        if req.description is not None:
            category.description = req.description.strip() or None
        if req.parent_id is not None:
            category.parent_id = req.parent_id if req.parent_id != "none" else None
        if req.translations is not None:
            category.translations = req.translations
        if req.sort_order is not None:
            category.sort_order = req.sort_order
        if req.is_active is not None:
            category.is_active = req.is_active

        self.db.commit()
        counts = cat_repo.count_all_forms(org.id)
        return OrganizationCategoryRead(
            id=category.id,
            organization_id=category.organization_id,
            name=category.name,
            slug=category.slug,
            icon=category.icon,
            description=category.description,
            parent_id=category.parent_id,
            translations=category.translations or {},
            sort_order=category.sort_order,
            is_active=category.is_active,
            forms_count=counts.get(category.id, 0),
            created_at=category.created_at,
            updated_at=category.updated_at,
        )

    def delete_category(self, user: User, category_id: str) -> None:
        org, member = self.ensure_default_organization(user)
        if member.role not in ("owner", "admin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only organization owners and admins can delete categories.",
            )
        cat_repo = CategoryRepository(self.db)
        category = cat_repo.get_by_id(org.id, category_id)
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Category '{category_id}' not found.",
            )
        self.db.query(FormTemplate).filter(
            FormTemplate.organization_id == org.id,
            FormTemplate.category_id == category.id,
        ).update({"category_id": None})

        cat_repo.delete(category)
        self.db.commit()

    def get_category_forms(self, user: User, category_id: str) -> list[str]:
        org, _ = self.ensure_default_organization(user)
        cat = self.cat_repo.get_by_id(org.id, category_id)
        if not cat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Category '{category_id}' not found.",
            )
        form_rows = (
            self.db.query(FormTemplate.id)
            .filter(
                FormTemplate.organization_id == org.id,
                FormTemplate.category_id == category_id,
            )
            .all()
        )
        return [r[0] for r in form_rows]

    def assign_category_forms(
        self, user: User, category_id: str, form_ids: list[str]
    ) -> list[str]:
        org, member = self.ensure_default_organization(user)
        if member.role not in ["owner", "admin", "editor"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin or editor permissions required to update categories.",
            )
        cat = self.cat_repo.get_by_id(org.id, category_id)
        if not cat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Category '{category_id}' not found.",
            )

        # Unassign any forms currently belonging to this category that are not in form_ids
        unassign_q = self.db.query(FormTemplate).filter(
            FormTemplate.organization_id == org.id,
            FormTemplate.category_id == category_id,
        )
        if form_ids:
            unassign_q = unassign_q.filter(~FormTemplate.id.in_(form_ids))
        unassign_q.update(
            {FormTemplate.category_id: None, FormTemplate.category: "general"},
            synchronize_session="fetch",
        )

        # Assign forms in form_ids to this category
        if form_ids:
            self.db.query(FormTemplate).filter(
                FormTemplate.organization_id == org.id,
                FormTemplate.id.in_(form_ids),
            ).update(
                {
                    FormTemplate.category_id: category_id,
                    FormTemplate.category: cat.name,
                },
                synchronize_session="fetch",
            )

        self.db.commit()
        return form_ids

    def get_public_organization_by_slug(self, slug: str) -> PublicOrganizationDetail:
        org = self.org_repo.get_by_slug(slug)
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Organization with slug '{slug}' was not found.",
            )

        cat_repo = CategoryRepository(self.db)
        categories_db = cat_repo.list_by_organization(org.id, only_active=True)

        cat_by_id = {c.id: c for c in categories_db}
        cat_by_slug = {c.slug.lower(): c for c in categories_db}

        stmt = (
            select(FormTemplate, FormVersion)
            .join(FormVersion, FormVersion.form_template_id == FormTemplate.id)
            .where(
                FormTemplate.organization_id == org.id,
                FormVersion.status == "published",
            )
            .order_by(FormTemplate.name.asc())
        )
        rows = self.db.execute(stmt).all()
        published_forms: list[PublicPublishedFormItem] = []
        needs_commit = False

        for template, version in rows:
            cat_obj = None
            if template.category_id and template.category_id in cat_by_id:
                cat_obj = cat_by_id[template.category_id]
            elif template.category and template.category.lower() in cat_by_slug:
                cat_obj = cat_by_slug[template.category.lower()]
                template.category_id = cat_obj.id
                needs_commit = True

            fields_count = len(version.fields) if version.fields else 0
            published_forms.append(
                PublicPublishedFormItem(
                    id=template.id,
                    key=template.key,
                    name=template.name,
                    description=template.description,
                    category=template.category,
                    category_id=cat_obj.id if cat_obj else template.category_id,
                    category_slug=cat_obj.slug
                    if cat_obj
                    else (template.category or "general"),
                    category_name=cat_obj.name if cat_obj else template.category,
                    submission_method=template.submission_method,
                    instructions=template.instructions,
                    required_documents=template.required_documents or [],
                    active_version_id=version.id,
                    version_number=version.version_number,
                    source_language=version.source_language,
                    supported_output_languages=version.supported_output_languages
                    or ["en", "de"],
                    fields_count=fields_count,
                    has_pdf=bool(
                        version.source_pdf_storage_path or version.pdf_template_key
                    ),
                )
            )

        if needs_commit:
            self.db.commit()

        counts_by_cat = cat_repo.count_published_forms(org.id)
        public_categories = [
            PublicCategoryItem(
                id=c.id,
                name=c.name,
                slug=c.slug,
                icon=c.icon,
                description=c.description,
                parent_id=c.parent_id,
                translations=c.translations or {},
                sort_order=c.sort_order,
                forms_count=counts_by_cat.get(c.id, 0),
            )
            for c in categories_db
        ]

        return PublicOrganizationDetail(
            id=org.id,
            name=org.name,
            slug=org.slug,
            organization_type=org.organization_type,
            verification_status=org.verification_status,
            is_verified_government=org.is_verified_government,
            description=org.description,
            office_address=org.office_address,
            official_website_url=org.official_website_url,
            has_logo=bool(org.logo_storage_path),
            published_forms_count=len(published_forms),
            supported_languages=org.supported_languages or ["de", "en"],
            contact_email=org.contact_email,
            contact_phone=org.contact_phone,
            cover_image_storage_path=org.cover_image_storage_path,
            ui_theme_config=getattr(org, "ui_theme_config", None),
            categories=public_categories,
            published_forms=published_forms,
        )

    def get_organization_logo_bytes(self, slug: str) -> tuple[bytes, str]:
        org = self.org_repo.get_by_slug(slug)
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Organization with slug '{slug}' was not found.",
            )
        return self.get_branding_image(org.id, "logo")
