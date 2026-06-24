# Security Policy

## Supported Versions

This project operates as a continuously deployed Telegram bot. Security updates are only provided for the latest version running on the `main` branch. 

## Scope of Vulnerabilities

Given the nature of this project (a financial Telegram bot with exchange integrations), we are particularly interested in the following **in-scope** vulnerabilities:
* **Authentication/Authorization Bypasses:** Unauthorized access to admin commands (`/admin`) or another user's private financial data.
* **API Key Exposure:** Vulnerabilities that could leak crypto exchange API keys (e.g., Binance, Bybit) or Telegram Bot tokens.
* **Injection Attacks:** NoSQL injection (MongoDB) or command injection via malicious Telegram messages or inline queries.
* **Server-Side Request Forgery (SSRF):** Exploits related to how the bot fetches currency exchange rates or interacts with external APIs.

**Out-of-Scope Vulnerabilities:**
* Vulnerabilities in the Telegram infrastructure or the Telegram Bot API itself.
* Vulnerabilities on the side of third-party cryptocurrency exchanges (Binance, Bybit).
* Denial of Service (DoS) attacks consisting of simply spamming the bot with messages (Telegram's built-in rate limits usually handle this).
* Issues requiring physical access to the server or a user's compromised device.

## Reporting a Vulnerability

We take the security of our users' financial data very seriously. If you discover a security vulnerability, please **DO NOT** open a public GitHub Issue.

Instead, please report the vulnerability privately so we have time to fix it before it becomes public knowledge. 

**How to report:**
1. **GitHub Private Vulnerability Reporting:** If enabled, please use the "Security" tab in this repository to privately report a vulnerability.
2. **Direct Contact:** Alternatively, you can reach out directly to the maintainer via Telegram: **@teferdet**.

**Please include the following in your report:**
* A clear description of the vulnerability and its potential impact.
* Step-by-step instructions to reproduce the issue.
* Any proof-of-concept (PoC) code or screenshots, if applicable.

We will try to acknowledge your report within 48 hours, verify the vulnerability, and keep you updated on our progress toward a patch.
