# PyRov — Multi-Environment Autonomous Exploration Rover — speaker notes

English notes first, then the same note in Egyptian Arabic. One entry per slide, in deck order.

## 1. PyRov

Good morning. We are the PyRov team. PyRov is an exploration rover that we built as a Python simulation — not from the map downwards, but from the motors upwards: DC motors, encoders, PID, a full sensor suite, and only then mapping and decision making. The same robot explores a cave, the surface of Mars and an underwater site. In the next twenty minutes we will show what we built, why every sensor sits where it sits, and what we measured.

<div dir="rtl" align="right">

صباح الخير. إحنا فريق PyRov. ‏PyRov روفر استكشاف بنيناه كمحاكاة بالبايثون، بس مش من الخريطة ونازلين، لأ، من المواتير وطالعين: مواتير DC، إنكودرز، PID، طقم حساسات كامل، وبعد كده بس ييجي رسم الخريطة واتخاذ القرار. نفس الروبوت بيستكشف كهف، وسطح المريخ، وموقع تحت الميّه. في العشرين دقيقة الجايين هنوريكم بنينا إيه، وليه كل حساس متركّب في مكانه بالذات، وقيسنا إيه.

</div>

## 2. A rover that explores a place it has never seen — safely, on its own

In one sentence: PyRov is a software rover that is dropped into an unknown place and has to explore it autonomously. The problem is real — Mars, collapsed mines, flooded caves — and simulation is the only safe and repeatable way to develop and compare the algorithms. The four numbers on the right summarise the project: three environments with one codebase, more than twenty modelled sensors, 264 measured runs, and up to 97 percent of the reachable area mapped.

<div dir="rtl" align="right">

في جملة واحدة: PyRov روفر سوفتوير بيتحط في مكان مجهول ولازم يستكشفه لوحده. المشكلة حقيقية، المريخ، المناجم المنهارة، الكهوف الغرقانة، والمحاكاة هي الطريقة الوحيدة الآمنة واللي تتكرر عشان نطوّر الخوارزميات ونقارن بينها. الأربع أرقام اللي على اليمين بتلخّص المشروع: تلات بيئات بكود واحد، أكتر من عشرين حساس متمودلين، 264 تجربة متقاسة، ولحد 97 في الميّه من المساحة اللي ينفع يوصلها اترسمت.

</div>

## 3. Why a robot has to decide for itself

Why autonomy at all? Because in the places we care about, a human cannot drive the robot: the signal is delayed, blocked or gone. The animation on the right is a real run from our simulator — on the left the true cave the robot never sees, on the right the map it builds by itself. Our central design decision was to write one engine and treat each environment as data. Later we will show that this is exactly what makes the comparisons fair.

<div dir="rtl" align="right">

ليه الاستقلالية أصلاً؟ عشان في الأماكن اللي بتهمنا، البني آدم مش هيقدر يسوق الروبوت: الإشارة إما متأخرة أو مقطوعة أو مش موجودة خالص. الأنيميشن اللي على اليمين ده تجربة حقيقية من المحاكي بتاعنا، على الشمال الكهف الحقيقي اللي الروبوت عمره ما بيشوفه، وعلى اليمين الخريطة اللي بيبنيها بنفسه. القرار التصميمي المركزي عندنا كان إننا نكتب محرّك واحد ونتعامل مع كل بيئة على إنها داتا. وبعدين هنوريكم إن ده بالظبط اللي بيخلّي المقارنات عادلة.

</div>

## 4. Every course topic is a working layer of the rover

This table is our map of the course. Each row is a lecture — actuators, encoders, control, sensors, behaviour, navigation, communication — and each is implemented as a module that the others depend on. We will go through them in that order: first the analysis of the hardware we simulate, then the design of the software on top, then the measurements.

<div dir="rtl" align="right">

الجدول ده هو خريطتنا للكورس. كل صف محاضرة، المشغّلات، الإنكودرز، التحكم، الحساسات، السلوك، الملاحة، الاتصالات، وكل واحدة متنفّذة كموديول الباقيين معتمدين عليه. هنمشي عليهم بالترتيب ده: الأول تحليل الهاردوير اللي بنحاكيه، بعدين تصميم السوفتوير اللي فوقه، وبعدين القياسات.

</div>

## 5. Analysis

Part two is the analysis: the hardware we simulate. We start with the sensors, because the supervisor asked for many sensors with well-justified placement; then the actuators and the control loop; then the on-board controller that runs everything.

<div dir="rtl" align="right">

الجزء التاني هو التحليل: الهاردوير اللي بنحاكيه. هنبدأ بالحساسات، عشان الدكتورة طلبت حساسات كتير بأماكن تركيب ليها مبرر، بعدين المشغّلات ولوب التحكم، بعدين الكنترولر اللي على الروبوت واللي بيشغّل كل حاجة.

</div>

## 6. The sensor suite, classified the way the course classifies it

Every sensor carries its classification from Sensors 1: local or global, internal or external, active or passive, binary, analog or digital. The suite is not the same in every world: Mars has a sun sensor instead of a compass, underwater has a Doppler velocity log instead of encoders and no infrared because light does not travel. The code that reads them never changes — only the configuration says what is mounted.

<div dir="rtl" align="right">

كل حساس شايل تصنيفه من محاضرة Sensors 1: محلي ولا عام، داخلي ولا خارجي، نشط ولا سلبي، ثنائي ولا تناظري ولا رقمي. الطقم مش هو هو في كل بيئة: المريخ فيه حساس شمس بدل البوصلة، وتحت الميّه فيه Doppler velocity log بدل الإنكودرز ومفيش إنفراريد عشان الضوء مش بيمشي. الكود اللي بيقراهم عمره ما بيتغيّر، الكونفيج بس هو اللي بيقول إيه المركّب.

</div>

## 7. Where each sensor sits — and the failure it prevents

This is the rover from above. Teal dots are the eight sonars, red lines the three infrared beams, green dots the six cliff switches. Two placement decisions came from failures: the rear cliff pair, because our escape behaviours reverse and a rover fell into a crater backwards, and the side pair, because the body brushed a pit while turning. The infrared sensors were first mounted at plus and minus thirty degrees — that left a blind strip exactly where the body is, so they now all face forward across the width.

<div dir="rtl" align="right">

ده الروفر من فوق. النقط التركواز هي التمن سونارات، الخطوط الحمرا التلات شعاعات إنفراريد، النقط الخضرا الست حساسات الحافة. قرارين في التركيب جم من فشل حصل فعلاً: زوج الحافة الخلفي، عشان سلوكيات الهروب عندنا بترجع لورا وروفر وقع في فوهة وهو راجع بضهره، والزوج الجانبي، عشان الجسم لمس حفرة وهو بيلف. حساسات الإنفراريد كانت متركّبة الأول على زائد وناقص تلاتين درجة، وده ساب شريط أعمى بالظبط مكان الجسم، فدلوقتي كلهم باصّين لقدّام على عرض الروفر.

</div>

## 8. Sensors lie in specific ways — so we modelled the lies

A simulated sensor that returns the truth plus Gaussian noise teaches nothing. Ours reproduce the specific failure modes from Sensors 2: the sonar loses echoes at grazing angles, the infrared sensor has a non-linear curve that folds back below six centimetres, the gyro drifts with a bias, and everything goes through an A/D converter. These are not decorations — each one caused a real bug during development that we had to understand and fix, and we will come back to that in the lessons.

<div dir="rtl" align="right">

حساس متحاكي بيرجّع الحقيقة زائد شوية ضوضاء جاوسية مش بيعلّم حاجة. حساساتنا بتعيد إنتاج أنماط الفشل بالذات من محاضرة Sensors 2: السونار بيضيّع الصدى عند الزوايا المايلة، الإنفراريد ليه منحنى غير خطي بيرجع ينطبق تحت ست سنتيمتر، الجيرو بينزاح بانحياز، وكل حاجة بتعدّي على محوّل A/D. دي مش زينة، كل واحدة فيهم عملت bug حقيقي وقت التطوير واضطرينا نفهمه ونصلّحه، وهنرجع للكلام ده في الدروس المستفادة.

</div>

## 9. Two DC motors, an H-bridge and a PWM signal

The actuator model follows Actuators 1 and 2 closely: an H-bridge for direction, PWM for the average voltage, and a motor whose speed is not proportional to the duty cycle. The dead band and the load dependence are what make open-loop control useless — the same duty gives a different speed on sand — and that motivates the next slide.

<div dir="rtl" align="right">

موديل المشغّلات ماشي بالظبط مع محاضرتي Actuators 1 و2: H-bridge للاتجاه، PWM للجهد المتوسط، وموتور سرعته مش متناسبة مع الـ duty cycle. المنطقة الميّتة والاعتماد على الحمل هما اللي بيخلّوا التحكم المفتوح ملوش لازمة، نفس الـ duty بيدّي سرعة مختلفة على الرمل، وده اللي بيمهّد للشريحة الجاية.

</div>

## 10. Encoder → PID → PWM, 20 times a second

This is the Control lecture running. We implemented on-off, on-off with hysteresis, and the incremental PID exactly as derived in class, and the plot shows the textbook behaviour: the P controller keeps a steady-state error because its output goes to zero when the error does, and the integral term removes it. The straight-driving controller is the structure from figure 5.16: integrate the position difference of the two wheels and feed it back. In the application you can watch this loop live in the Motor control tab.

<div dir="rtl" align="right">

دي محاضرة التحكم وهي شغّالة. نفّذنا on-off، وon-off بـ hysteresis، والـ PID التزايدي بالظبط زي ما اتشرح في المحاضرة، والرسمة بتوري سلوك الكتاب: متحكم P بيسيب خطأ في الحالة المستقرة لأن خرجه بيروح للصفر لما الخطأ يروح للصفر، والحد التكاملي هو اللي بيشيله. متحكم المشي عدل هو نفس الهيكل بتاع شكل 5.16: نكامل فرق الموضع بين العجلتين ونرجّعه. في البرنامج تقدر تتفرج على اللوب ده لايف في تاب Motor control.

</div>

## 11. One embedded controller, one 50 ms loop

The microcontroller analysis: the whole robot is one control loop at twenty hertz, the same structure as the EyeCon examples in Embedded Robotics. The table on the right lists the interfaces such a controller would need — pulse counters for the encoders, an A/D converter with a multiplexer for the analog sensors, digital inputs for the switches, I-squared-C for the inertial unit, and two PWM channels for the H-bridges. In the simulator this loop is the step function of the mission.

<div dir="rtl" align="right">

تحليل الميكروكنترولر: الروبوت كله لوب تحكم واحد بعشرين هرتز، نفس هيكل أمثلة EyeCon في Embedded Robotics. الجدول اللي على اليمين فيه الواجهات اللي كنترولر زي ده هيحتاجها: عدّادات نبضات للإنكودرز، محوّل A/D بـ multiplexer للحساسات التناظرية، مداخل رقمية للمفاتيح، I2C لوحدة القصور الذاتي، وقناتين PWM للـ H-bridges. في المحاكي اللوب ده هو دالة step بتاعة المهمة.

</div>

## 12. Design & Implementation

Part three: the software design built on that hardware, and how it was implemented.

<div dir="rtl" align="right">

الجزء التالت: تصميم السوفتوير المبني على الهاردوير ده، واتنفّذ إزاي.

</div>

## 13. The world the robot never sees, and the belief it builds

The architecture has one rule: the robot never touches the world directly. The world and the robot's true state are ground truth; only the sensors read them; everything the robot knows lives in its belief — a pose estimate and a map; and decisions are made on the belief alone. The interface shows both side by side, which is how you see the difference between what is true and what the robot thinks. Everything that differs between environments is configuration.

<div dir="rtl" align="right">

المعمارية ليها قاعدة واحدة: الروبوت عمره ما بيلمس العالم على طول. العالم والحالة الحقيقية للروبوت هما الـ ground truth، الحساسات بس هي اللي بتقراهم، وكل اللي الروبوت عارفه عايش في اعتقاده، تقدير للموضع وخريطة، والقرارات بتتاخد على الاعتقاد بس. الواجهة بتعرض الاتنين جنب بعض، وده اللي بيخلّيك تشوف الفرق بين اللي حقيقي واللي الروبوت فاكره. وكل حاجة بتختلف بين البيئات هي كونفيج.

</div>

## 14. Where am I? Three answers, drawn side by side

Localisation is where the sensor analysis pays off. The red estimate is pure dead reckoning and it drifts by metres. The green one fuses three things: a ground-speed sensor that does not see wheel slip, a gyro for fast heading changes, and a compass or sun sensor to bound the gyro's drift. The map is a probabilistic grid; its rules were tuned against real failures — for instance, an echo places the obstacle just beyond the surface, otherwise half the hits fall inside the corridor and the walls grow thick.

<div dir="rtl" align="right">

تحديد الموضع هو المكان اللي تحليل الحساسات بيثمر فيه. التقدير الأحمر ده dead reckoning صافي وبينزاح بالأمتار. الأخضر بيدمج تلات حاجات: حساس سرعة أرضية مش بيشوف انزلاق العجل، جيرو لتغيّرات الاتجاه السريعة، وبوصلة أو حساس شمس عشان يحدّ انزياح الجيرو. الخريطة شبكة احتمالية، وقواعدها اتظبطت على فشل حقيقي، مثلاً الصدى بيحط العائق بعد السطح بشوية، غير كده نص الضربات بتقع جوه الممر والحيطان بتتخن.

</div>

## 15. Subsumption: the higher layer takes the wheels

Behaviour is organised as a subsumption architecture, straight from the Robot Behaviour lecture. Ten layers; the highest one that wants control wins. The reflexes are on top — stop, escape, cliff, slope — then avoidance, then the operator, then return-home, then exploration. The avoidance layer is itself an on-off controller with a hysteresis band, which is the Control lecture applied to behaviour. And the manual driving mode exists to demonstrate the layers by switching them off.

<div dir="rtl" align="right">

السلوك متنظّم كمعمارية subsumption، من محاضرة Robot Behaviour على طول. عشر طبقات، وأعلى واحدة عايزة التحكم هي اللي بتكسب. ردود الفعل فوق، stop وescape وcliff وslope، بعدين التفادي، بعدين المشغّل البشري، بعدين الرجوع للبيت، بعدين الاستكشاف. طبقة التفادي نفسها متحكم on-off بنطاق hysteresis، يعني محاضرة التحكم متطبّقة على السلوك. ووضع السواقة اليدوية موجود عشان نعرض الطبقات بإننا نقفلها.

</div>

## 16. Deciding where to go next, and how to get there

Three strategies decide where to go; one planner decides how to get there. The proposal's hypothesis was that nearest-frontier would win in open terrain and DFS in corridors. We implemented both faithfully, and added a third: a utility score that weighs expected information against terrain-weighted cost, hazards and battery. You will see in the results which one actually won.

<div dir="rtl" align="right">

تلات استراتيجيات بتقرر نروح فين، ومخطّط واحد بيقرر نوصل إزاي. فرضية المقترح كانت إن nearest-frontier هيكسب في الأرض المفتوحة وDFS في الممرات. نفّذنا الاتنين بأمانة، وضفنا تالت: درجة منفعة بتوازن المعلومات المتوقعة مع التكلفة الموزونة بالتضاريس والمخاطر والبطارية. هتشوفوا في النتايج مين اللي كسب فعلاً.

</div>

## 17. AI only where it changes what the rover does

Three uses of AI, each with a visible consequence. The terrain classifier is real machine learning — a random forest over texture features — and its predictions enter the planner's cost map, so the rover visibly avoids sand and mud. The fault detector is statistics, and it decides which sensors to trust. The utility explorer is a decision function. We are explicit about the scope: nothing here is a large model; everything trains or runs locally in seconds.

<div dir="rtl" align="right">

تلات استخدامات للذكاء الاصطناعي، كل واحد ليه أثر واضح. مصنّف التضاريس ده machine learning حقيقي، random forest على خصائص النسيج، وتوقعاته بتدخل في خريطة التكلفة بتاعة المخطّط، فالروفر بيتفادى الرمل والطين قدّامك. كاشف الأعطال ده إحصاء، وهو اللي بيقرر نثق في أنهي حساسات. مستكشف المنفعة دالة قرار. وإحنا واضحين في النطاق: مفيش هنا أي موديل كبير، كل حاجة بتتدرّب أو بتشتغل محلياً في ثواني.

</div>

## 18. Three worlds, one robot — the configuration is the only difference

The three environments stress different things. The cave is about corridors, darkness and dead ends. Mars is about open terrain, slip and the lack of a magnetic field. Under water, the whole sensor suite changes — thrusters, sonar, a Doppler log — and still the same control, estimation and decision code runs. That is the claim of the proposal, and it is what makes the comparisons in the results fair.

<div dir="rtl" align="right">

التلات بيئات بتضغط على حاجات مختلفة. الكهف عن الممرات والضلمة والطرق المسدودة. المريخ عن الأرض المفتوحة والانزلاق وغياب المجال المغناطيسي. تحت الميّه طقم الحساسات كله بيتغيّر، دوافع ومسح سوناري وDoppler log، وبرضه نفس كود التحكم والتقدير والقرار هو اللي شغّال. ده ادّعاء المقترح، وده اللي بيخلّي المقارنات في النتايج عادلة.

</div>

## 19. A desktop application that shows truth and belief side by side

The application is a conventional desktop program, built with Qt. The left panel configures a mission; the two maps show ground truth and belief; the tabs below expose the inner loop — every sensor reading, the motor control loop, statistics and the radio link. Any sensor can be broken with one click while the mission runs, which is how we demonstrate the fault detector and the safety layers.

<div dir="rtl" align="right">

البرنامج ده برنامج ديسكتوب عادي، معمول بـ Qt. اللوحة الشمال بتظبط المهمة، الخريطتين بيعرضوا الحقيقة والاعتقاد، والتابات اللي تحت بتكشف اللوب الداخلي، كل قراية حساس، لوب التحكم في المواتير، الإحصائيات، ووصلة الراديو. أي حساس ممكن تكسره بضغطة واحدة والمهمة شغّالة، وده اللي بنعرض بيه كاشف الأعطال وطبقات الأمان.

</div>

## 20. Drive it from a phone — through a radio that can fail

Remote control is where the communication activity from Robot Behaviour meets the argument for autonomy. Every command from the phone travels through a simulated radio link that weakens with distance and with each wall between the rover and its base. When you drive deep into the cave the link drops, the console tells you so, and after three seconds the rover takes over and drives itself back into range. The lesson writes itself: a rover that cannot decide alone is lost the moment the radio is.

<div dir="rtl" align="right">

التحكم عن بُعد هو المكان اللي نشاط الاتصالات من Robot Behaviour بيقابل فيه حجّة الاستقلالية. كل أمر من الموبايل بيعدّي على وصلة راديو متحاكية بتضعف مع المسافة ومع كل حيطة بين الروفر والقاعدة. لما تسوق جوه الكهف بعيد، الوصلة بتقع، الكونسول بيقولك، وبعد تلات ثواني الروفر بياخد التحكم ويرجع بنفسه لحد ما يدخل في المدى. الدرس بيكتب نفسه: روفر مش قادر يقرر لوحده بيضيع في اللحظة اللي الراديو بيضيع فيها.

</div>

## 21. Every mission leaves evidence

Engineering around the robot: every mission produces a report that lands in the team's Drive folder, the same mission object runs headless for the experiments, forty-nine tests pin the physics and the behaviours, and a one-click installer lets anyone on the team run it.

<div dir="rtl" align="right">

الهندسة اللي حوالين الروبوت: كل مهمة بتطلع تقرير بينزل في فولدر Drive بتاع الفريق، نفس كائن المهمة بيشتغل من غير شاشة للتجارب، تسعة وأربعين test بيثبّتوا الفيزياء والسلوكيات، وinstaller بضغطة واحدة بيخلّي أي حد في الفريق يشغّله.

</div>

## 22. Results & Tests

Part four: what we measured. Every number comes from the headless batch runner; every seed is a different generated map and a different noise sequence.

<div dir="rtl" align="right">

الجزء الرابع: قيسنا إيه. كل رقم جاي من مشغّل الدفعات من غير شاشة، وكل seed خريطة متولّدة مختلفة وتسلسل ضوضاء مختلف.

</div>

## 23. The hypothesis was half right — and the AI explorer won everywhere

Here is the hypothesis test. The proposal predicted DFS in corridors and nearest-frontier in the open. DFS did win the cave among the two classical methods. But nearest-frontier was the weakest everywhere — greedy on distance, it chases crumbs. The utility explorer, which weighs how much it expects to learn against how much the path costs, came first in all three worlds. And no rover fell into a pit in ninety runs — the cliff layer works.

<div dir="rtl" align="right">

ده اختبار الفرضية. المقترح توقّع DFS في الممرات وnearest-frontier في المفتوح. DFS فعلاً كسب الكهف من بين الطريقتين الكلاسيكيتين. بس nearest-frontier كان الأضعف في كل مكان، طمّاع على المسافة، بيجري ورا الفتافيت. مستكشف المنفعة، اللي بيوازن هيتعلّم قد إيه مع المسار هيكلّف قد إيه، جه الأول في التلات عوالم. ومفيش روفر وقع في حفرة في تسعين تجربة، طبقة الحافة شغّالة.

</div>

## 24. Fused localisation is as good as knowing the truth

Localisation in numbers. Encoders alone: two to five metres of error in five minutes — slip in mud and sand, thrusters that never touch the ground. The fused estimate: four to seventeen centimetres. And the important finding: the rover with the fused estimate explores as well as a rover that knows its true position, so the remaining error no longer limits the mission.

<div dir="rtl" align="right">

تحديد الموضع بالأرقام. الإنكودرز لوحدها: من مترين لخمس أمتار خطأ في خمس دقايق، انزلاق في الطين والرمل، ودوافع عمرها ما بتلمس الأرض. التقدير المدموج: من أربعة لسبعتاشر سنتيمتر. والنتيجة المهمة: الروفر بالتقدير المدموج بيستكشف كويس زي روفر عارف موضعه الحقيقي بالظبط، يعني الخطأ المتبقي مبقاش بيحدّ المهمة.

</div>

## 25. Kill one sensor at a time: which ones the rover cannot live without

The ablation answers the question the supervisor cares about most: which sensors earn their place. Kill the sonar and coverage collapses; kill the ground-speed sensor and the estimate is five to sixteen metres off; kill the compass or sun sensor and the map rotates away. Kill the cliff switches and one rover in four ends in a crater. The infrared and bumpers cost almost nothing to lose — they are the last line of defence, which is exactly the role we gave them.

<div dir="rtl" align="right">

الـ ablation بيجاوب على السؤال اللي الدكتورة مهتمة بيه أكتر حاجة: أنهي حساسات تستاهل مكانها. اقتل السونار والتغطية تنهار، اقتل حساس السرعة الأرضية والتقدير يبعد من خمسة لستاشر متر، اقتل البوصلة أو حساس الشمس والخريطة تلف. اقتل حساسات الحافة وروفر من كل أربعة ينتهي في فوهة. الإنفراريد والبامبرز خسارتهم مش بتكلّف تقريباً حاجة، هما خط الدفاع الأخير، وده بالظبط الدور اللي ادّيناهولهم.

</div>

## 26. How we made sure the numbers mean something

A word on method. Forty-nine tests pin the physics and behaviours so that a change in one layer cannot silently break another. The experiments run the identical mission object without a window, many seeds in parallel, and report means with their spread. And several of our hardest bugs were found by the simulated physics itself — the specular echoes erasing walls, for example — and each one turned into a test.

<div dir="rtl" align="right">

كلمة عن المنهج. تسعة وأربعين test بيثبّتوا الفيزياء والسلوكيات عشان تغيير في طبقة ميكسرش طبقة تانية في السكوت. التجارب بتشغّل نفس كائن المهمة بالظبط من غير شاشة، seeds كتير بالتوازي، وبتطلع متوسطات مع تشتّتها. وكام bug من أصعب اللي قابلناهم المحاكاة الفيزيائية نفسها هي اللي كشفتهم، الصدى المنعكس اللي كان بيمسح الحيطان مثلاً، وكل واحد منهم اتحوّل لـ test.

</div>

## 27. Conclusion & Future

Part five: conclusions and future work.

<div dir="rtl" align="right">

الجزء الخامس: الخلاصة والشغل الجاي.

</div>

## 28. One modular robot explored three unknown worlds by changing only its configuration

Five things we take away. First, building from the motors up was not an academic exercise — the control problems are real and visible. Second, sensor placement is a safety decision. Third, fusion turns a drifting robot into one that can trust its map. Fourth, measuring beat assuming: our own hypothesis was half wrong. And fifth, autonomy is what is left when the radio fails — the rover that drives itself home is the whole point.

<div dir="rtl" align="right">

خمس حاجات طالعين بيهم. أولاً، البناء من المواتير وطالعين مكانش تمرين أكاديمي، مشاكل التحكم حقيقية وباينة. تانياً، مكان تركيب الحساس قرار أمان. تالتاً، الدمج بيحوّل روبوت بينزاح لروبوت يقدر يثق في خريطته. رابعاً، القياس غلب الافتراض، فرضيتنا إحنا كانت نص غلط. وخامساً، الاستقلالية هي اللي بتفضل لما الراديو يقع، الروفر اللي بيسوق نفسه للبيت هو الفكرة كلها.

</div>

## 29. Where PyRov goes next

Four natural next steps. Scan matching would close the loop between the map and the pose. A learned explorer could replace our hand-tuned utility weights, trained in the same harness that produced our results. The radio model is already there for a multi-robot version. And because the controller analysis is essentially a wiring list, the step to real hardware is a matter of interfaces, not of rewriting the robot.

<div dir="rtl" align="right">

أربع خطوات طبيعية جاية. الـ scan matching هيقفل الدايرة بين الخريطة والموضع. مستكشف متعلّم ممكن يحل محل أوزان المنفعة اللي ظبطناها بإيدينا، ويتدرّب في نفس المنصّة اللي طلّعت نتايجنا. موديل الراديو موجود جاهز لنسخة متعددة الروبوتات. وعشان تحليل الكنترولر عملياً قايمة توصيلات، الخطوة للهاردوير الحقيقي مسألة واجهات، مش إعادة كتابة للروبوت.

</div>

## 30. Thank you

Thank you. We are happy to run the live demonstration now: a cave mission, the motor loop, a broken sensor, the two localisation modes, driving from a phone, and the radio link failing and the rover returning on its own. Questions are welcome.

<div dir="rtl" align="right">

شكراً. يسعدنا نعمل العرض الحي دلوقتي: مهمة في الكهف، لوب المواتير، حساس مكسور، وضعي تحديد الموضع، السواقة من الموبايل، ووصلة الراديو وهي بتقع والروفر بيرجع لوحده. أهلاً بأي أسئلة.

</div>
