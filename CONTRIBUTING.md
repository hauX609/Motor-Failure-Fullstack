# Contributing

Thanks for contributing to Motor Failure Fullstack.

## Branching
- Create a feature branch from `main`.
- Use clear branch names, for example:
  - `feat/dashboard-trend-fix`
  - `fix/alerts-normalization`

## Commit Messages
- Keep commits focused and small.
- Use imperative style:
  - `Fix alert trend normalization`
  - `Add motor location support`

## Local Validation Before PR

Frontend:
```bash
cd motor_failure
npm run build
```

Backend:
```bash
cd motor_failure_prediction
python3 -m py_compile app.py
```

## Pull Requests
- Explain what changed and why.
- Include screenshots for UI changes.
- Mention any env/config changes required.
- Link related issue (if applicable).

## Security
- Never commit real secrets.
- Use `.env.example` templates and local `.env.*` files.
