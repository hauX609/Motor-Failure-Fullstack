# Release Checklist

## Pre-Release

- [ ] Verify `main` is stable and CI/local checks pass
- [ ] Confirm no real secrets are present in tracked files
- [ ] Update environment templates if configuration changed
- [ ] Review open critical bugs and known risks

## Backend Release Checks

- [ ] `motor_failure_prediction/.env.production` values validated
- [ ] `MOTOR_API_KEY` and SMTP credentials rotated/valid
- [ ] `CORS_ALLOWED_ORIGINS` contains correct production domains
- [ ] `RUN_DATA_GENERATOR` setting confirmed for target environment
- [ ] Startup script runs successfully (`./run_prod.sh`)

## Frontend Release Checks

- [ ] `motor_failure/.env.production` has correct API URL
- [ ] Mock mode disabled in production (`VITE_USE_MOCK_DATA=false`)
- [ ] Build succeeds (`npm run build`)
- [ ] Dashboard and alerts pages render with live API data

## Data and Observability

- [ ] DB backup created before deployment
- [ ] Logs/monitoring paths verified
- [ ] Health/readiness endpoints return expected status

## Post-Release Verification

- [ ] Login, dashboard, motors, alerts, and prediction flows smoke-tested
- [ ] Alerts trend updates with fresh events
- [ ] No spike in 4xx/5xx errors after deploy
- [ ] Rollback plan is documented and ready
