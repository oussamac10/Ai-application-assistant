# User Accounts and Persistent Sessions — User Guide

**Phase:** 12
**Feature:** User Accounts and Persistent Sessions

---

## Overview

You can complete an application anonymously, exactly as before — nothing about the anonymous flow has changed. If you create an account, you can additionally:

- **Save** an application you started anonymously into your account.
- **Resume** any saved application later, from any device, without needing the original browser tab.
- **Rename** and **delete** saved applications.

Creating an account is optional. An anonymous application still works end to end (fill in fields, review, export) without ever signing in.

---

## How to use it

### Creating an account

Click **Register** (top-right of any page), enter your email and a password (at least 10 characters), and confirm it. You're signed in immediately after registering.

### Signing in and out

Click **Log in** / **Log out** in the same top-right menu at any time.

### Saving (claiming) an anonymous application

While filling in an application you started anonymously, a **Save this application?** prompt appears. If you're already signed in, click **Save to my account**. If not, click **Log in to save**, sign in or register, then return to the application to save it. Saving does not restart or duplicate your progress — your existing answers stay exactly as they were.

Once saved, the browser-local credentials that used to grant access to that application stop working — only your account can access it from then on.

### My Applications

Click **My Applications** to see everything you've saved: its form, current status, and progress. From there you can:

- **Resume** — continues exactly where you left off.
- **Rename** — give it a memorable name instead of the default form name.
- **Delete** — removes it from your account. This cannot be undone.

---

## Privacy and security notes

- Passwords are never stored in a reversible form — only a salted Argon2id hash.
- Your session cookie is not readable by page scripts and is never placed in a URL.
- Only you can see, resume, rename, or delete your own saved applications.
- Deleting an application does not un-delete it — there is no recovery.

---

## Related

- [`docs/decisions/0011-user-accounts-persistent-sessions.md`](decisions/0011-user-accounts-persistent-sessions.md) — architecture decisions
- [`docs/security.md`](security.md) — general security posture
- [`docs/privacy.md`](privacy.md) — data retention and privacy principles
