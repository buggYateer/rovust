"""The built-in user guide (Help > User guide, F1) and the Controls card
(Help > Controls), in English and Egyptian Arabic.

Kept in one place so the guide always describes the interface as it is. The
team guide (docs/team_guide_ar.html) explains the same things in more depth.
"""
from __future__ import annotations

GUIDE = {}
CONTROLS = {}

GUIDE["en"] = """
<h2>User guide</h2>

<h3>1. The screen</h3>
<ul>
<li><b>Header</b> (top): the mission chip (<i>Mission #n</i> &middot; environment &middot; clock &middot; status),
then <b>New mission</b>, <b>Pause</b>, <b>Stop</b>, <b>Restart</b>, the simulation speed <b>&times;1 &times;4 &times;8
&times;16</b>, and on the right <b>Lights</b>, <b>Phone console</b>, <b>Send report</b>, the language button
(<b>&#1593;&#1585;&#1576;&#1610;</b> / <b>English</b>) and the light/dark button (sun / moon).</li>
<li><b>Mission setup</b> (side panel): what to explore and how. The panel button at its top folds it into a thin strip
(the strip keeps a button to open it again and a start button).</li>
<li><b>Live numbers</b> above the maps: <i>Mapped</i> (share of the reachable area), <i>Distance</i>, <i>Battery</i>,
<i>Link</i> (radio strength; "not used" while nobody drives over the radio), <i>Behaviour</i> (the layer in control) and
<i>Position error</i> (how far the rover's own estimate is from the truth).</li>
<li><b>Map layers</b>: the chips under the numbers switch what is drawn: sonar, IR beams, terrain (AI), frontiers,
visited cells, true path.</li>
<li><b>The two maps</b>: <i>True world</i> (the ground truth the rover never sees) and <i>Robot's map</i> (built only
from its sensors). Click a map to open it large and live; click it again or press Esc to close.</li>
<li><b>Telemetry</b> (bottom tabs): Sensors, Motor control, Statistics, Radio link, Events. The arrow at the right folds
the tabs to one line; clicking a tab opens them again.</li>
<li><b>Status bar</b> (bottom): one short alert on the left, and on the right the report state, link, mapped share,
behaviour, mission time and speed.</li>
</ul>
<p><b>Greyed buttons</b> cannot do anything right now. Before the first mission only <i>New mission</i> works; once a
mission is over Pause, Stop and Lights turn grey, Restart and Send report stay available.</p>

<h3>2. Starting a mission</h3>
<ul>
<li><b>Environment</b>: <i>Cave</i> (narrow branching corridors, dark, mud, pits, gas), <i>Mars</i> (open ground, rocks,
craters, sand where the wheels slip), <i>Underwater</i> (reef walls, mud, a current; thrusters, sonar and a DVL instead
of wheels). Hover a card for its description. The rover's software is the same in all three.</li>
<li><b>Exploration strategy</b>: <i>Nearest frontier</i> goes to the closest edge of the unknown; <i>DFS + backtrack</i>
walks a lattice of waypoints depth-first and backs up at dead ends; <i>Utility (AI)</i> scores every frontier by the
information it may give, its terrain cost, hazards and the battery.</li>
<li><b>Localisation</b>: <i>Fused</i> (gyro + compass or sun sensor + optical flow / DVL), <i>Encoders</i> (dead
reckoning only: watch the map tear apart) or <i>Perfect</i> (the true position, for comparison).</li>
<li><b>AI</b>: the camera terrain classifier (feeds the planner's cost map) and the sensor fault detector.
<b>Seed</b>: the number of the generated world; the same seed always gives the same world and the same noise.</li>
</ul>
<p>Press <b>Start mission</b> (panel) or <b>New mission</b> (header, Ctrl+N). The rover stands still for 1.5 s to learn
its gyro bias, turns a full circle to fill its first map, then explores. It goes home when the map is complete or the
battery is only just enough to get back.</p>

<h3>3. What the maps show</h3>
<p><b>True world</b>: terrain colours, the true rover (orange) and its true path (yellow), sonar cones (blue, a dot where
an echo returns), IR beams (red), cliff switches (green dots that turn red over a drop), the base station (hollow circle)
and a line to the rover coloured by the radio link.</p>
<p><b>Robot's map</b>: white = free, black = occupied, blue-grey = unknown, red = hazard, tinted = terrain predicted by
the AI. Green rover and path = the estimate in use, the small red rover = encoders only, dashed blue = the planned A* path,
orange dots = frontiers, the circled one = the current target. The legend under the maps names every mark.</p>

<h3>4. The bottom tabs</h3>
<ul>
<li><b>Sensors</b>: every mounted sensor with its type (local/global, internal/external, active/passive,
binary/analog/digital; hover for all four), its live reading with a bar, <b>Inject fault</b>
(<i>ok / stuck / dead / noisy</i>) and <b>Health</b> (<i>ok</i>, <i>injected</i>, or <i>ignored</i> when the AI fault
detector stopped trusting it). Columns can be resized; double-click a column edge to reset it. The camera image and the
classifier's answer are at the side.</li>
<li><b>Motor control</b>: the lecture's loop, PWM &rarr; H-bridge &rarr; DC motor &rarr; encoder &rarr; PID. Command
(v, &omega;), both motors, wheel slip, the straight-driving correction, and a live plot of desired speed, measured speed
and duty for the left wheel.</li>
<li><b>Statistics</b>: status, coverage, mapped cells, path length, time, backtracking, collisions, cliff events,
position error (in use and encoders only), battery, frontiers, AI terrain accuracy.</li>
<li><b>Radio link</b>: the base, the rover, distance and walls in between, signal, latency, packets delivered / dropped,
driving mode, the last command and who sent it.</li>
<li><b>Events</b>: every alert that started or ended, newest first. The tab shows how many problems are active now.</li>
</ul>

<h3>5. Alerts</h3>
<p>The status bar shows <b>one</b> short alert at a time, the most serious one: stuck in mud or sand, weak or lost link,
low battery, gas, a failed sensor, too dark for the camera, paused, mission over. A condition must last 0.8 s before it is
shown, and an alert stays at least 3 s unless a more serious one arrives. <b>+n</b> says how many other problems are active.
Click the alert to open the Events tab. When it is dark, a <b>Lights on</b> button appears next to it. The phone console
shows the same alert as a short chip in its header.</p>

<h3>6. Driving it yourself</h3>
<p><b>Remote control</b> in the side panel says who drives:</p>
<ul>
<li><b>Auto</b>: the rover explores and returns by itself.</li>
<li><b>Assisted</b>: you steer; the safety layers (bumper escape, cliff stop, slope, obstacle avoidance) stay on and
override you. This is how real rovers are driven.</li>
<li><b>Manual</b>: you drive and nothing stops you, not even a cliff.</li>
</ul>
<p><b>If the link drops</b> (only in Assisted and Manual): what the rover does after 3 s without radio: <i>Return home</i>
(default), <i>Explore alone</i> or <i>Wait for the link</i>.</p>
<p><b>Keyboard</b> (Assisted or Manual): hold an arrow key or W A S D; works with any keyboard language. The rover stops
1 s after the last command.</p>
<p><b>Game controller</b> (USB dongle or Bluetooth): plug it in or pair it and press a button. The controller card in the
side panel names it, lights up every button you press and moves a dot with the stick. Touching the stick during an
Auto mission switches to Assisted.</p>
<table border="1" cellpadding="4" cellspacing="0">
<tr><th>PlayStation (Xbox)</th><th>Does</th></tr>
<tr><td>&#10005; (A) held</td><td>gas: drive forward, the left stick or the arrows steer</td></tr>
<tr><td>&#9651; (Y) held</td><td>reverse, the left stick or the arrows steer</td></tr>
<tr><td>Left stick or arrows alone</td><td>point-to-go: push where the rover should go on the map; it turns to face that
way, then drives. Circle the stick to spin it in place.</td></tr>
<tr><td>R2 / L2 + right stick</td><td>analog driving: the harder you press, the faster</td></tr>
<tr><td>Start</td><td>stop</td></tr>
<tr><td>&#9675; (B)</td><td>headlights</td></tr>
<tr><td>&#9633; (X)</td><td>return home</td></tr>
<tr><td>L1 / R1 (LB / RB)</td><td>change mode: Auto / Assisted / Manual</td></tr>
</table>
<p>Controller support needs the optional <i>pygame-ce</i> package (installed by setup.bat).</p>
<p><b>Phone or tablet</b>: press <b>Phone console</b> (header) or <b>Open console for phone / tablet</b> (side panel).
An address and a <b>QR code</b> appear in the panel: scan the code with the phone camera, or open the address in any browser
on the same Wi-Fi. Click the QR code to enlarge it.</p>

<h3>7. The radio link</h3>
<p>Every command from the phone, the controller and the keyboard travels over a simulated radio link to a base station at
the start point. The signal falls with distance and with every wall in between (cave: rock; underwater: an acoustic modem
with a 0.4 s delay; Mars: a relay with a 2 s delay). Weak link: about half the commands are lost. Lost link: nothing arrives,
and after 3 s the rover acts on the <i>If the link drops</i> setting.</p>

<h3>8. When a mission ends</h3>
<p>The rover is back at base, the battery is empty, it fell into a pit (only possible in Manual), or you pressed
<b>Stop</b>. A banner on the maps says why, and everything stays on screen. Start again with <b>New mission</b>, or
<b>Restart</b> (R) for the same settings. While a mission runs, Stop and Restart first ask: with a report, without one,
or cancel.</p>

<h3>9. Reports</h3>
<p><b>Send report</b> (Ctrl+S) asks for a name, or uses the automatic one (date, environment, computer), and saves
<i>reports/Mission #n - name/Report k - time</i>: an HTML page with all the statistics and both maps, the map pictures and the raw numbers.
With the Drive bridge configured (File &gt; Report settings) the folder is also uploaded to the team's shared Drive folder,
which gives it its number. Without internet the report waits and is sent later; the status bar shows how many are waiting.
You can send one at any moment while the mission runs: all reports of one run go into the same mission folder,
numbered Report 1, Report 2, ...
With <i>auto-send</i> on, a report is made by itself when a mission ends on its own. File &gt; Open reports folder shows them.</p>

<h3>10. Things to try in a demonstration</h3>
<ul>
<li>Assisted from the phone or the controller: drive into a wall, the rover refuses. Switch to Manual and try again.</li>
<li>Drive deep into the cave with <i>If the link drops: Return home</i>: the link bars fall, commands stop arriving and the
rover comes back by itself.</li>
<li>Same seed, Localisation <i>Encoders</i> then <i>Fused</i>: the red estimate drifts, the map duplicates walls.</li>
<li>Mars: set <i>optflow</i> to <i>dead</i>; the estimate now trusts the slipping wheels.</li>
<li>Set <i>sonar0</i> to <i>noisy</i> and wait for Health to say <i>ignored</i>.</li>
<li>Compare DFS and the utility explorer on the same seed with the Statistics tab open.</li>
</ul>
"""

GUIDE["ar"] = """
<div dir="rtl">
<h2>إزاي تستخدم البرنامج</h2>

<h3>1. الشاشة</h3>
<ul>
<li><b>الشريط اللي فوق</b>: كارت المهمة (<i>مهمة #n</i> · المكان · الوقت · الحالة)، وبعده <b>مهمة جديدة</b>،
<b>وقّف</b> (إيقاف مؤقت)، <b>خلّص المهمة</b>، <b>عيدها</b>، وسرعة المحاكاة <b>×1 ×4 ×8 ×16</b>. وعلى الطرف التاني
<b>النور</b>، <b>سوق من الموبايل</b>، <b>ابعت التقرير</b>، زرار اللغة (<b>English</b> / <b>عربي</b>)، وزرار الفاتح
والغامق (شمس / قمر).</li>
<li><b>تجهيز المهمة</b> (البانل الجانبي): هيستكشف فين وإزاي. الزرار اللي فوقه بيقفله لشريط رفيع فيه زرار يفتحه تاني
وزرار يبدأ مهمة.</li>
<li><b>الأرقام الحية</b> فوق الخرايط: <i>اتكشف</i> (نسبة المكان اللي ممكن يوصله)، <i>مشي</i>، <i>البطارية</i>،
<i>الإشارة</i> (قوة الراديو، ومكتوب "مش مستخدمة" لو محدش بيسوق من بعيد)، <i>بيعمل إيه</i> (الطبقة اللي ماسكة
التحكم)، و<i>تايه قد إيه</i> (الفرق بين مكانه الحقيقي واللي هو فاكره).</li>
<li><b>يظهر على الخريطة</b>: الزراير الصغيرة تحت الأرقام بتظهّر وتخفي: السونار، الأشعة تحت الحمرا، نوع الأرض،
اللي لسه مجهول، عدّى منين، مشي منين فعلاً.</li>
<li><b>الخريطتين</b>: <i>المكان على حقيقته</i> (الروبوت مش شايفه) و<i>اللي الروبوت شايفه</i> (من حساساته بس). دوس على
أي خريطة تفتح كبيرة وحية، ودوس تاني أو Esc تقفلها.</li>
<li><b>الأرقام اللي تحت</b> (تبويبات): الحساسات، الموتور، أرقام المهمة، الإشارة، اللي حصل. السهم اللي على الطرف بيصغّرها
لسطر واحد، والضغط على أي تبويب بيفتحها تاني.</li>
<li><b>الشريط اللي تحت</b>: تنبيه واحد قصير، وعلى الطرف التاني حالة التقرير، الإشارة، اتكشف قد إيه، بيعمل إيه، الوقت
والسرعة.</li>
</ul>
<p><b>الزرار الرمادي</b> مش هيعمل حاجة دلوقتي. قبل أول مهمة مفيش غير <i>مهمة جديدة</i>؛ ولما المهمة تخلص، وقّف
وخلّص المهمة والنور بيبقوا رمادي، وعيدها وابعت التقرير بيفضلوا شغالين.</p>

<h3>2. تبدأ مهمة</h3>
<ul>
<li><b>هيستكشف فين؟</b> <i>كهف</i> (ممرات ضيقة، ضلمة، طين، حفر، غاز)، <i>المريخ</i> (أرض مفتوحة، صخور، حفر كبيرة،
رمل العجل بيزحلق فيه)، <i>تحت المية</i> (شعاب، طين، تيار؛ مراوح وسونار وDVL بدل العجل). اقف بالماوس على الكارت
تشوف وصفه. برنامج الروبوت نفسه واحد في التلاتة.</li>
<li><b>هيدوّر إزاي؟</b> <i>أقرب حتة مجهولة</i> (nearest frontier)، <i>للآخر وبعدين يرجع</i> (DFS + backtracking)،
<i>بالذكاء الاصطناعي</i> (utility: بيقيّم كل حتة مجهولة بالمعلومات اللي هيكسبها وتكلفة الأرض والخطر والبطارية).</li>
<li><b>هيعرف هو فين إزاي؟</b> <i>كل الحساسات</i> (جيرو + بوصلة أو حساس شمس + optical flow / DVL)، <i>العجل بس</i>
(dead reckoning، وهتشوف الخريطة بتتشرّخ)، أو <i>بالظبط</i> (المكان الحقيقي، للمقارنة بس).</li>
<li><b>الذكاء الاصطناعي</b>: مصنّف نوع الأرض من الكاميرا وكاشف الحساس البايظ. <b>رقم الخريطة</b> (seed): نفس الرقم
= نفس الخريطة ونفس الضوضاء.</li>
</ul>
<p>دوس <b>يلا نبدأ</b> في البانل أو <b>مهمة جديدة</b> فوق (Ctrl+N). الروبوت بيقف 1.5 ثانية يتعلم انحراف الجيرو، يلف
لفة كاملة يملا أول خريطة، وبعدين يستكشف. بيرجع مكان ما بدأ لما الخريطة تكمل أو البطارية تبقى يادوب تكفّي الرجوع.</p>

<h3>3. الخرايط بتبيّن إيه</h3>
<p><b>المكان على حقيقته</b>: ألوان الأرض، الروبوت الحقيقي (برتقالي) ومشي منين فعلاً (أصفر)، مخاريط السونار (أزرق، ونقطة
مكان الصدى)، أشعة الـ IR (أحمر)، حساسات الحافة (نقط خضرا بتحمرّ فوق الحفرة)، القاعدة (دايرة فاضية) وخط للروبوت
لونه حسب الإشارة.</p>
<p><b>اللي الروبوت شايفه</b>: أبيض فاضي، أسود حيطة، رمادي مزرق مجهول، أحمر خطر، ملوّن = نوع الأرض اللي الذكاء
الاصطناعي توقعه. الروبوت والسكة الخضرا = المكان اللي بيعتمد عليه، الروبوت الأحمر الصغير = حسب العجل بس، الخط الأزرق
المتقطع = السكة اللي ناوي يمشيها (A*)، النقط البرتقاني = الحتت المجهولة، والمحوّطة = رايح فين دلوقتي. السطر اللي تحت
الخرايط بيشرح كل علامة.</p>

<h3>4. التبويبات اللي تحت</h3>
<ul>
<li><b>الحساسات</b>: كل حساس متركّب ونوعه (اقف عليه بالماوس تشوف التصنيف الكامل)، بيقرا كام مع شريط، <b>جرّب عطل</b>
(<i>سليم / معلّق / ميت / مشوّش</i>) و<b>حالته</b> (<i>تمام</i>، <i>عطل مقصود</i>، أو <i>مش بنصدّقه</i> لما كاشف الأعطال
يبطّل يعتمد عليه). تقدر تكبّر وتصغّر الأعمدة، ودبل كليك على حافة العمود بيرجّعه. صورة الكاميرا ورأي الذكاء
الاصطناعي على الجنب.</li>
<li><b>الموتور</b>: دايرة المحاضرة PWM ← H-bridge ← موتور DC ← encoder ← PID. الأمر (سرعة، لفّ)، الموتورين، زحلقة
العجل، تصحيح المشي المستقيم، ورسمة حية للسرعة المطلوبة والحقيقية وقوة الموتور للعجلة الشمال.</li>
<li><b>أرقام المهمة</b>: الحالة، اتكشف قد إيه، مشي قد إيه، الوقت، رجع كام مرة، خبط كام مرة، وقف عند حافة كام مرة، تايه
قد إيه (باللي بيعتمد عليه وبالعجل بس)، البطارية، الحتت المجهولة، ودقة الذكاء الاصطناعي.</li>
<li><b>الإشارة</b>: القاعدة والروبوت والمسافة والحيطان اللي بينهم، قوة الإشارة، التأخير، أوامر وصلت / ضاعت، مين سايق،
وآخر أمر ومين بعته.</li>
<li><b>اللي حصل</b>: كل تنبيه بدأ أو خلص، الأحدث فوق. اسم التبويب بيقول فيه كام مشكلة دلوقتي.</li>
</ul>

<h3>5. التنبيهات</h3>
<p>الشريط اللي تحت بيعرض تنبيه <b>واحد</b> بس في المرة، الأهم: غارز في الطين أو الرمل، الإشارة ضعيفة أو فصلت، البطارية
بتخلص، فيه غاز، حساس باظ، الدنيا ضلمة على الكاميرا، المهمة واقفة، المهمة خلصت. الحاجة لازم تفضل 0.8 ثانية قبل ما تظهر،
والتنبيه بيفضل 3 ثواني على الأقل إلا لو جه واحد أخطر. <b>+n</b> معناها فيه كام مشكلة تانية. دوس على التنبيه يفتح
تبويب اللي حصل. ولو الدنيا ضلمة بيظهر جنبه زرار <b>ولّع النور</b>. صفحة الموبايل بتعرض نفس التنبيه كلمتين في الهيدر.</p>

<h3>6. تسوق إنت</h3>
<p><b>السواقة من بعيد</b> في البانل بتحدد مين سايق:</p>
<ul>
<li><b>لوحده</b>: الروبوت بيستكشف ويرجع من غير ما حد يلمسه.</li>
<li><b>إنت + هو</b>: إنت بتوجّه، وطبقات الأمان (الرجوع من خبطة، الوقوف عند الحافة، الطلعة، تفادي الحيطان) شغالة
وبتغلبك لو لازم. كده بالظبط بيسوقوا الروفرات الحقيقية.</li>
<li><b>إنت اللي سايق</b>: محدش هيوقفك، ولا حتى قدام حفرة.</li>
</ul>
<p><b>لو الإشارة فصلت</b> (في الوضعين اللي فيهم إنت سايق بس): الروبوت يعمل إيه بعد 3 ثواني من غير إشارة:
<i>يرجع مكان ما بدأ</i> (الافتراضي)، <i>يكمّل لوحده</i>، أو <i>يستنى الإشارة</i>.</p>
<p><b>الكيبورد</b>: اضغط مع الاستمرار على الأسهم أو W A S D، وبيشتغل بأي لغة كيبورد. الروبوت بيقف بعد ثانية من آخر أمر.</p>
<p><b>دراع الألعاب</b> (بدونجل أو بلوتوث): وصّله أو اعمله pair ودوس أي زرار. كارت الدراع في البانل بيكتب اسمه، وبينوّر كل
زرار بتدوسه، ونقطة بتتحرك مع العصاية. لو لمست العصاية والمهمة "لوحده" الوضع بيتحول لـ "إنت + هو".</p>
<table border="1" cellpadding="4" cellspacing="0">
<tr><th>بلايستيشن (Xbox)</th><th>بيعمل إيه</th></tr>
<tr><td>✕ (A) دايس عليه</td><td>بنزين: يمشي لقدّام، والعصاية الشمال أو الأسهم للاتجاه</td></tr>
<tr><td>△ (Y) دايس عليه</td><td>ورا، والعصاية الشمال أو الأسهم للاتجاه</td></tr>
<tr><td>العصاية الشمال أو الأسهم لوحدهم</td><td>شاور يروح فين: زق العصاية ناحية المكان على الخريطة، يلف ناحيته وبعدين يمشي.
لفّ العصاية حوالين نفسها يلف في مكانه.</td></tr>
<tr><td>R2 / L2 + العصاية اليمين</td><td>سواقة بالضغطة: كل ما تدوس أكتر يمشي أسرع</td></tr>
<tr><td>Start</td><td>وقّف</td></tr>
<tr><td>○ (B)</td><td>النور</td></tr>
<tr><td>□ (X)</td><td>رجوع لمكان البداية</td></tr>
<tr><td>L1 / R1 (LB / RB)</td><td>غيّر الوضع: لوحده / إنت + هو / إنت اللي سايق</td></tr>
</table>
<p>الدراع محتاج مكتبة <i>pygame-ce</i> (setup.bat بينزّلها).</p>
<p><b>الموبايل أو التابلت</b>: دوس <b>سوق من الموبايل</b> فوق أو <b>افتح السواقة من الموبايل</b> في البانل. هيظهر لينك و<b>كود
QR</b> في البانل: صوّر الكود بكاميرا الموبايل أو افتح اللينك من أي متصفح على نفس الواي فاي. دوس على الكود يكبر.</p>

<h3>7. الإشارة</h3>
<p>كل أمر من الموبايل أو الدراع أو الكيبورد بيعدّي على راديو محاكى لقاعدة عند نقطة البداية. الإشارة بتضعف مع المسافة ومع
كل حيطة في السكة (الكهف: صخر، تحت المية: مودم صوتي بتأخير 0.4 ثانية، المريخ: relay بتأخير ثانيتين). ضعيفة: حوالي نص
الأوامر بتضيع. فاصلة: مفيش حاجة بتوصل، وبعد 3 ثواني الروبوت بيعمل اللي اخترته في <i>لو الإشارة فصلت</i>.</p>

<h3>8. لما المهمة تخلص</h3>
<p>الروبوت رجع مكان ما بدأ، أو البطارية خلصت، أو وقع في حفرة (ده بيحصل في "إنت اللي سايق" بس)، أو إنت دوست <b>خلّص
المهمة</b>. بيظهر على الخرايط السبب، وكل حاجة بتفضل على الشاشة. ابدأ تاني بـ <b>مهمة جديدة</b>، أو <b>عيدها</b> (R)
بنفس الإعدادات. ولو المهمة لسه شغالة، «خلّص المهمة» و«عيدها» بيسألوك الأول: بتقرير، من غير تقرير، ولا إلغاء.</p>

<h3>9. التقارير</h3>
<p><b>ابعت التقرير</b> (Ctrl+S) بيسألك على اسم أو ياخد الاسم التلقائي (التاريخ، المكان، الجهاز)، وبيحفظ
<i>reports/Mission #n - الاسم/Report k - الوقت</i>: صفحة HTML فيها كل الأرقام والخريطتين، صور الخرايط، والأرقام الخام. لو لينك الدرايف
متظبط (ملف &gt; إعدادات التقارير) الفولدر بيترفع على فولدر الدرايف بتاع التيم، وهو اللي بيدّيه رقمه. من غير نت التقرير
بيستنى ويترفع بعدين، والشريط اللي تحت بيقول فيه كام مستني. وتقدر تبعت تقرير في أي وقت والمهمة شغالة، وكل
تقارير نفس المهمة بتتحط في فولدر المهمة نفسه، متمرّقمة Report 1 وReport 2 وهكذا. ولو <i>الإرسال التلقائي</i> شغال بيتعمل تقرير لوحده لما المهمة تخلص لوحدها. ملف &gt; افتح فولدر التقارير بيوريهم.</p>

<h3>10. تجارب حلوة في العرض</h3>
<ul>
<li>"إنت + هو" من الموبايل أو الدراع: سوق في حيطة، الروبوت هيرفض. حوّل "إنت اللي سايق" وجرّب تاني.</li>
<li>ادخل جوه الكهف و<i>لو الإشارة فصلت: يرجع</i>: الإشارة بتقل، الأوامر بتبطّل توصل، والروبوت بيرجع لوحده.</li>
<li>نفس رقم الخريطة، مرة <i>العجل بس</i> ومرة <i>كل الحساسات</i>: الأحمر بيتوه والحيطان بتتكرر.</li>
<li>على المريخ خلّي <i>optflow</i> <i>ميت</i>: الروبوت يعتمد على العجل اللي بيزحلق.</li>
<li>خلّي <i>sonar0</i> <i>مشوّش</i> واستنى لحد ما حالته تبقى <i>مش بنصدّقه</i>.</li>
<li>قارن DFS والذكاء الاصطناعي على نفس الرقم وتبويب أرقام المهمة مفتوح.</li>
</ul>
</div>
"""

CONTROLS["en"] = """
<b>Mission</b><br>
Ctrl+N &nbsp; new mission &nbsp;&middot;&nbsp; Space &nbsp; pause / resume &nbsp;&middot;&nbsp; Ctrl+. &nbsp; stop<br>
R &nbsp; restart with the same settings &nbsp;&middot;&nbsp; 1 2 3 4 &nbsp; speed &times;1 &times;4 &times;8 &times;16<br>
H &nbsp; headlights &nbsp;&middot;&nbsp; Ctrl+S &nbsp; send report<br><br>
<b>Window</b><br>
Ctrl+L &nbsp; English / Arabic &nbsp;&middot;&nbsp; Ctrl+D &nbsp; dark mode &nbsp;&middot;&nbsp; F1 &nbsp; user guide
&nbsp;&middot;&nbsp; Ctrl+Q &nbsp; exit<br><br>
<b>Driving</b> (Assisted or Manual)<br>
Arrow keys or W A S D, held down.<br><br>
<b>Game controller</b><br>
&#10005; gas &middot; &#9651; reverse &middot; left stick or arrows steer (alone: point-to-go) &middot;
R2 / L2 + right stick analog &middot; Start stop &middot; &#9675; lights &middot; &#9633; home &middot; L1 / R1 mode<br><br>
<b>Sensors</b><br>
Sensors tab, <i>Inject fault</i>: stuck (keeps its last value), dead (reports nothing), noisy.
"""

CONTROLS["ar"] = """
<div dir="rtl">
<b>المهمة</b><br>
Ctrl+N مهمة جديدة · Space وقّف / كمّل · Ctrl+. خلّص المهمة<br>
R عيدها بنفس الإعدادات · 1 2 3 4 السرعة ×1 ×4 ×8 ×16<br>
H النور · Ctrl+S ابعت التقرير<br><br>
<b>الشباك</b><br>
Ctrl+L عربي / English · Ctrl+D الوضع الغامق · F1 إزاي تستخدمه · Ctrl+Q اقفل البرنامج<br><br>
<b>السواقة</b> (إنت + هو، أو إنت اللي سايق)<br>
الأسهم أو W A S D مع الاستمرار.<br><br>
<b>دراع الألعاب</b><br>
✕ بنزين · △ ورا · العصاية الشمال أو الأسهم للاتجاه (لوحدهم: شاور يروح فين) · R2 / L2 + العصاية اليمين سواقة بالضغطة ·
Start وقّف · ○ النور · □ رجوع · L1 / R1 الوضع<br><br>
<b>الحساسات</b><br>
تبويب الحساسات، <i>جرّب عطل</i>: معلّق (بيفضل يقول آخر رقم)، ميت (مبيقولش حاجة)، مشوّش.
</div>
"""
