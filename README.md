# HyperOS safe debloat

A guide and toolset to audit, inspect, and safely debloat Xiaomi HyperOS and MIUI devices running Android 14, 15, and 16 over ADB.

## Audit methodology

Package selections in this project come from a direct audit of a live device, rather than unverified debloat lists.

1. Bytecode decompilation with Droid ASC.
   Installed APK files were extracted from device partitions and decompiled using Droid ASC. Inspecting classes in `com.xiaomi.joyose` revealed the embedded OneTrack SDK communicating with tracking endpoints including `tracking.intl.miui.com` and `sdkconfig.ad.xiaomi.com`. Decompiling `com.miui.android.fashiongallery` confirmed embedded InMobi, Google AdMob, and Glance SDK ad components running inside the lock screen application.

2. Forensic spyware scan with MVT.
   Amnesty International's Mobile Verification Toolkit scanned installed package identifiers, active memory processes, and system properties against 11,481 indicators of compromise covering Pegasus, Predator, and commercial stalkerware families to confirm the device baseline was clean.

3. Cross-referencing the Universal Android Debloater database.
   Installed packages were matched against the UAD-NG database to identify community safety ratings. Packages marked unsafe, such as `com.miui.rom`, `com.android.updater`, and low-level telephony overlays, are excluded to prevent bootloops.

4. Resolving the Android 14+ SecurityException.
   Modern HyperOS blocks `pm disable-user` on system packages like Joyose, returning `SecurityException: Cannot disable system packages`. Conventional debloaters often resort to `pm uninstall --user 0`, which removes package registrations and risks breaking dependent system services. This tool uses Android's AppOps mechanism (`RUN_IN_BACKGROUND: ignore`, `RUN_ANY_IN_BACKGROUND: ignore`, `WAKE_LOCK: ignore`) to freeze the package and halt background execution while leaving the underlying files untouched.

5. Hardware and biometric protection.
   Optical and Goodix in-display fingerprint components (`com.goodix.fingerprint.setting`, `com.fingerprints.optical`) remain whitelisted to ensure biometric authentication continues to function.

## Target packages

| Package | Purpose on device | Neutralization method |
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
| `com.miui.thirdappassistant` | Third-party app assistant | Ignores background execution via AppOps |
| `com.xiaomi.barrage` | Game bullet screen notification overlay | Ignores background execution via AppOps |
| `com.xiaomi.aiasst.vision` | Assistant visual engine | Ignores background execution via AppOps |

## Prerequisites

1. Install ADB and add it to your system path.
2. Enable USB debugging on the phone in Developer options:
   - Go to Settings > About phone and tap OS Version seven times.
   - Go to Settings > Additional settings > Developer options and turn on USB debugging.
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

Run an MVT forensic scan against Amnesty International indicators:
```bash
python hyperos_debloat.py scan-spyware
```

Audit and extract a package APK for Droid ASC inspection:
```bash
python hyperos_debloat.py audit-apk com.xiaomi.joyose
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
