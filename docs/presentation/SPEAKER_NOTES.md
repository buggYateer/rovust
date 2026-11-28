# Rovust — Multi-Environment Autonomous Exploration Rover — speaker notes

English notes first, then the same note in Egyptian Arabic. One entry per slide, in deck order.

## 1. Rovust

Good morning. We are team Rovust — the name is Rover plus Robust: a rover built to keep going on its own. We built it as a Python simulation from the motors up: DC motors, encoders, PID, a full sensor suite, and only then the map and the decisions. The same robot explores a cave, the surface of Mars and an underwater site. Behind me, the real cave, and in front of it the map the rover built by itself.

<div dir="rtl" align="right">

صباح الخير، إحنا فريق Rovust — والاسم جاي من Rover وRobust: روبوت مستكشف يقدر يكمّل لوحده. بنيناه كمحاكاة بالبايثون من الموتورات لفوق: موتورات DC، وencoders، وPID، وطقم سنسورز كامل، وبعدين بس الخريطة والقرار. نفس الروبوت بيستكشف كهف، وسطح المريخ، وتحت المية. وورايا الكهف الحقيقي، وقدامه الخريطة اللي الروبوت رسمها لوحده.

</div>

## 2. A rover that explores a place it has never seen — safely, on its own

In one sentence: Rovust is a software rover that is dropped into an unknown place and has to explore it autonomously. The problem is real — Mars, collapsed mines, flooded caves — and simulation is the only safe and repeatable way to develop and compare the algorithms. The four numbers on the right summarise the project: three environments with one codebase, more than twenty modelled sensors, 264 measured runs, and up to 97 percent of the reachable area mapped. Why autonomy at all? Because in the places we care about, a human cannot drive the robot: the signal is delayed, blocked or gone. The animation on the right is a real run from our simulator — on the left the true cave the robot never sees, on the right the map it builds by itself. Our central design decision was to write one engine and treat each environment as data. Later we will show that this is exactly what makes the comparisons fair.

<div dir="rtl" align="right">

في جملة واحدة: Rovust روفر سوفتوير بيتحط في مكان مجهول ولازم يستكشفه لوحده. المشكلة حقيقية، المريخ، المناجم المنهارة، الكهوف الغرقانة، والمحاكاة هي الطريقة الوحيدة الآمنة واللي تتكرر عشان نطوّر الخوارزميات ونقارن بينها. الأربع أرقام اللي على اليمين بتلخّص المشروع: تلات بيئات بكود واحد، أكتر من عشرين حساس متمودلين، 264 تجربة متقاسة، ولحد 97 في الميّه من المساحة اللي ينفع يوصلها اترسمت. ليه الاستقلالية أصلاً؟ عشان في الأماكن اللي بتهمنا، البني آدم مش هيقدر يسوق الروبوت: الإشارة إما متأخرة أو مقطوعة أو مش موجودة خالص. الأنيميشن اللي على اليمين ده تجربة حقيقية من المحاكي بتاعنا، على الشمال الكهف الحقيقي اللي الروبوت عمره ما بيشوفه، وعلى اليمين الخريطة اللي بيبنيها بنفسه. القرار التصميمي المركزي عندنا كان إننا نكتب محرّك واحد ونتعامل مع كل بيئة على إنها داتا. وبعدين هنوريكم إن ده بالظبط اللي بيخلّي المقارنات عادلة.

</div>

## 3. Built from the motors up — the course, layer by layer

This table is our map of the course. Each row is a lecture — actuators, encoders, control, sensors, behaviour, navigation, communication — and each is implemented as a module that the others depend on. We will go through them in that order: first the analysis of the hardware we simulate, then the design of the software on top, then the measurements.

<div dir="rtl" align="right">

الجدول ده هو خريطتنا للكورس. كل صف محاضرة، المشغّلات، الإنكودرز، التحكم، الحساسات، السلوك، الملاحة، الاتصالات، وكل واحدة متنفّذة كموديول الباقيين معتمدين عليه. هنمشي عليهم بالترتيب ده: الأول تحليل الهاردوير اللي بنحاكيه، بعدين تصميم السوفتوير اللي فوقه، وبعدين القياسات.

</div>

## 4. Analysis

Part two is the analysis: the hardware we simulate. Sensors first, then the motors and the control loop, then the wiring and the loop as a flowchart.

<div dir="rtl" align="right">

الجزء التاني: الـ Analysis. الروبوت معمول من إيه: السنسورز، وبعدين الموتورات والتحكم، وبعدين التوصيل والـ flowchart.

</div>

## 5. 20+ sensors, classified the way the course classifies them

Every sensor carries its classification from Sensors 1: local or global, internal or external, active or passive, binary, analog or digital. The suite is not the same in every world: Mars has a sun sensor instead of a compass, underwater has a Doppler velocity log instead of encoders and no infrared because light does not travel. The code that reads them never changes — only the configuration says what is mounted.

<div dir="rtl" align="right">

كل حساس شايل تصنيفه من محاضرة Sensors 1: محلي ولا عام، داخلي ولا خارجي، نشط ولا سلبي، ثنائي ولا تناظري ولا رقمي. الطقم مش هو هو في كل بيئة: المريخ فيه حساس شمس بدل البوصلة، وتحت الميّه فيه Doppler velocity log بدل الإنكودرز ومفيش إنفراريد عشان الضوء مش بيمشي. الكود اللي بيقراهم عمره ما بيتغيّر، الكونفيج بس هو اللي بيقول إيه المركّب.

</div>

## 6. Four wheels, two DC motors, an H-bridge and PWM

The actuator model follows Actuators 1 and 2 closely: an H-bridge for direction, PWM for the average voltage, and a motor whose speed is not proportional to the duty cycle. The rover has four wheels but only two motors, one per side driving both wheels of that side, so it steers like a differential drive: equal speeds go straight, different speeds turn, opposite speeds spin it in place. The dead band and the load dependence are what make open-loop control useless — the same duty gives a different speed on sand — and that motivates the next slide.

<div dir="rtl" align="right">

موديل المشغّلات ماشي بالظبط مع محاضرتي Actuators 1 و2: H-bridge للاتجاه، PWM للجهد المتوسط، وموتور سرعته مش متناسبة مع الـ duty cycle. الروبوت 4 عجلات بس بموتورين، موتور لكل جنب بيلف العجلتين بتوع جنبه، فبيتوجّه زي الـ differential drive: الجنبين نفس السرعة يمشي مستقيم، سرعتين مختلفين يلف، وعكس بعض يلف في مكانه. المنطقة الميّتة والاعتماد على الحمل هما اللي بيخلّوا التحكم المفتوح ملوش لازمة، نفس الـ duty بيدّي سرعة مختلفة على الرمل، وده اللي بيمهّد للشريحة الجاية.

</div>

## 7. Encoder → PID → PWM, 20 times a second

This is the Control lecture running. We implemented on-off, on-off with hysteresis, and the incremental PID exactly as derived in class, and the plot shows the textbook behaviour: the P controller keeps a steady-state error because its output goes to zero when the error does, and the integral term removes it. The straight-driving controller is the structure from figure 5.16: integrate the position difference of the two wheels and feed it back. In the application you can watch this loop live in the Motor control tab.

<div dir="rtl" align="right">

دي محاضرة التحكم وهي شغّالة. نفّذنا on-off، وon-off بـ hysteresis، والـ PID التزايدي بالظبط زي ما اتشرح في المحاضرة، والرسمة بتوري سلوك الكتاب: متحكم P بيسيب خطأ في الحالة المستقرة لأن خرجه بيروح للصفر لما الخطأ يروح للصفر، والحد التكاملي هو اللي بيشيله. متحكم المشي عدل هو نفس الهيكل بتاع شكل 5.16: نكامل فرق الموضع بين العجلتين ونرجّعه. في البرنامج تقدر تتفرج على اللوب ده لايف في تاب Motor control.

</div>

## 8. One controller, every interface the rover needs

This is the hardware as a wiring diagram. On the left every sensor and the interface it uses on the controller: the encoders on hardware pulse counters, the analog sensors through a ten-bit A to D converter, the bumpers and cliff switches on digital inputs, the gyro, accelerometer and compass on I squared C, the sonar ring with trigger and echo timing, and the camera and optical flow on a serial bus. In the middle one controller running one fifty millisecond loop, like the EyeCon in the lectures. On the right two PWM signals with direction lines go into an L293D, which is two H-bridges, one per motor, with twelve volts for the motors and five volts for the logic. The radio link to the operator is a serial connection.

<div dir="rtl" align="right">

دي الهاردوير كرسمة توصيل. على الشمال كل سنسور والـ interface اللي بيدخل بيها على المتحكم: الـ encoders على pulse counters في الهاردوير، السنسورز الأنالوج من خلال ADC عشرة بت، الـ bumpers والـ cliff switches على digital inputs، الـ gyro والـ accelerometer والـ compass على I2C، الـ sonar بالـ trigger والـ echo، والكاميرا والـ optical flow على serial. في النص متحكم واحد بيلف لوب كل 50 ملّي ثانية زي الـ EyeCon في المحاضرات. وعلى اليمين إشارتين PWM مع خطوط الاتجاه داخلين على L293D، اللي هو 2 H-bridge، واحد لكل موتور، 12 فولت للموتور و5 فولت للوجيك. والراديو serial.

</div>

## 9. Now picture it: every part we described, on one rover

Before the software, here is everything we just described on one rover, in 3D, and this is also where each sensor sits and why. The four wheels and the two motors, one per side, and how it spins in place; the inside, with the gearboxes, encoders and battery. Then each sensor in turn. Eight sonars around the body, 45 degrees apart, so no part of the body shadows a cone. Three IR rangers facing forward across the body width, recessed six centimetres because closer than that the reading folds back; they were first at plus and minus thirty degrees, which left a blind strip exactly where the body is. Six cliff sensors: the rear pair because our escape behaviours reverse and a rover fell into a crater backwards, the side pair because the body brushed a pit while turning. The bumpers, the camera looking at the ground ahead for the terrain classifier, the heading sensors at the centre with the compass away from the motors, and the radio. Sizes come from the simulation's code; heights and the parts inside are our estimate, because the simulation is two-dimensional.

<div dir="rtl" align="right">

قبل ما نروح للسوفتوير، ده كل اللي اتكلمنا عنه متجمّع في روبوت واحد، 3D، وهنا كمان أماكن السنسورز وليه كل واحد في مكانه. العجل الأربعة والموتورين، موتور لكل جنب، وإزاي بيلف في مكانه. وبعدين من جوه: علبة التروس والـ encoders والبطارية. وبعدين كل سنسور لوحده: تمانية سونار حوالين الجسم كل 45 درجة، عشان مفيش حتة من الجسم تداري على أي مخروط. تلات IR باصّين لقدّام على عرض الجسم كله وراجعين 6 سم لجوه، لأن أقرب من كده القراية بتغلط. وكانوا الأول على زاوية ±30 فسابوا حتة عمياء قدّام الجسم بالظبط. ست حساسات حفر: اللي ورا عشان سلوكيات الهروب بترجع لورا، وروبوت وقع في حفرة بضهره، واللي على الجنب عشان الجسم قرّب من حفرة وهو بيلف. وبعدين الـ bumpers، والكاميرا اللي بتبص على الأرض قدّام لمصنّف الأرض، وحساسات الاتجاه في النص والبوصلة بعيد عن الموتورات، والراديو. المقاسات من كود المحاكاة، والارتفاعات واللي جوه تقدير مننا، لأن المحاكاة 2D.

</div>

## 10. What the controller does every 50 ms

This is the whole robot on one slide, as a flowchart on the left and pseudocode on the right. Every 50 milliseconds the controller first checks whether the mission is over. If not, it looks at the radio link for an operator command. Then the subsumption stack runs: the highest layer that wants control produces a forward speed v and a turn rate omega. Inverse kinematics splits that into two wheel speeds, a PID per wheel compares them with the encoder speed and outputs a PWM duty cycle, and the H-bridge drives the motor. Then the sensors are read, the pose is estimated by fusing odometry with the gyro, compass and optical flow, and the occupancy grid is updated. Every fourth frame the AI runs: the terrain classifier, the fault detector, and the explorer that chooses the next target and plans a path to it with A star.

<div dir="rtl" align="right">

دي الروبوت كله في شريحة واحدة: flowchart على الشمال وpseudocode على اليمين. كل 50 ملّي ثانية المتحكم بيشوف الأول المهمة خلصت ولا لأ. لو لأ، بيبص على الراديو لو فيه أمر من الأوبريتور. بعد كده الـ subsumption بيشتغل: أعلى طبقة عايزة التحكم بتطلّع سرعة لقدام v وسرعة لف أوميجا. الـ inverse kinematics بتقسمهم لسرعتين للعجلتين، والـ PID بتاع كل عجلة بيقارن بسرعة الـ encoder ويطلّع duty cycle للـ PWM، والـ H-bridge بيشغّل الموتور. بعدها بنقرا السنسورز، ونحسب المكان بدمج الـ odometry مع الـ gyro والـ compass والـ optical flow، ونحدّث الخريطة. وكل رابع فريم الذكاء الاصطناعي بيشتغل: مصنّف الأرض، كاشف الأعطال، والـ explorer اللي بيختار الهدف الجاي ويخطط له طريق بـ A star.

</div>

## 11. Design & Implementation

Part three: the software built on that hardware, and the application people use to watch and drive it.

<div dir="rtl" align="right">

الجزء التالت: الـ Design. إزاي القراءات بتبقى خريطة وقرار وحركة، والبرنامج اللي بنتفرج ونسوق منه.

</div>

## 12. Where am I? Fusion turns metres into centimetres

Localisation is where the sensor analysis pays off. The red estimate is pure dead reckoning and it drifts by metres. The green one fuses three things: a ground-speed sensor that does not see wheel slip, a gyro for fast heading changes, and a compass or sun sensor to bound the gyro's drift. The map is a probabilistic grid; its rules were tuned against real failures — for instance, an echo places the obstacle just beyond the surface, otherwise half the hits fall inside the corridor and the walls grow thick.

<div dir="rtl" align="right">

تحديد الموضع هو المكان اللي تحليل الحساسات بيثمر فيه. التقدير الأحمر ده dead reckoning صافي وبينزاح بالأمتار. الأخضر بيدمج تلات حاجات: حساس سرعة أرضية مش بيشوف انزلاق العجل، جيرو لتغيّرات الاتجاه السريعة، وبوصلة أو حساس شمس عشان يحدّ انزياح الجيرو. الخريطة شبكة احتمالية، وقواعدها اتظبطت على فشل حقيقي، مثلاً الصدى بيحط العائق بعد السطح بشوية، غير كده نص الضربات بتقع جوه الممر والحيطان بتتخن.

</div>

## 13. Subsumption: the higher layer takes the wheels

Behaviour is organised as a subsumption architecture, straight from the Robot Behaviour lecture. Ten layers; the highest one that wants control wins. The reflexes are on top — stop, escape, cliff, slope — then avoidance, then the operator, then return-home, then exploration. The avoidance layer is itself an on-off controller with a hysteresis band, which is the Control lecture applied to behaviour. And the manual driving mode exists to demonstrate the layers by switching them off.

<div dir="rtl" align="right">

السلوك متنظّم كمعمارية subsumption، من محاضرة Robot Behaviour على طول. عشر طبقات، وأعلى واحدة عايزة التحكم هي اللي بتكسب. ردود الفعل فوق، stop وescape وcliff وslope، بعدين التفادي، بعدين المشغّل البشري، بعدين الرجوع للبيت، بعدين الاستكشاف. طبقة التفادي نفسها متحكم on-off بنطاق hysteresis، يعني محاضرة التحكم متطبّقة على السلوك. ووضع السواقة اليدوية موجود عشان نعرض الطبقات بإننا نقفلها.

</div>

## 14. Deciding where to go next, and how to get there

Three strategies decide where to go; one planner decides how to get there. The proposal's hypothesis was that nearest-frontier would win in open terrain and DFS in corridors. We implemented both faithfully, and added a third: a utility score that weighs expected information against terrain-weighted cost, hazards and battery. You will see in the results which one actually won.

<div dir="rtl" align="right">

تلات استراتيجيات بتقرر نروح فين، ومخطّط واحد بيقرر نوصل إزاي. فرضية المقترح كانت إن nearest-frontier هيكسب في الأرض المفتوحة وDFS في الممرات. نفّذنا الاتنين بأمانة، وضفنا تالت: درجة منفعة بتوازن المعلومات المتوقعة مع التكلفة الموزونة بالتضاريس والمخاطر والبطارية. هتشوفوا في النتايج مين اللي كسب فعلاً.

</div>

## 15. AI where it changes what the rover does

Three uses of AI, each with a visible consequence. The terrain classifier is real machine learning — a random forest over texture features — and its predictions enter the planner's cost map, so the rover visibly avoids sand and mud. It is fast, too: the forest is evaluated straight from its trees, about one millisecond per prediction instead of ten, with identical answers. The fault detector is statistics, and it decides which sensors to trust. The utility explorer is a decision function. We are explicit about the scope: nothing here is a large model; everything trains or runs locally in seconds.

<div dir="rtl" align="right">

تلات استخدامات للذكاء الاصطناعي، كل واحد ليه أثر واضح. مصنّف التضاريس ده machine learning حقيقي، random forest على خصائص النسيج، وتوقعاته بتدخل في خريطة التكلفة بتاعة المخطّط، فالروفر بيتفادى الرمل والطين قدّامك. وكمان سريع: بقينا نحسب التوقع من الشجر على طول، فبقى حوالي مللي ثانية بدل عشرة، وبنفس النتيجة بالظبط. كاشف الأعطال ده إحصاء، وهو اللي بيقرر نثق في أنهي حساسات. مستكشف المنفعة دالة قرار. وإحنا واضحين في النطاق: مفيش هنا أي موديل كبير، كل حاجة بتتدرّب أو بتشتغل محلياً في ثواني.

</div>

## 16. Same robot, same code — only the configuration changes

The three environments stress different things. The cave is about corridors, darkness and dead ends. Mars is about open terrain, slip and the lack of a magnetic field. Under water, the whole sensor suite changes — thrusters, sonar, a Doppler log — and still the same control, estimation and decision code runs. That is the claim of the proposal, and it is what makes the comparisons in the results fair.

<div dir="rtl" align="right">

التلات بيئات بتضغط على حاجات مختلفة. الكهف عن الممرات والضلمة والطرق المسدودة. المريخ عن الأرض المفتوحة والانزلاق وغياب المجال المغناطيسي. تحت الميّه طقم الحساسات كله بيتغيّر، دوافع ومسح سوناري وDoppler log، وبرضه نفس كود التحكم والتقدير والقرار هو اللي شغّال. ده ادّعاء المقترح، وده اللي بيخلّي المقارنات في النتايج عادلة.

</div>

## 17. A desktop app to watch, test and drive the rover

The application is a conventional desktop program built with Qt, shown here in English with the light theme and in Egyptian Arabic with the dark theme, where the whole layout mirrors right to left. The header carries the mission — number, world, clock and status — and the controls: new mission, pause, stop, restart, speed up to sixteen times, lights, the phone console and sending the report. The side panel sets up the mission and can fold away to a strip. Six live cards summarise it — mapped, distance, battery, link, behaviour and position error — and below them the two maps, ground truth and belief. The tabs at the bottom expose the inner loop: every sensor, the motor control loop, statistics, the radio link and an event log. Any sensor can be broken with one click while the mission runs. We also designed it to stay calm: the status bar shows one alert at a time with a count of the others, and buttons that cannot act right now are greyed out instead of failing silently.

<div dir="rtl" align="right">

البرنامج ده برنامج ديسكتوب عادي معمول بـ Qt، وهنا شايفينه مرتين: مرة بالإنجليزي والثيم الفاتح، ومرة بالعربي المصري والثيم الغامق، والشاشة كلها بتتقلب من اليمين للشمال. فوق عندك المهمة نفسها، رقمها والبيئة والوقت وحالتها، وجنبها الأزرار: مهمة جديدة، وقّف مؤقت، خلّص، ابدأ من الأول، السرعة لحد ستاشر مرة، النور، كونسول الموبايل، وابعت التقرير. اللوحة الجانبية بتجهّز فيها المهمة، وتقدر تطبّقها لشريط صغير لو عايز مساحة. تحتها ست كروت لايف بيلخّصوا الدنيا: اتكشف قد إيه، مشي قد إيه، البطارية، الإشارة، بيعمل إيه دلوقتي، وتايه قد إيه في الموضع. وبعدهم الخريطتين، الحقيقة واللي الروبوت فاكره. والتابات اللي تحت بتوريك اللي جوّه: كل حساس، لوب المواتير، الإحصائيات، الراديو، وسجل الأحداث. وأي حساس تقدر تبوّظه بضغطة والمهمة شغّالة. وكمان عملناه هادي: شريط الحالة بيعرض تنبيه واحد بس، وجنبه عدد الباقيين، والزرار اللي مينفعش يشتغل دلوقتي بيبقى رمادي بدل ما تدوس عليه ومايحصلش حاجة.

</div>

## 18. Drive it from a phone or a game controller

Remote control is where the communication activity from Robot Behaviour meets the argument for autonomy. The desktop opens a console for a phone or tablet and shows its address and a QR code: scan it and you drive, with the joystick inside a ring of live sonar readings. A game controller works too, on the desktop or on the phone, and it drives like a racing game: cross is gas, triangle is reverse, the stick steers, and the stick alone means "go that way". Whatever you drive with, every command travels through a simulated radio link that weakens with distance and with each wall between the rover and its base. When you drive deep into the cave the link drops, a short alert says so — the same alert rules on the desktop and the phone, held long enough to read, never a popup — and after three seconds the rover takes over and drives itself back into range. The lesson writes itself: a rover that cannot decide alone is lost the moment the radio is.

<div dir="rtl" align="right">

التحكم عن بُعد هو المكان اللي نشاط الاتصالات من Robot Behaviour بيقابل فيه حجّة الاستقلالية. من البرنامج بتفتح كونسول للموبايل أو التابلت، ويطلعلك العنوان وQR code: تصوّره بالموبايل وتسوق على طول، والجويستيك في النص وحواليه دايرة قرايات السونار، فبتحس بالحيطة قبل ما تخبط فيها. ودراع الألعاب كمان شغّال، بالسلك أو بالبلوتوث، على الكمبيوتر أو على الموبايل، وبيسوق زي ألعاب العربيات بالظبط: إكس بنزين، المثلث رجوع، والعصاية أو الأسهم للاتجاه، ولو حرّكت العصاية لوحدها يبقى بتقوله روح من هنا. وأيًّا كان بتسوق بإيه، كل أمر بيعدّي على وصلة راديو متحاكية بتضعف مع المسافة ومع كل حيطة بين الروفر والقاعدة. لما تدخل جوه الكهف بعيد، الإشارة بتقع، ويطلعلك تنبيه صغير يقولك كده، ونفس قواعد التنبيه دي على الكمبيوتر والموبايل، بيفضل قدامك وقت كفاية تقراه، ومفيش popup ولا اهتزاز. وبعد تلات ثواني الروفر بياخد التحكم ويرجع بنفسه لحد ما يدخل في المدى. الدرس بيكتب نفسه: روفر مش قادر يقرر لوحده بيضيع في اللحظة اللي الراديو بيضيع فيها.

</div>

## 19. Results

Part four: what we measured. Every number comes from a run, and every run is a different generated map.

<div dir="rtl" align="right">

الجزء الرابع: النتايج. 264 تجربة، وكل رقم هنقوله جاي من تجربة.

</div>

## 20. The AI explorer won in all three worlds

Here is the hypothesis test. The proposal predicted DFS in corridors and nearest-frontier in the open. DFS did win the cave among the two classical methods. But nearest-frontier was the weakest everywhere — greedy on distance, it chases crumbs. The utility explorer, which weighs how much it expects to learn against how much the path costs, came first in all three worlds. And no rover fell into a pit in ninety runs — the cliff layer works.

<div dir="rtl" align="right">

ده اختبار الفرضية. المقترح توقّع DFS في الممرات وnearest-frontier في المفتوح. DFS فعلاً كسب الكهف من بين الطريقتين الكلاسيكيتين. بس nearest-frontier كان الأضعف في كل مكان، طمّاع على المسافة، بيجري ورا الفتافيت. مستكشف المنفعة، اللي بيوازن هيتعلّم قد إيه مع المسار هيكلّف قد إيه، جه الأول في التلات عوالم. ومفيش روفر وقع في حفرة في تسعين تجربة، طبقة الحافة شغّالة.

</div>

## 21. Remove one sensor at a time: which ones are essential?

The ablation answers the question the supervisor cares about most: which sensors earn their place. Kill the sonar and coverage collapses; kill the ground-speed sensor and the estimate is five to sixteen metres off; kill the compass or sun sensor and the map rotates away. Kill the cliff switches and one rover in four ends in a crater. The infrared and bumpers cost almost nothing to lose — they are the last line of defence, which is exactly the role we gave them.

<div dir="rtl" align="right">

الـ ablation بيجاوب على السؤال اللي الدكتورة مهتمة بيه أكتر حاجة: أنهي حساسات تستاهل مكانها. اقتل السونار والتغطية تنهار، اقتل حساس السرعة الأرضية والتقدير يبعد من خمسة لستاشر متر، اقتل البوصلة أو حساس الشمس والخريطة تلف. اقتل حساسات الحافة وروفر من كل أربعة ينتهي في فوهة. الإنفراريد والبامبرز خسارتهم مش بتكلّف تقريباً حاجة، هما خط الدفاع الأخير، وده بالظبط الدور اللي ادّيناهولهم.

</div>

## 22. Conclusion

Part five: the conclusion, then the demo video.

<div dir="rtl" align="right">

الجزء الأخير: اللي طلعنا بيه، وبعده فيديو الديمو.

</div>

## 23. One robot, three unknown worlds — only the configuration changed

Five things we take away. First, building from the motors up was not an academic exercise — the control problems are real and visible. Second, sensor placement is a safety decision. Third, fusion turns a drifting robot into one that can trust its map. Fourth, measuring beat assuming: our own hypothesis was half wrong. And fifth, autonomy is what is left when the radio fails — the rover that drives itself home is the whole point. Four natural next steps. Scan matching would close the loop between the map and the pose. A learned explorer could replace our hand-tuned utility weights, trained in the same harness that produced our results. The radio model is already there for a multi-robot version. And because the controller analysis is essentially a wiring list, the step to real hardware is a matter of interfaces, not of rewriting the robot.

<div dir="rtl" align="right">

خمس حاجات طالعين بيهم. أولاً، البناء من المواتير وطالعين مكانش تمرين أكاديمي، مشاكل التحكم حقيقية وباينة. تانياً، مكان تركيب الحساس قرار أمان. تالتاً، الدمج بيحوّل روبوت بينزاح لروبوت يقدر يثق في خريطته. رابعاً، القياس غلب الافتراض، فرضيتنا إحنا كانت نص غلط. وخامساً، الاستقلالية هي اللي بتفضل لما الراديو يقع، الروفر اللي بيسوق نفسه للبيت هو الفكرة كلها. أربع خطوات طبيعية جاية. الـ scan matching هيقفل الدايرة بين الخريطة والموضع. مستكشف متعلّم ممكن يحل محل أوزان المنفعة اللي ظبطناها بإيدينا، ويتدرّب في نفس المنصّة اللي طلّعت نتايجنا. موديل الراديو موجود جاهز لنسخة متعددة الروبوتات. وعشان تحليل الكنترولر عملياً قايمة توصيلات، الخطوة للهاردوير الحقيقي مسألة واجهات، مش إعادة كتابة للروبوت.

</div>

## 24. Where the methods come from

Our references. The course comes first: Bräunl's Embedded Robotics, which the lectures follow, and the lecture notes themselves; the PID, H-bridge, encoder and driving-straight material is from there. Then the classic papers behind each design choice: Brooks for subsumption, Elfes for occupancy grids, Thrun, Burgard and Fox for probabilistic localisation, Hart, Nilsson and Raphael for A star, Yamauchi for frontier exploration, Coulter for pure pursuit, and Breiman for the random forest.

<div dir="rtl" align="right">

المراجع. الأول المنهج: كتاب Embedded Robotics لـ Bräunl اللي المحاضرات ماشية عليه، والمحاضرات نفسها — الـ PID والـ H-bridge والـ encoders والمشي المستقيم من هناك. وبعدين الأوراق الأساسية ورا كل قرار: Brooks للـ subsumption، وElfes للـ occupancy grid، وThrun وBurgard وFox لتحديد المكان بالاحتمالات، وHart وNilsson وRaphael للـ A star، وYamauchi للـ frontier exploration، وCoulter للـ pure pursuit، وBreiman للـ random forest.

</div>

## 25. demo-video

The demo video: three minutes of the application running — a cave mission and its two maps, the motor loop, a sensor breaking, the radio failing and the rover coming home, driving from a phone and a game controller, a report, Mars, underwater and the Arabic interface.

<div dir="rtl" align="right">

فيديو الديمو: تلات دقايق للبرنامج وهو شغال — مهمة في الكهف وخريطتينها، ولوب الموتور، وسنسور بيبوظ، والراديو بيقطع والروبوت بيرجع لوحده، والسواقة من الموبايل والدراع، والتقرير، والمريخ وتحت المية، والواجهة بالعربي.

</div>

## 26. Thank you

Thank you for listening. We are happy to answer your questions.

<div dir="rtl" align="right">

شكرًا لحضرتكم، وتحت أمركم في أي سؤال.

</div>
