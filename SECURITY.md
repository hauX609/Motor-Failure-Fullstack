# Security Policy

## Supported Versions

Security updates are applied on the `main` branch.

## Reporting a Vulnerability

Please do not open public issues for security vulnerabilities.

Report privately by email:
- Email: harshit2825@gmail.com
- Subject: `[SECURITY] Motor Failure Fullstack vulnerability report`

Include:
- Affected component (`motor_failure` frontend or `motor_failure_prediction` backend)
- Reproduction steps
- Impact assessment
- Suggested mitigation (if known)

## Secrets and Credentials

- Never commit real secrets to the repository.
- Use env templates (`.env.example`) and local private env files.
- Rotate exposed credentials immediately.

## Security Best Practices for Contributors

- Validate input on all backend routes.
- Keep auth/session logic regression-tested.
- Prefer least-privilege defaults for production config.
- Use dependency updates regularly and patch high/critical vulnerabilities quickly.
