class OrganizationNotFoundError(Exception):
    pass


class CaseNotFoundError(Exception):
    pass


class OrganizationQuotaExceededError(Exception):
    pass


class InvalidInviteTokenError(Exception):
    pass


class CaseUnauthorizedError(Exception):
    pass
