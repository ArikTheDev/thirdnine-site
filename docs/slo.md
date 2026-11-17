# Service level objective: thirdnine.dev

The site's reliability target, how it's measured, and what happens when it's at risk. It's the same structure Third Nine sets up for clients.

## Objective

**99.9% of availability checks succeed over any rolling 30-day window.**

## How it's measured

- An external uptime monitor requests `https://thirdnine.dev/` on a fixed interval. Free plans typically check every 3 to 5 minutes.
- A check succeeds when the response is HTTP 200 within 5 seconds. Where the monitor supports keyword checks, it also confirms the page contains "Third Nine", so a blank or wrong page counts as down.
- The indicator is successful checks divided by total checks over the last 30 days.

## Error budget

30 days is 43,200 minutes. Allowing 0.1% of that gives a budget of **43.2 minutes of downtime per 30 days**. With 5-minute checks, that's about 8 failed checks.

| Budget used in the window | What happens |
| --- | --- |
| Under 50% | Normal. Changes can ship any time. |
| 50% to 100% | Only fixes ship. Review the follow-ups from the last incident. |
| Over 100% | Freeze everything except reliability fixes until the window recovers, and write a postmortem. |

## Alerting

- **Page:** two consecutive failed checks send a phone alert. With 5-minute checks, an outage can run up to 10 minutes before that alert, so move to 1-minute checks before promising clients faster response.
- **Email:** TLS certificate expiry within 14 days, and domain registration expiry within 30 days.

## Why 99.9%

Three nines allows about 43 minutes of downtime a month. That's enough time for a person to be alerted, find the cause and roll back, which matches a one-person on-call setup. Each extra nine cuts the allowance tenfold: 99.99% leaves about 4 minutes a month, which only automatic recovery can meet.

## Review

Look at this page monthly, alongside the incident log in [runbook.md](runbook.md). Change the target only after a quarter of data.
