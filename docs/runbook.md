# Runbook: thirdnine.dev

What to do when the uptime monitor alerts or something looks wrong. Work top to bottom and write down times as you go.

## First 5 minutes

1. Acknowledge the alert so you know it reached you.
2. Confirm the problem from a second network: open `https://thirdnine.dev` on your phone with Wi-Fi off.
3. Check the [Cloudflare status page](https://www.cloudflarestatus.com) for a provider incident.
4. Start an entry in the incident log below with the start time.

## Site down or showing errors

| What you see | Likely cause | What to do |
| --- | --- | --- |
| Broken layout or wrong content right after a push | A bad deploy | Cloudflare dashboard → Workers & Pages → this project → **Deployments**. Open the three-dot menu on the last good production deployment and choose **Rollback to this deployment**. The switch is immediate. Then fix the problem on a branch. |
| Error 522, or "this site can't be reached" | Custom domain or DNS problem | In the Pages project, open **Custom domains** and check that `thirdnine.dev` shows as active. In the DNS tab, check that nobody edited or deleted its records. |
| Certificate or "connection not private" warning | Certificate not issued or renewed | Check the domain's status under **Custom domains**. Every `.dev` site must load over HTTPS, so this is a full outage until fixed. |
| Cloudflare reports an incident | Provider outage | Nothing to fix locally. Post a short note to clients if it lasts more than 15 minutes, and log the time. |
| Domain doesn't resolve at all | Domain registration lapsed | Renew at the registrar and turn on auto-renew. |

## Email to `hello@thirdnine.dev` not arriving

1. Cloudflare dashboard → the domain → **Email Routing**: check that the route is enabled and the destination address is verified.
2. In the DNS tab, check that the MX and TXT records Email Routing added are still there.
3. Check the Gmail spam folder.

## After any incident

Within two business days, add a short postmortem to the log: what happened, how many minutes it was down, how it was noticed, how it was fixed, and one change that stops it from happening the same way again. No blame, just the timeline and the fix.

## Incident log

| Date | Minutes down | Cause | Fix | Follow-up |
| --- | --- | --- | --- | --- |
| | | | | |
