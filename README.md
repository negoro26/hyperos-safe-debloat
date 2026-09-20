# HyperOS safe debloat

A tool to audit, disable, and neutralize bloatware and telemetry on Xiaomi HyperOS and MIUI devices running Android 14, 15, and 16 over ADB.

## What we did to build this

We did not guess which packages to disable. We audited a live device directly.

1. Pulled APKs from the phone and decompiled them with Droid ASC.
   We extracted packages like Joyose, GuardProvider, FashionGallery, and Orange AppCenter directly from the device partitions. Decompiling their DEX bytecode confirmed tracking domains in Joyose such as `tracking.intl.miui.com` and `sdkconfig.ad.xiaomi.com` through Xiaomi's OneTrack SDK. Decompiling FashionGallery confirmed embedded InMobi and Glance ad networks inside the lock screen application.

2. Scanned for commercial spyware and stalkerware using MVT.
   We ran Amnesty International's Mobile Verification Toolkit against all installed applications, running processes, and system properties on the device. We checked 11,481 indicators of compromise covering Pegasus, Predator, and known stalkerware families to confirm the device was clean before modifying settings.

3. Cross-referenced the Universal Android Debloater community database.
   We downloaded the UAD-NG package database and matched it against the phone's 387 installed packages. We pulled their safety ratings to separate safe removals from unsafe packages like `com.miui.rom`, `com.android.updater`, or telephony overlays that trigger bootloops when altered.

4. Solved the Android 14+ SecurityException without uninstalling.
   Modern HyperOS blocks `pm disable-user` on system packages like Joyose with a security exception. Many guides tell users to run `pm uninstall --user 0`, but uninstallation can cause dependency crashes or break camera and biometric integration. We kept all system files intact and used Android's AppOps mechanism to ignore background execution and wake locks instead.

5. Preserved fingerprint drivers and hardware services.
   We explicitly whitelisted Goodix and optical in-display fingerprint packages such as `com.goodix.fingerprint.setting` and `com.fingerprints.optical` so biometric authentication never breaks.

## Target packages

| Package | Purpose on device | How this tool handles it |
| :--- | :--- | :--- |
| `com.xiaomi.joyose` | OneTrack telemetry, cloud profiles, thermal throttling | Ignores background execution and wake locks via AppOps |
| `com.miui.android.fashiongallery` | Lock screen wallpaper carousel and Glance ad network | Disables for user 0 |
| `com.amazon.appmanager` | Preloaded partner telemetry stub | Disables for user 0 |
| `com.mi.global.bbs` | Xiaomi Community app | Disables for user 0 |
| `com.miui.audiomonitor` | Background audio recording monitor | Ignores background execution via AppOps |
| `com.bsp.logmanager` | Hardware logging daemon | Ignores background execution via AppOps |
| `com.debug.loggerui` | MediaTek logging interface | Ignores background execution via AppOps |
| `com.mi.AutoTest` | Factory assembly testing tool | Ignores background execution via AppOps |
| `com.wingtech.sartest` | Wingtech SAR radio frequency test tool | Ignores background execution via AppOps |
| `com.wing.wtsarcontrol` | Wingtech SAR control tool | Ignores background execution via AppOps |
| `com.mediatek.engineermode` | MediaTek Engineer Mode | Ignores background execution via AppOps |
| `com.mediatek.lbs.em2.ui` | MediaTek GPS diagnostic tool | Ignores background execution via AppOps |
| `com.mediatek.ygps` | MediaTek YGPS test utility | Ignores background execution via AppOps |
| `com.xiaomi.mtb` | Baseband diagnostic tool | Ignores background execution via AppOps |
| `com.wdstechnology.android.kryten` | Carrier configuration client | Ignores background execution via AppOps |
| `com.miui.vsimcore` | Virtual SIM service | Ignores background execution via AppOps |
| `com.miui.thirdappassistant` | Third-party app assistant | Ignores background execution via AppOps |
| `com.xiaomi.barrage` | Game bullet screen notification overlay | Ignores background execution via AppOps |
| `com.xiaomi.aiasst.vision` | Assistant visual engine | Ignores background execution via AppOps |

## Prerequisites

1. Install ADB and add it to your system path.
2. Enable USB debugging on the phone in Developer options.
3. Connect the phone to the computer and accept the authorization prompt.
4. Python 3.8 or newer.

## How to use

Check package status:
```bash
python hyperos_debloat.py status
```

Preview changes without modifying the device:
```bash
python hyperos_debloat.py debloat --dry-run
```

Apply the debloat rules:
```bash
python hyperos_debloat.py debloat
```

Run profile-guided AOSP optimization:
```bash
python hyperos_debloat.py dexopt
```

Revert changes and re-enable packages:
```bash
python hyperos_debloat.py restore
```

## License

MIT
