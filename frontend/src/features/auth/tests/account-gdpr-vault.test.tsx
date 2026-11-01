import React from "react";
import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

const pushMock = vi.fn();
let searchTokenValue: string | null = null;

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
  useSearchParams: () => ({
    get: (key: string) => (key === "token" ? searchTokenValue : null),
  }),
}));

const translateStub = (key: string) => key;

vi.mock("next-intl", () => ({
  useTranslations: () => translateStub,
}));

const refreshMock = vi.fn();
const authUserMock = vi.fn(() => ({
  user: {
    id: "user-gdpr-1",
    email: "gdpr@example.com",
    emailVerified: false,
    createdAt: "2026-10-26T00:00:00Z",
  },
  loading: false,
  refresh: refreshMock,
  logout: vi.fn(),
}));

vi.mock("@/features/auth/context/AuthProvider", () => ({
  useAuth: () => authUserMock(),
  useOptionalAuth: () => authUserMock(),
}));

const requestEmailVerificationMock = vi.fn();
const confirmEmailVerificationMock = vi.fn();
const requestPasswordResetMock = vi.fn();
const confirmPasswordResetMock = vi.fn();
const exportAccountDataMock = vi.fn();
const deleteAccountMock = vi.fn();

vi.mock("@/features/auth/services/authClient", async (importOriginal) => {
  const actual = await importOriginal<
    typeof import("@/features/auth/services/authClient")
  >();
  return {
    ...actual,
    requestEmailVerification: (...args: unknown[]) =>
      requestEmailVerificationMock(...args),
    confirmEmailVerification: (...args: unknown[]) =>
      confirmEmailVerificationMock(...args),
    requestPasswordReset: (...args: unknown[]) =>
      requestPasswordResetMock(...args),
    confirmPasswordReset: (...args: unknown[]) =>
      confirmPasswordResetMock(...args),
    exportAccountData: (...args: unknown[]) => exportAccountDataMock(...args),
    deleteAccount: (...args: unknown[]) => deleteAccountMock(...args),
  };
});

const listProfileVaultMock = vi.fn();
const upsertProfileVaultEntryMock = vi.fn();
const deleteProfileVaultEntryMock = vi.fn();
const clearProfileVaultMock = vi.fn();

vi.mock("@/features/profile-vault/services/vaultClient", () => ({
  listProfileVault: (...args: unknown[]) => listProfileVaultMock(...args),
  upsertProfileVaultEntry: (...args: unknown[]) =>
    upsertProfileVaultEntryMock(...args),
  deleteProfileVaultEntry: (...args: unknown[]) =>
    deleteProfileVaultEntryMock(...args),
  clearProfileVault: (...args: unknown[]) => clearProfileVaultMock(...args),
}));

afterEach(() => {
  searchTokenValue = null;
  vi.clearAllMocks();
});

describe("Phase S2 — Account Lifecycle, Profile Vault & GDPR Self-Service", () => {
  it("requests an email verification link from AccountSettingsPage", async () => {
    listProfileVaultMock.mockResolvedValue([]);
    requestEmailVerificationMock.mockResolvedValue({
      status: "verification_sent",
    });

    const { default: AccountPage } = await import("@/app/account/page");
    render(<AccountPage />);

    const verifyBtn = await screen.findByTestId("request-verify-email-btn");
    fireEvent.click(verifyBtn);

    await waitFor(() => {
      expect(requestEmailVerificationMock).toHaveBeenCalledTimes(1);
    });
  });

  it("lists, adds, and deletes encrypted Profile Vault entries on AccountSettingsPage", async () => {
    listProfileVaultMock.mockResolvedValue([
      {
        questionKey: "personal.first_name",
        fieldType: "string",
        value: "Amira",
        normalizedValue: "Amira",
        valueLanguage: "en",
        updatedAt: "2026-10-26T10:00:00Z",
      },
    ]);
    upsertProfileVaultEntryMock.mockResolvedValue({
      questionKey: "address.city",
      fieldType: "string",
      value: "Berlin",
      normalizedValue: "Berlin",
      valueLanguage: "en",
      updatedAt: "2026-10-26T11:00:00Z",
    });
    deleteProfileVaultEntryMock.mockResolvedValue(undefined);

    const { default: AccountPage } = await import("@/app/account/page");
    render(<AccountPage />);

    expect(await screen.findByText("Amira")).toBeTruthy();

    fireEvent.change(screen.getByTestId("vault-key-select"), {
      target: { value: "address.city" },
    });
    fireEvent.change(screen.getByTestId("vault-value-input"), {
      target: { value: "Berlin" },
    });
    fireEvent.click(screen.getByTestId("vault-save-entry-btn"));

    await waitFor(() => {
      expect(upsertProfileVaultEntryMock).toHaveBeenCalledWith(
        "address.city",
        "Berlin",
        "string",
        "en",
      );
    });

    fireEvent.click(screen.getByTestId("vault-delete-personal.first_name"));
    await waitFor(() => {
      expect(deleteProfileVaultEntryMock).toHaveBeenCalledWith(
        "personal.first_name",
      );
    });
  });

  it("filters out filled fields from dropdown and displays completion banner when all fields are stored", async () => {
    const allKeys = [
      "personal.first_name",
      "personal.last_name",
      "person.date_of_birth",
      "personal.nationality",
      "contact.email",
      "contact.phone",
      "address.street",
      "address.postal_code",
      "address.city",
      "address.country",
      "finance.iban",
    ];

    listProfileVaultMock.mockResolvedValue(
      allKeys.map((k) => ({
        questionKey: k,
        fieldType: "string",
        value: "dummy",
        normalizedValue: "dummy",
        valueLanguage: "en",
        updatedAt: "2026-10-26T10:00:00Z",
      })),
    );

    const { default: AccountPage } = await import("@/app/account/page");
    render(<AccountPage />);

    expect(await screen.findByText("allFieldsSaved")).toBeTruthy();
    expect(screen.queryByTestId("vault-key-select")).toBeNull();
  });

  it("exports portable GDPR JSON data and supports permanent account erasure", async () => {
    listProfileVaultMock.mockResolvedValue([]);
    exportAccountDataMock.mockResolvedValue({
      exportedAt: "2026-10-26T12:00:00Z",
      account: { id: "user-gdpr-1", email: "gdpr@example.com" },
      profileVault: [],
      applications: [],
      documents: [],
    });
    deleteAccountMock.mockResolvedValue(undefined);

    const originalCreateObjectURL = URL.createObjectURL;
    const originalRevokeObjectURL = URL.revokeObjectURL;
    URL.createObjectURL = vi.fn(() => "blob:http://localhost/gdpr-export");
    URL.revokeObjectURL = vi.fn();

    const { default: AccountPage } = await import("@/app/account/page");
    render(<AccountPage />);

    const exportBtn = await screen.findByTestId("gdpr-export-btn");
    fireEvent.click(exportBtn);

    await waitFor(() => {
      expect(exportAccountDataMock).toHaveBeenCalledTimes(1);
    });

    fireEvent.click(screen.getByTestId("delete-account-open-btn"));
    fireEvent.click(screen.getByTestId("delete-account-confirm-btn"));

    await waitFor(() => {
      expect(deleteAccountMock).toHaveBeenCalledTimes(1);
      expect(pushMock).toHaveBeenCalledWith("/");
    });

    URL.createObjectURL = originalCreateObjectURL;
    URL.revokeObjectURL = originalRevokeObjectURL;
  });

  it("requests and confirms password reset on ResetPasswordPage", async () => {
    requestPasswordResetMock.mockResolvedValue({
      status: "password_reset_requested",
    });
    confirmPasswordResetMock.mockResolvedValue({
      status: "password_reset_completed",
    });

    const { default: ResetPasswordPage } = await import(
      "@/app/reset-password/page"
    );
    const { unmount } = render(<ResetPasswordPage />);

    fireEvent.change(screen.getByTestId("reset-email-input"), {
      target: { value: "gdpr@example.com" },
    });
    fireEvent.click(screen.getByTestId("reset-request-submit"));

    await waitFor(() => {
      expect(requestPasswordResetMock).toHaveBeenCalledWith("gdpr@example.com");
    });

    unmount();
    searchTokenValue = "reset-tok-123";
    render(<ResetPasswordPage />);

    fireEvent.change(screen.getByTestId("reset-new-password-input"), {
      target: { value: "NewStrongPass123!" },
    });
    fireEvent.change(screen.getByTestId("reset-confirm-password-input"), {
      target: { value: "NewStrongPass123!" },
    });
    fireEvent.click(screen.getByTestId("reset-confirm-submit"));

    await waitFor(() => {
      expect(confirmPasswordResetMock).toHaveBeenCalledWith(
        "reset-tok-123",
        "NewStrongPass123!",
        "NewStrongPass123!",
      );
    });
  });
});
