---
title: PawDesk
emoji: 🐾
colorFrom: yellow
colorTo: green
sdk: docker
app_port: 7860
pinned: false
short_description: Hybrid workflow booking intake desk for pet care
---

# PawDesk

A booking intake desk for pet care businesses (boarding, daycare, grooming). Models read the pet parent's message and vaccine certificate and draft the reply. Code checks the vaccines against the facility's rules, finds a kennel, and makes every decision. Anything risky waits for a staff member, and every step is traced and visible live.

This Space is a public demo:
- **All data is synthetic,** and it resets whenever the Space restarts: the made-up clients and kennels come back, and every request is cleared.
- **Everyone is staff.** You can approve, edit, or decline replies in the review queue. Approved replies are never sent anywhere.
- **Model use is capped** per hour and per day. Once a limit is reached, the Try page says so until it frees up.

Start on the **Try** page: pick a sample request (one is a prompt-injection attempt) or make one up, send it, and watch each step run.
