# Google sign-in setup

LaunchAudit signs users in with Google (OAuth2 code flow). Until this is set
up, the app still works fully: guests can run audits, and the home page
offers a clearly-labelled demo sign-in instead. Setting up Google turns the
demo sign-in off automatically.

No Google OAuth client exists yet. These steps create one.

## 1. Create the OAuth client in Google Cloud

1. Open the [Google Cloud console](https://console.cloud.google.com/) and
   sign in with a Google account you control.
2. Create a project (or pick an existing one). Any name works, e.g.
   `LaunchAudit`.
3. Go to **APIs & Services > OAuth consent screen** and fill in the
   required fields (app name, user support email, developer contact email).
   For a judges-only demo, **External** user type with the app in testing
   mode is fine; add the demo users under **Test users** if testing mode
   asks for them. No scopes beyond the defaults are needed: LaunchAudit
   asks Google only for `openid`, `email` and `profile`.
4. Go to **APIs & Services > Credentials > Create Credentials > OAuth
   client ID**.
5. Choose application type **Web application**.
6. Under **Authorized redirect URIs**, add the backend callback URL:
   - Local development: `http://localhost:8000/auth/google/callback`
   - Production: `{API origin}/auth/google/callback`, where `{API origin}`
     is the deployed backend's base URL (for example
     `https://api.example.com/auth/google/callback`).
   The redirect URI must match exactly, including the path; Google rejects
   the login if it does not.
7. Click **Create**. Google shows a **Client ID** and a **Client secret**.
   Copy both now; the secret is only shown once.

## 2. Set the backend environment variables

On the machine or host that runs the backend, set these three variables:

```env
GOOGLE_CLIENT_ID=<the client ID from step 7>
GOOGLE_CLIENT_SECRET=<the client secret from step 7>
GOOGLE_REDIRECT_URI=<the exact redirect URI from step 6>
```

For local development, put them in `backend/.env` (never commit that file;
it is gitignored). On the production host, set them in the host's own
environment settings. Restart the backend after changing them.

Two related variables:

- `SESSION_SECRET`: a random string of at least 32 characters. Sessions
  cannot be issued without it (Google login and demo login both return
  404). Generate one with, for example,
  `python -c "import secrets; print(secrets.token_urlsafe(32))"`.
- `FRONTEND_URL`: where the backend redirects after a successful Google
  login. Default `http://localhost:3000`; in production set it to the
  deployed frontend origin (for example `https://launchaudit.example.com`).

## 3. Check it works

1. Open the frontend and confirm the home page shows **Sign in with
   Google** (not the demo button).
2. Sign in. You should land back on the home page with your name in the
   header.
3. Run an audit while signed in: it is saved under your email instead of
   as a guest run.

## How it works (summary)

- `GET /auth/google/login` redirects to Google with a signed `state` token
  (10-minute expiry, prevents login CSRF).
- `GET /auth/google/callback` swaps the code for tokens, verifies the ID
  token against Google's tokeninfo endpoint (audience, expiry, verified
  email), creates or updates the user by Google subject id, and issues a
  signed session token (HS256, 30-day expiry).
- The frontend stores the session token in localStorage and sends it as
  `Authorization: Bearer` on API calls. Signing out discards it.
- Demo sign-in is only offered while Google is unconfigured, and is
  labelled demo everywhere. It never pretends to be Google sign-in.
