# JioHotstar Premium AutoBuild

[![CI](https://github.com/gramnaters/zeo/actions/workflows/ci.yml/badge.svg)](https://github.com/gramnaters/zeo/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/gramnaters/zeo?label=release)](https://github.com/gramnaters/zeo/releases/latest)
[![Downloads](https://img.shields.io/github/downloads/gramnaters/zeo/total)](https://github.com/gramnaters/zeo/releases)

Automated JioHotstar patcher — builds a ready-to-install APK, updated every 6 hours.

Get the [latest release](https://github.com/gramnaters/zeo/releases/latest).

<!-- LATEST_BUILD_START -->
| Build | Version | APK |
|-------|---------|-----|
| `260115` | `26.10.12.2` | [Download](https://github.com/gramnaters/zeo/releases/download/260115/JioHotstar-Premium-v26.10.12.2-arm64.apk) |
<!-- LATEST_BUILD_END -->

## Install

- **Obtainium** (auto-updates): [![Add to Obtainium](https://raw.githubusercontent.com/ImranR98/Obtainium/refs/heads/main/assets/graphics/badge_obtainium.png)](https://apps.obtainium.imranr.dev/redirect?r=obtainium%3A%2F%2Fapp%2F%7B%22id%22%3A%22in.startv.hotstar%22%2C%22url%22%3A%22https%3A%2F%2Fgithub.com%2Fgramnaters%2Fzeo%22%7D)
- **Manual**: grab the APK from [Releases](https://github.com/gramnaters/zeo/releases)

<details>
<summary><b>How it works</b></summary>

A scheduled GitHub Action checks for new JioHotstar versions every 6 hours.
When one appears, it downloads, patches, re-signs, and publishes it as a
release automatically — no manual steps needed.

</details>

## Disclaimer

Unofficial modification of JioHotstar for personal use only. Not affiliated with JioStar or Disney.
