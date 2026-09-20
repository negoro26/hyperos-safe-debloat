# HyperOS Safe Debloat 🛡️⚡

A safe, non-destructive debloating and telemetry neutralization tool for **Xiaomi HyperOS & MIUI** devices running **Android 14, 15, and 16**.

Unlike conventional debloaters that rely on destructive uninstalls (`pm uninstall`) which can trigger bootloops or break camera/biometrics on modern Xiaomi devices, **HyperOS Safe Debloat** uses an **AppOps Neutralization Fallback** specifically designed for Android 14+ system security policies.

---

## Key Features

- **Zero-Uninstall Guarantee**: Never runs `pm uninstall` or modifies `/system`/`/product` read-only partitions. Completely reversible.
- **Android 14/15/16 SecurityException Workaround**: On newer Android releases, `pm disable-user` on system packages (such as `com.xiaomi.joyose`) fails with `SecurityException: Cannot disable system packages`. This tool automatically falls back to revoking background execution (`RUN_IN_BACKGROUND: ignore`, `RUN_ANY_IN_BACKGROUND: ignore`, and `WAKE_LOCK: ignore`), freezing telemetry daemons in place.
- **Biometrics & Hardware Whitelist**: Explicitly protects optical and Goodix in-display fingerprint drivers (`com.goodix.fingerprint.setting`, `com.fingerprints.optical`) and core system frameworks.
- **AOSP Idle Profile Compilation**: Triggers official profile-guided background dexopt (`cmd package bg-dexopt-job`) to compile frequently used hot methods without bloating storage or wasting battery.
- **Dynamic Refresh Rate Preservation**: Respects display battery conservation policy (avoids forced 120Hz locks that drain battery).

---

## Target Bloatware & Telemetry Matrix

| Target Package | Role / Threat | Neutralization Method |
| :--- | :--- | :--- |
| `com.xiaomi.joyose` | OneTrack telemetry framework, cloud profiles, game & thermal throttling | **AppOps Background Freeze** |
| `com.miui.android.fashiongallery` | Lock-screen Wallpaper Carousel / Glance (InMobi, AdMob, AppsFlyer) | **User-space Disable** |
| `com.amazon.appmanager` | Preloaded partner telemetry stub | **User-space Disable** |
| `com.mi.global.bbs` | Xiaomi Community forums and tracking | **User-space Disable** |
| `com.miui.audiomonitor` | Audio recording monitor service | **AppOps Background Freeze** |
| `com.bsp.logmanager` | Board Support Package hardware logger | **AppOps Background Freeze** |
| `com.debug.loggerui` | MediaTek graphics/video diagnostic interface | **AppOps Background Freeze** |
| `com.mi.AutoTest` | OEM factory assembly testing suite | **AppOps Background Freeze** |
| `com.wingtech.sartest` | Wingtech ODM SAR testing daemon | **AppOps Background Freeze** |
| `com.wing.wtsarcontrol` | Wingtech ODM SAR RF control daemon | **AppOps Background Freeze** |
| `com.mediatek.engineermode` | MediaTek Engineer Mode utility | **AppOps Background Freeze** |
| `com.mediatek.lbs.em2.ui` | MediaTek GPS testing utility | **AppOps Background Freeze** |
| `com.mediatek.ygps` | MediaTek YGPS diagnostic utility | **AppOps Background Freeze** |
| `com.xiaomi.mtb` | Modem Test Box (baseband diagnostic tool) | **AppOps Background Freeze** |
| `com.wdstechnology.android.kryten`| WDS Carrier OTA Access Point Configurator | **AppOps Background Freeze** |
| `com.miui.vsimcore` | Virtual SIM background service | **AppOps Background Freeze** |
| `com.miui.thirdappassistant` | Third-party app assistant daemon | **AppOps Background Freeze** |
| `com.xiaomi.barrage` | Game bullet screen notification overlay | **AppOps Background Freeze** |
| `com.xiaomi.aiasst.vision` | Background AI assistant visual engine | **AppOps Background Freeze** |

---

## Prerequisites

1. **ADB (Android Debug Bridge)** installed and accessible.
2. **USB Debugging** enabled on your Xiaomi device:
   - Go to **Settings > About phone** and tap **OS Version** 7 times to enable Developer options.
   - Go to **Settings > Additional settings > Developer options** and enable **USB debugging**.
   - Connect phone to PC and tap **"Always allow from this computer"**.
3. **Python 3.8+** installed.

---

## Usage

### 1. Check Status
Inspect the current state of all tracked bloatware and telemetry packages:
```bash
python hyperos_debloat.py status
```

### 2. Preview Changes (Dry-Run)
Simulate debloating without modifying anything on the device:
```bash
python hyperos_debloat.py debloat --dry-run
```

### 3. Apply Safe Debloat
Disable safe user packages and freeze protected system daemons via AppOps:
```bash
python hyperos_debloat.py debloat
```

### 4. Trigger AOSP Profile-Guided Dexopt (Optional)
Run the official Android idle maintenance job to optimize app execution speed:
```bash
python hyperos_debloat.py dexopt
```

### 5. Restore / Revert All Changes
If you ever want to re-enable everything and restore default permissions:
```bash
python hyperos_debloat.py restore
```

---

## License

MIT License. See [LICENSE](LICENSE) for details.
