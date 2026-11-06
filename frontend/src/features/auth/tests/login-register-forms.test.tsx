import React from "react";
import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

const pushMock = vi.fn();
let mockSearchParams = new URLSearchParams();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
  useSearchParams: () => mockSearchParams,
}));

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => key,
}));

const loginMock = vi.fn();
const registerMock = vi.fn();

vi.mock("@/features/auth/context/AuthProvider", () => ({
  useAuth: () => ({
    user: null,
    loading: false,
    login: loginMock,
    register: registerMock,
    logout: vi.fn(),
    refresh: vi.fn(),
  }),
}));

class FakeAuthApiError extends Error {
  status: number;
  errorCode: string | null;
  constructor(status: number, message: string, errorCode: string | null = null) {
    super(message);
    this.status = status;
    this.errorCode = errorCode;
  }
}

vi.mock("@/features/auth/services/authClient", () => ({
  AuthApiError: FakeAuthApiError,
}));

afterEach(() => {
  vi.clearAllMocks();
});

describe("LoginForm", () => {
  it("logs in and redirects to /applications on success", async () => {
    loginMock.mockResolvedValue({ id: "u1", email: "user@example.com", createdAt: "now" });
    const { default: LoginForm } = await import("@/features/auth/components/LoginForm");
    render(<LoginForm />);

    fireEvent.change(screen.getByLabelText("emailLabel"), {
      target: { value: "user@example.com" },
    });
    fireEvent.change(screen.getByLabelText("passwordLabel"), {
      target: { value: "correct-horse-battery" },
    });
    fireEvent.click(screen.getByText("loginButton"));

    await waitFor(() =>
      expect(loginMock).toHaveBeenCalledWith("user@example.com", "correct-horse-battery")
    );
    await waitFor(() => expect(pushMock).toHaveBeenCalledWith("/applications"));
  });

  it("shows a generic error message on invalid credentials", async () => {
    loginMock.mockRejectedValue(new FakeAuthApiError(401, "Authentication required."));
    const { default: LoginForm } = await import("@/features/auth/components/LoginForm");
    render(<LoginForm />);

    fireEvent.change(screen.getByLabelText("emailLabel"), {
      target: { value: "user@example.com" },
    });
    fireEvent.change(screen.getByLabelText("passwordLabel"), {
      target: { value: "wrong-password" },
    });
    fireEvent.click(screen.getByText("loginButton"));

    await waitFor(() => expect(screen.getByText("error_generic_login_failed")).toBeDefined());
    expect(pushMock).not.toHaveBeenCalled();
  });

  it("redirects to custom redirectUrl on login success when redirect param is present", async () => {
    mockSearchParams = new URLSearchParams("redirect=/application/session/sess-123");
    loginMock.mockResolvedValue({ id: "u1", email: "user@example.com", createdAt: "now" });
    const { default: LoginForm } = await import("@/features/auth/components/LoginForm");
    render(<LoginForm />);

    fireEvent.change(screen.getByLabelText("emailLabel"), {
      target: { value: "user@example.com" },
    });
    fireEvent.change(screen.getByLabelText("passwordLabel"), {
      target: { value: "correct-horse-battery" },
    });
    fireEvent.click(screen.getByText("loginButton"));

    await waitFor(() =>
      expect(pushMock).toHaveBeenCalledWith("/application/session/sess-123")
    );
    mockSearchParams = new URLSearchParams();
  });
});

describe("RegisterForm", () => {
  it("registers and redirects to /applications on success", async () => {
    registerMock.mockResolvedValue({ id: "u1", email: "new@example.com", createdAt: "now" });
    const { default: RegisterForm } = await import("@/features/auth/components/RegisterForm");
    render(<RegisterForm />);

    fireEvent.change(screen.getByLabelText("emailLabel"), {
      target: { value: "new@example.com" },
    });
    fireEvent.change(screen.getByLabelText("passwordLabel"), {
      target: { value: "correct-horse-battery" },
    });
    fireEvent.change(screen.getByLabelText("passwordConfirmationLabel"), {
      target: { value: "correct-horse-battery" },
    });
    fireEvent.click(screen.getByText("registerButton"));

    await waitFor(() => expect(registerMock).toHaveBeenCalled());
    await waitFor(() => expect(pushMock).toHaveBeenCalledWith("/applications"));
  });

  it("registers and redirects to custom redirectUrl on success when redirect param is present", async () => {
    mockSearchParams = new URLSearchParams("redirect=/application/session/sess-abc");
    registerMock.mockResolvedValue({ id: "u1", email: "new@example.com", createdAt: "now" });
    const { default: RegisterForm } = await import("@/features/auth/components/RegisterForm");
    render(<RegisterForm />);

    fireEvent.change(screen.getByLabelText("emailLabel"), {
      target: { value: "new@example.com" },
    });
    fireEvent.change(screen.getByLabelText("passwordLabel"), {
      target: { value: "correct-horse-battery" },
    });
    fireEvent.change(screen.getByLabelText("passwordConfirmationLabel"), {
      target: { value: "correct-horse-battery" },
    });
    fireEvent.click(screen.getByText("registerButton"));

    await waitFor(() => expect(registerMock).toHaveBeenCalled());
    await waitFor(() => expect(pushMock).toHaveBeenCalledWith("/application/session/sess-abc"));
    mockSearchParams = new URLSearchParams();
  });

  it("surfaces the password_mismatch error code as a translated message", async () => {
    registerMock.mockRejectedValue(
      new FakeAuthApiError(422, "Password and confirmation do not match.", "password_mismatch")
    );
    const { default: RegisterForm } = await import("@/features/auth/components/RegisterForm");
    render(<RegisterForm />);

    fireEvent.change(screen.getByLabelText("emailLabel"), {
      target: { value: "new@example.com" },
    });
    fireEvent.change(screen.getByLabelText("passwordLabel"), {
      target: { value: "correct-horse-battery" },
    });
    fireEvent.change(screen.getByLabelText("passwordConfirmationLabel"), {
      target: { value: "different-password" },
    });
    fireEvent.click(screen.getByText("registerButton"));

    await waitFor(() => expect(screen.getByText("error_password_mismatch")).toBeDefined());
    expect(pushMock).not.toHaveBeenCalled();
  });
});
