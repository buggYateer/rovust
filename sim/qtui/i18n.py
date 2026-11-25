"""English / Egyptian Arabic for the desktop interface.

Arabic here is how people in Egypt actually talk about the robot, not a
word-for-word translation. Widgets ask ``tr(key, *args)`` for text and
re-read it when ``LANG.changed`` fires; Arabic also flips the layout to
right-to-left.
"""
from __future__ import annotations

from PySide6.QtCore import QObject, QSettings, Qt, Signal
from PySide6.QtWidgets import QApplication

STR = {
    "en": {
        # window chrome
        "appTitle": "Multi-Environment Exploration Rover",
        "mFile": "&File", "mMission": "&Mission", "mView": "&View", "mHelp": "&Help", "mSpeed": "&Speed",
        "newMission": "&New mission", "restartMission": "&Restart mission", "exit": "E&xit",
        "sendReport": "Send report", "openReports": "Open reports &folder", "reportSettings": "Report se&ttings...",
        "pause": "Pause", "resume": "Resume", "stopMission": "Stop", "restart": "Restart", "lights": "Lights",
        "homeNow": "Return &home now", "darkMode": "&Dark mode", "guide": "&User guide", "controls": "&Controls", "about": "&About",
        "showSetup": "Mission setup panel", "showTele": "Telemetry panel", "language": "عربي",
        "console": "Phone console", "consoleOn": "Console on", "mission": "Mission", "noMission": "no mission yet",
        "stopTip": "End the mission here and keep everything on screen (you can still send a report)",
        "reportTip": "Save a report of this mission (statistics + maps) and upload it to the team's Drive folder",
        "themeTip": "Light / dark", "langTip": "Switch to Arabic",
        # setup panel
        "setup": "Mission setup", "collapse": "Hide the panel", "expand": "Show the panel",
        "env": "Environment", "cave": "Cave", "mars": "Mars", "underwater": "Underwater",
        "strategy": "Exploration strategy", "frontier": "Nearest frontier", "dfs": "DFS + backtrack", "utility": "Utility (AI)",
        "loc": "Localisation", "fused": "Fused", "fusedS": "gyro + heading + flow", "odometry": "Encoders", "odometryS": "wheels only",
        "perfect": "Perfect", "perfectS": "reference",
        "options": "Options", "ai": "AI: terrain classifier + fault detector", "seed": "Seed", "seedHint": "same seed = same world",
        "start": "Start mission",
        "remote": "Remote control", "autonomous": "Auto", "assisted": "Assisted", "manual": "Manual",
        "autonomousTip": "The rover drives itself", "assistedTip": "You steer, the safety layers stay on",
        "manualTip": "You drive, nothing stops you",
        "lossL": "If the link drops", "lossHome": "Return home", "lossExplore": "Explore alone", "lossHold": "Wait for the link",
        "openConsole": "Open console for phone / tablet", "closeConsole": "Close console",
        "openOn": "On a phone or tablet on the same Wi-Fi, open:", "copy": "Copy the address", "copied": "Copied",
        "consoleErr": "Could not start the console: {}",
        "keys": "Arrow keys or W A S D drive the rover in Assisted and Manual.",
        "padOff": "No controller", "padMapPs": "✕ gas · △ reverse · stick or arrows steer · Start stop · ○ lights · □ home · L1/R1 mode. Start a mission first.", "padMap": "A gas · Y reverse · stick or arrows steer · Start stop · B lights · X home · LB/RB mode. Start a mission first.", "qrTip": "Scan it with the phone camera. Click to make it bigger.", "padHow": "Plug it in or pair it, then press any button", "newBtn": "New mission",
        "padOn": "Controller: {}", "padMissing": "Controller support needs pygame-ce (pip install pygame-ce)",
        "layers": "Map layers", "sonar": "Sonar", "ir": "IR beams", "terrain": "Terrain (AI)", "frontiers": "Frontiers",
        "visited": "Visited", "true_path": "True path",
        "envBlurb_cave": "Narrow branching corridors, dead ends, darkness, mud, pits and gas pockets. Short sonar range; iron in the rock disturbs the compass.",
        "envBlurb_mars": "Open terrain with rock fields, craters and sandy ground with heavy wheel slip. No magnetic field: heading comes from a sun sensor.",
        "envBlurb_underwater": "Flooded site with reef walls, mud flats and a steady current. Thrusters, sonar and a DVL instead of wheels, light and encoders.",
        # KPIs
        "kCov": "Mapped", "kDist": "Distance", "kBatt": "Battery", "kLink": "Link", "kBeh": "Behaviour", "kErr": "Position error",
        "linkNone": "not used",
        # maps
        "world": "True world", "worldS": "the robot never sees this", "belief": "Robot's map", "beliefS": "built from its own sensors",
        "enlargeTip": "Click to open a large live view", "noMissionMap": "No mission running",
        "missionOver": "MISSION OVER", "startNew": "Start again: New mission, or Restart (R).",
        "popupHint": "Live view. Click the small map again or close this window to return. Esc closes.",
        "legend": ["true path", "fused estimate", "encoders only", "planned path", "frontiers / target", "hazard", "sonar echo", "IR beam", "cliff switch"],
        # telemetry
        "tSens": "Sensors", "tMotor": "Motor control", "tStats": "Statistics", "tRadio": "Radio link", "tEvents": "Events",
        "teleCollapse": "Fold the telemetry", "teleExpand": "Open the telemetry",
        "thSensor": "Sensor", "thClass": "Type", "thReading": "Reading", "thFault": "Inject fault", "thHealth": "Health",
        "ok": "ok", "stuck": "stuck", "dead": "dead", "noisy": "noisy",
        "fOkTip": "sensor works", "fStuckTip": "keeps reporting its last value", "fDeadTip": "reports nothing", "fNoisyTip": "very noisy readings",
        "hOk": "ok", "hInjected": "injected", "hFaulty": "ignored",
        "camera": "Camera", "aiSays": "AI says: {} ({:.0%})", "truth": "truth: {}",
        "faultMsg": "Fault detector: {} looks {} - no longer used",
        "evEmpty": "Nothing has happened yet.", "evEnded": "{} · over",
        # end reasons
        "endFell": "The rover fell into a pit.", "endFellManual": "The rover fell into a pit while being driven in manual mode (the cliff layer was switched off).",
        "endBattery": "The battery is empty.", "endStopped": "Stopped by the operator.", "endBack": "The rover is back at the base.",
        "endBackWhy": "The rover is back at the base - {}.",
        "why_explored": "the map is complete", "why_battery": "the battery was only just enough to get back",
        "why_link lost": "the radio link was lost", "why_operator": "you asked it to",
        # status
        "st_exploring": "Exploring", "st_returning": "Returning", "st_returned": "Back at base", "st_stopped": "Stopped",
        "st_fell": "Fell", "st_battery_dead": "Battery empty", "st_paused": "Paused", "st_ready": "Ready",
        "ready": "Ready",
        "sbLink": "Link", "sbCov": "Mapped", "sbBeh": "Behaviour",
        "reportsWaiting": "{} report(s) waiting to upload", "startFirst": "start a mission first",
        "reportSaved": "report saved - uploading...", "reportLocal": "report saved locally ({}) - set the Drive bridge in File > Report settings",
        # alerts (keys shared with the phone console, see sim/alerts.py)
        "a_ok": "All good", "a_mud": "mud", "a_sand": "soft sand",
        "a_stuck": "Stuck in {} · wheels slipping {}%", "a_stuck_end": "Got out of the {}",
        "a_linkWeak": "Weak signal · {}% · commands may drop", "a_linkLost": "Link lost · the rover is on its own",
        "a_batt": "Battery low · {}% · it heads home by itself", "a_gas": "Gas here · {}% · careful",
        "a_faultAi": "{} failed · the AI stopped trusting it", "a_faultNoAi": "{} failed · the rover still trusts it",
        "a_dark": "Too dark for the camera", "a_darkBtn": "Lights on", "a_paused": "Mission paused", "a_ended": "Mission over",
        "a_tip": "Click to see everything that happened",
    },
    "ar": {
        "appTitle": "روبوت بيستكشف أي مكان",
        "mFile": "ملف", "mMission": "المهمة", "mView": "عرض", "mHelp": "مساعدة", "mSpeed": "السرعة",
        "newMission": "مهمة جديدة", "restartMission": "عيد المهمة", "exit": "اقفل البرنامج",
        "sendReport": "ابعت التقرير", "openReports": "افتح فولدر التقارير", "reportSettings": "إعدادات التقارير...",
        "pause": "وقّف", "resume": "كمّل", "stopMission": "خلّص المهمة", "restart": "عيدها", "lights": "النور",
        "homeNow": "رجّعه دلوقتي", "darkMode": "الوضع الغامق", "guide": "إزاي تستخدمه", "controls": "الزراير", "about": "عن المشروع",
        "showSetup": "بانل تجهيز المهمة", "showTele": "بانل الأرقام", "language": "English",
        "console": "سوق من الموبايل", "consoleOn": "الموبايل شغال", "mission": "مهمة", "noMission": "لسه مفيش مهمة",
        "stopTip": "خلّص المهمة هنا وسيب كل حاجة على الشاشة (تقدر تبعت تقرير بعدها)",
        "reportTip": "احفظ تقرير بالأرقام والخرايط وارفعه على فولدر الدرايف بتاع التيم",
        "themeTip": "فاتح / غامق", "langTip": "English",
        "setup": "تجهيز المهمة", "collapse": "اقفل البانل", "expand": "افتح البانل",
        "env": "هيستكشف فين؟", "cave": "كهف", "mars": "المريخ", "underwater": "تحت المية",
        "strategy": "هيدوّر إزاي؟", "frontier": "أقرب حتة مجهولة", "dfs": "للآخر وبعدين يرجع", "utility": "بالذكاء الاصطناعي",
        "loc": "هيعرف هو فين إزاي؟", "fused": "كل الحساسات", "fusedS": "جيرو + اتجاه + حركة", "odometry": "العجل بس", "odometryS": "بيعدّ اللفات",
        "perfect": "بالظبط", "perfectS": "للمقارنة بس",
        "options": "إضافات", "ai": "ذكاء اصطناعي يعرف الأرض ويلقط الحساس البايظ", "seed": "رقم الخريطة", "seedHint": "نفس الرقم = نفس الخريطة",
        "start": "يلا نبدأ",
        "remote": "السواقة من بعيد", "autonomous": "لوحده", "assisted": "إنت + هو", "manual": "إنت اللي سايق",
        "autonomousTip": "الروبوت بيسوق نفسه", "assistedTip": "إنت بتوجّهه، وهو بيحمي نفسه من الخبط والوقعة",
        "manualTip": "إنت اللي سايق ومفيش حاجة هتوقفه",
        "lossL": "لو الإشارة فصلت", "lossHome": "يرجع مكان ما بدأ", "lossExplore": "يكمّل لوحده", "lossHold": "يستنى الإشارة",
        "openConsole": "افتح السواقة من الموبايل", "closeConsole": "اقفل السواقة من الموبايل",
        "openOn": "افتح اللينك ده من أي موبايل على نفس الواي فاي:", "copy": "انسخ اللينك", "copied": "اتنسخ",
        "consoleErr": "معرفناش نشغّل السواقة من الموبايل: {}",
        "keys": "تقدر تسوقه بالأسهم أو W A S D.",
        "padOff": "مفيش دراع متوصل", "padMapPs": "✕ بنزين · △ ورا · العصاية أو الأسهم للاتجاه · Start وقّف · ○ النور · □ رجوع · L1/R1 الوضع. ابدأ مهمة الأول.", "padMap": "A بنزين · Y ورا · العصاية أو الأسهم للاتجاه · Start وقّف · B النور · X رجوع · LB/RB الوضع. ابدأ مهمة الأول.", "qrTip": "صوّره بكاميرا الموبايل. دوس عليه علشان يكبر.", "padHow": "وصّله أو اعمله pair ودوس أي زرار فيه", "newBtn": "مهمة جديدة",
        "padOn": "الدراع: {}", "padMissing": "علشان الدراع يشتغل لازم pygame-ce (pip install pygame-ce)",
        "layers": "يظهر على الخريطة", "sonar": "السونار", "ir": "الأشعة تحت الحمرا", "terrain": "نوع الأرض", "frontiers": "اللي لسه مجهول",
        "visited": "عدّى منين", "true_path": "مشي منين فعلاً",
        "envBlurb_cave": "ممرات ضيقة بتتفرع وطرق مسدودة، ضلمة وطين وحفر وجيوب غاز. السونار مبيشوفش بعيد، والحديد اللي في الصخر بيلخبط البوصلة.",
        "envBlurb_mars": "أرض مفتوحة، صخور وحفر ورمل طري العجل بيغرز فيه. مفيش مغناطيسية، فبيعرف اتجاهه من الشمس.",
        "envBlurb_underwater": "مكان غرقان فيه شعاب وطين وتيار شغال على طول. بيتحرك بمراوح بدل العجل، وبيشوف بالسونار.",
        "kCov": "اتكشف", "kDist": "مشي", "kBatt": "البطارية", "kLink": "الإشارة", "kBeh": "بيعمل إيه", "kErr": "تايه قد إيه",
        "linkNone": "مش مستخدمة",
        "world": "المكان على حقيقته", "worldS": "الروبوت مش شايف ده", "belief": "اللي الروبوت شايفه", "beliefS": "من حساساته بس",
        "enlargeTip": "دوس علشان تكبّر الخريطة", "noMissionMap": "مفيش مهمة شغالة",
        "missionOver": "المهمة خلصت", "startNew": "ابدأ تاني: مهمة جديدة، أو عيدها (R).",
        "popupHint": "عرض حي. دوس على الخريطة الصغيرة تاني أو اقفل الشباك ده علشان ترجع. Esc بيقفله.",
        "legend": ["مشي منين فعلاً", "فاكر إنه مشي منين", "حسب العجل", "ناوي يروح منين", "لسه مجهول / رايح فين", "خطر", "صدى السونار", "شعاع الأشعة", "حساس الحافة"],
        "tSens": "الحساسات", "tMotor": "الموتور", "tStats": "أرقام المهمة", "tRadio": "الإشارة", "tEvents": "اللي حصل",
        "teleCollapse": "صغّر الأرقام", "teleExpand": "افتح الأرقام",
        "thSensor": "الحساس", "thClass": "نوعه", "thReading": "بيقرا كام", "thFault": "جرّب عطل", "thHealth": "حالته",
        "ok": "سليم", "stuck": "معلّق", "dead": "ميت", "noisy": "مشوّش",
        "fOkTip": "شغال عادي", "fStuckTip": "بيفضل يقول آخر رقم", "fDeadTip": "مبيقولش حاجة", "fNoisyTip": "أرقامه بتتنطط",
        "hOk": "تمام", "hInjected": "عطل مقصود", "hFaulty": "مش بنصدّقه",
        "camera": "الكاميرا", "aiSays": "الذكاء الاصطناعي بيقول: {} ({:.0%})", "truth": "الحقيقة: {}",
        "faultMsg": "{} شكله {}، فبطّلنا نعتمد عليه",
        "evEmpty": "لسه محصلش حاجة.", "evEnded": "{} · خلاص",
        "endFell": "الروبوت وقع في حفرة.", "endFellManual": "الروبوت وقع في حفرة وإنت سايق يدوي (حماية الحافة كانت مقفولة).",
        "endBattery": "البطارية خلصت.", "endStopped": "إنت اللي خلّصت المهمة.", "endBack": "الروبوت رجع مكان ما بدأ.",
        "endBackWhy": "الروبوت رجع مكان ما بدأ - {}.",
        "why_explored": "كشف الخريطة كلها", "why_battery": "البطارية كانت يادوب تكفّي الرجوع",
        "why_link lost": "الإشارة فصلت", "why_operator": "إنت طلبت منه",
        "st_exploring": "بيستكشف", "st_returning": "راجع", "st_returned": "رجع", "st_stopped": "خلصت",
        "st_fell": "وقع", "st_battery_dead": "البطارية خلصت", "st_paused": "واقف", "st_ready": "جاهز",
        "ready": "جاهز",
        "sbLink": "الإشارة", "sbCov": "اتكشف", "sbBeh": "بيعمل إيه",
        "reportsWaiting": "{} تقرير مستني يترفع", "startFirst": "ابدأ مهمة الأول",
        "reportSaved": "التقرير اتحفظ - بيترفع...", "reportLocal": "التقرير اتحفظ على الجهاز ({}) - حط لينك الدرايف من ملف > إعدادات التقارير",
        "a_ok": "كله تمام", "a_mud": "الطين", "a_sand": "الرمل الطري",
        "a_stuck": "غارز في {} · العجل بيزحلق {}%", "a_stuck_end": "طلع من {}",
        "a_linkWeak": "الإشارة ضعيفة · {}% · ممكن أوامر تضيع", "a_linkLost": "الإشارة فصلت · الروبوت بيتصرف لوحده",
        "a_batt": "البطارية بتخلص · {}% · هيرجع لوحده", "a_gas": "فيه غاز هنا · {}% · خلّي بالك",
        "a_faultAi": "{} باظ · الذكاء الاصطناعي بطّل يصدّقه", "a_faultNoAi": "{} باظ · والروبوت لسه مصدّقه!",
        "a_dark": "الدنيا ضلمة والكاميرا مش شايفة", "a_darkBtn": "ولّع النور", "a_paused": "المهمة واقفة", "a_ended": "المهمة خلصت",
        "a_tip": "دوس علشان تشوف كل اللي حصل",
    },
}

# behaviour names from sim/behaviors.py, as the operator would say them
BEHAVIOURS = {
    "en": {"STOP": "Emergency stop", "ESCAPE": "Backing off a bump", "CLIFF": "Stopped at an edge", "SLOPE": "Too steep",
           "SCAN": "Looking around", "AVOID": "Avoiding a wall", "TELEOP": "You drive", "HOME": "Going home",
           "EXPLORE": "Exploring", "WANDER": "Wandering", "HOLD": "Waiting for the link"},
    "ar": {"STOP": "وقف طوارئ", "ESCAPE": "بيرجع لورا من خبطة", "CLIFF": "وقف عند حافة", "SLOPE": "الطلعة صعبة",
           "SCAN": "بيبص حواليه", "AVOID": "بيتفادى حيطة", "TELEOP": "إنت اللي سايق", "HOME": "راجع مكان ما بدأ",
           "EXPLORE": "بيستكشف", "WANDER": "بيتمشّى", "HOLD": "مستني الإشارة"},
}


class _Lang(QObject):
    changed = Signal(str)

    def __init__(self):
        super().__init__()
        self.code = "en"

    def set(self, code: str):
        code = code if code in STR else "en"
        self.code = code
        app = QApplication.instance()
        if app is not None:
            app.setLayoutDirection(Qt.LayoutDirection.RightToLeft if code == "ar" else Qt.LayoutDirection.LeftToRight)
        QSettings("RoboticsTeamProject", "RoverSimulator").setValue("lang", code)
        self.changed.emit(code)

    @property
    def rtl(self) -> bool:
        return self.code == "ar"


LANG = _Lang()


def saved_language() -> str:
    return str(QSettings("RoboticsTeamProject", "RoverSimulator").value("lang", "en"))


def tr(key: str, *args):
    s = STR[LANG.code].get(key)
    if s is None:
        s = STR["en"].get(key, key[2:] if key[:2] in ("g_", "c_") else key)
    return s.format(*args) if args and isinstance(s, str) else s


def behaviour(name: str) -> str:
    return BEHAVIOURS[LANG.code].get(name, name.title())


def alert_text(a) -> str:
    """Words for an alert from sim/alerts.py."""
    k, args = a.key, a.args
    if k == "stuck":
        return tr("a_stuck", tr("a_" + args[0]), args[1])
    if k == "fault":
        return tr("a_faultAi" if args[1] else "a_faultNoAi", args[0])
    if k in ("linkWeak", "batt", "gas"):
        return tr("a_" + k, args[0])
    return tr("a_" + k)


def alert_end_text(a) -> str:
    if a.key == "stuck":
        return tr("a_stuck_end", tr("a_" + a.args[0]))
    return tr("evEnded", alert_text(a))


def end_reason(m) -> str:
    st = m.status
    if st == "fell":
        return tr("endFellManual" if m.mode == "manual" else "endFell")
    if st == "battery_dead":
        return tr("endBattery")
    if st == "stopped":
        return tr("endStopped")
    if st == "returned":
        why = m.stats.get("return_reason", "")
        return tr("endBackWhy", tr("why_" + why)) if ("why_" + why) in STR["en"] else tr("endBack")
    return ""


# ---------------------------------------------------------------- the bottom tabs
STR["en"].update({
    "m_behaviour": "Active behaviour", "m_cmd": "Command (v, w)", "m_left": "Left motor", "m_right": "Right motor",
    "m_slip": "Wheel slip (L / R)", "m_straight": "Straight-drive I term", "m_enc": "Encoder counts (L / R)",
    "m_want": "desired wheel speed", "m_meas": "measured (encoder)", "m_duty": "PWM duty",
    "s_status": "Status", "s_coverage": "Coverage of reachable area", "s_mapped": "Mapped cells", "s_path": "Path length",
    "s_time": "Steps / time", "s_backtracks": "Backtracking", "s_bumps": "Collisions / bumps", "s_cliff": "Cliff events",
    "s_loc": "Position error (in use)", "s_odom": "Encoders-only error", "s_battery": "Battery", "s_frontiers": "Frontiers known",
    "s_ai": "AI terrain accuracy", "s_aiOff": "AI off", "s_frames": "{} frames",
    "r_state": "Link", "r_latency": "One-way latency", "r_packets": "Packets delivered / dropped", "r_mode": "Driving mode",
    "r_last": "Last command received", "r_clients": "Operator", "r_nobody": "nobody yet", "r_at": "at t = {:.1f} s",
    "r_fallback": "  (link lost - rover acts on its own: {})", "r_walls": "({:.1f} m, {} walls)",
    "r_hint": "Commands from the console, the controller and the keyboard travel over this link. Signal falls with distance "
              "and with every wall between the rover and its base; weak = half the packets lost, lost = nothing arrives "
              "and the rover acts on its own after 3 s.",
    "r_base": "base station", "r_rover": "rover", "r_between": "{:.1f} m   -   {} wall cells in the way",
    "link_ok": "OK", "link_weak": "WEAK", "link_lost": "LOST",
})
STR["ar"].update({
    "m_behaviour": "بيعمل إيه دلوقتي", "m_cmd": "الأمر (سرعة، لفّ)", "m_left": "الموتور الشمال", "m_right": "الموتور اليمين",
    "m_slip": "العجل بيزحلق (شمال / يمين)", "m_straight": "تصحيح المشي المستقيم", "m_enc": "لفات العجل (شمال / يمين)",
    "m_want": "السرعة المطلوبة", "m_meas": "السرعة الحقيقية (الإنكودر)", "m_duty": "قوة الموتور (PWM)",
    "s_status": "الحالة", "s_coverage": "اتكشف قد إيه من المكان", "s_mapped": "خلايا اتكشفت", "s_path": "مشي قد إيه",
    "s_time": "خطوات / وقت", "s_backtracks": "رجع كام مرة", "s_bumps": "خبط كام مرة", "s_cliff": "وقف عند حافة",
    "s_loc": "تايه قد إيه", "s_odom": "تايه قد إيه بالعجل بس", "s_battery": "البطارية", "s_frontiers": "حتت مجهولة",
    "s_ai": "دقة الذكاء الاصطناعي", "s_aiOff": "الذكاء الاصطناعي مقفول", "s_frames": "{} صورة",
    "r_state": "الإشارة", "r_latency": "التأخير", "r_packets": "أوامر وصلت / ضاعت", "r_mode": "مين سايق",
    "r_last": "آخر أمر وصل", "r_clients": "مين بيسوق", "r_nobody": "لسه محدش", "r_at": "عند {:.1f} ث",
    "r_fallback": "  (الإشارة فصلت - الروبوت بيتصرف لوحده: {})", "r_walls": "({:.1f} m، {} حيطة)",
    "r_hint": "الأوامر من الموبايل والدراع والكيبورد بتعدّي على الإشارة دي. الإشارة بتضعف كل ما الروبوت يبعد وكل ما "
              "يبقى فيه حيطان بينه وبين القاعدة. ضعيفة = نص الأوامر بتضيع، فاصلة = مفيش حاجة بتوصل والروبوت بيتصرف "
              "لوحده بعد 3 ثواني.",
    "r_base": "القاعدة", "r_rover": "الروبوت", "r_between": "{:.1f} m   -   {} حيطة في السكة",
    "link_ok": "كويسة", "link_weak": "ضعيفة", "link_lost": "فاصلة",
})


# sensor classes and the camera's terrain classes
STR["en"].update({"c_local": "local", "c_global": "global", "c_internal": "internal", "c_external": "external",
                  "c_active": "active", "c_passive": "passive", "c_binary": "binary", "c_analog": "analog", "c_digital": "digital",
                  "g_ground": "ground", "g_rock": "rock", "g_sand": "sand", "g_mud": "mud", "g_bedrock": "bedrock",
                  "g_water": "water", "g_reef": "reef", "g_": "?", "g_?": "?"})
STR["ar"].update({"c_local": "على الروبوت", "c_global": "من برّه", "c_internal": "جوّاه", "c_external": "بيحس باللي برّه",
                  "c_active": "بيبعت إشارة", "c_passive": "بيستقبل بس", "c_binary": "آه أو لأ", "c_analog": "أنالوج", "c_digital": "ديجيتال",
                  "g_ground": "أرض عادية", "g_rock": "صخر", "g_sand": "رمل", "g_mud": "طين", "g_bedrock": "صخر ناعم",
                  "g_water": "مية", "g_reef": "شعاب", "g_": "؟", "g_?": "؟"})


# report dialogs
STR["en"].update({
    "rnAsk": "Name this report, or send it with the automatic name.", "rnEmpty": "Leave empty to use the automatic name",
    "rnSaved": "Saved as  Mission #<n> - <name>   (automatic: {})", "rnNamed": "Send with this name",
    "rnAuto": "Send with the automatic name",
    "rsUrl": "Drive bridge URL:", "rsAuto": "Send a report automatically when a mission ends",
    "rsHint": "The URL comes from the Google Apps Script bridge described in docs/DRIVE_REPORTS.md. "
              "Reports are always saved under reports/ as well.",
})
STR["ar"].update({
    "rnAsk": "سمّي التقرير، أو ابعته بالاسم التلقائي.", "rnEmpty": "سيبه فاضي علشان ياخد الاسم التلقائي",
    "rnSaved": "هيتحفظ كده:  Mission #<n> - <الاسم>   (التلقائي: {})", "rnNamed": "ابعته بالاسم ده",
    "rnAuto": "ابعته بالاسم التلقائي",
    "rsUrl": "لينك الدرايف:", "rsAuto": "ابعت تقرير لوحده لما المهمة تخلص",
    "rsHint": "اللينك بييجي من سكريبت Google Apps Script المشروح في docs/DRIVE_REPORTS.md. "
              "التقارير بتتحفظ برضه في فولدر reports على الجهاز.",
})


# stop / restart confirmation
STR["en"].update({
    "cfStopTitle": "Stop the mission?", "cfStopMsg": "The rover stops where it is and everything stays on screen.",
    "cfStopSend": "Stop and send report", "cfStopPlain": "Stop without a report",
    "cfRestartTitle": "Restart the mission?", "cfRestartMsg": "This run ends and a new one starts with the same settings.",
    "cfRestartSend": "Send report, then restart", "cfRestartPlain": "Restart without a report",
    "cfCancel": "Cancel",
})
STR["ar"].update({
    "cfStopTitle": "توقّف المهمة؟", "cfStopMsg": "الروبوت هيقف مكانه وكل حاجة هتفضل على الشاشة.",
    "cfStopSend": "وقّف وابعت تقرير", "cfStopPlain": "وقّف من غير تقرير",
    "cfRestartTitle": "تعيد المهمة؟", "cfRestartMsg": "المهمة دي هتخلص وتبدأ واحدة جديدة بنفس الإعدادات.",
    "cfRestartSend": "ابعت تقرير وبعدين عيدها", "cfRestartPlain": "عيدها من غير تقرير",
    "cfCancel": "إلغاء",
})
