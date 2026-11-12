# SOFTWARE TEST DOCUMENTATION (STD) & USER ACCEPTANCE TESTING (UAT) REPORT
## IEEE 829-2008 / ISO/IEC/IEEE 29119-3 Standard
### Bidirectional SIBI Sign Language and Speech Translation System (SignToSpeech v0.5.0-sibi)

---

**Course:** Software Engineering (Rekayasa Perangkat Lunak) - Odd Semester 2026/2027  
**Faculty / Department:** Faculty of Engineering, Universitas Indonesia / Department of Electrical Engineering  
**Study Program:** Computer Engineering  
**Course Lecturer:** Prof. Dr. Ir. Riri Fitri Sari, M.M., M.Sc.  
**Development Team (Group 5):**  
1. Ahmad Malik Prasetyo (Student ID: 2406416270)  
2. Danish Al Fayyadh Sunarta (Student ID: 2406416951)  
3. Vanesa Kayla Zahra (Student ID: 2306161901)  

**User Partner / External Evaluator (First Party in MoU):** Raihan Muhammad Nafis Al-Kautsar (Student ID: 2406413451)  
**Evaluation Status:** FULLY ACCEPTED (100% Passed STD & UAT)  

---

## TABLE OF CONTENTS

1. [Section I: Introduction and Testing Foundations](#section-i-introduction-and-testing-foundations)
   - 1.1 Software Test Document Definition (STD / IEEE 829)
   - 1.2 User Acceptance Testing Definition (UAT)
   - 1.3 Comparative Analysis: STD vs. UAT
   - 1.4 Standards and Regulatory References
2. [Section II: System Architecture and Test Items](#section-ii-system-architecture-and-test-items)
   - 2.1 Component Architecture (SignToSpeech v0.5.0)
   - 2.2 Features to be Tested
   - 2.3 Features Not to be Tested
3. [Section III: Test Approach and Strategy](#section-iii-test-approach-and-strategy)
   - 3.1 Testing Levels
   - 3.2 Pass and Fail Criteria
   - 3.3 Suspension and Resumption Rules
4. [Section IV: Test Environment Specifications](#section-iv-test-environment-specifications)
5. [Section V: STD Test Case Matrix and Results](#section-v-std-test-case-matrix-and-results)
   - 5.1 JVM Unit Testing Summary (33 Tests)
   - 5.2 Machine Learning Parity Test (Keras vs. TFLite)
   - 5.3 Complete 25 Functional and Integration Test Cases
6. [Section VI: User Acceptance Testing (UAT) Report](#section-vi-user-acceptance-testing-uat-report)
   - 6.1 Participant Profiles and Field Setup
   - 6.2 Evaluation of 3 Core User Journeys
   - 6.3 Usability Questionnaire (5-Point Likert Scale)
   - 6.4 Qualitative Feedback and Observations
7. [Section VII: Conclusion and Formal Sign-Off](#section-vii-conclusion-and-formal-sign-off)
   - 7.1 Release Readiness Verdict
   - 7.2 Acceptance Sign-Off Sheet
8. [Section VIII: Appendix and Test Evidence Index](#section-viii-appendix-and-test-evidence-index)

---

## SECTION I: INTRODUCTION AND TESTING FOUNDATIONS

### 1.1 Software Test Document Definition (STD / IEEE 829)
A Software Test Document (STD) is a formal engineering specification that outlines the test plan, test case designs, technical pass/fail criteria, and test execution outcomes under the IEEE 829-2008 standard (adopted in ISO/IEC/IEEE 29119-3).

In the software development life cycle, the STD fulfills the **Verification** requirement (*"Are we building the product right?"*). Verification confirms through structured technical checks that the codebase, module interfaces, edge AI inference pipelines, and system throughput satisfy the requirements defined in the Software Requirements Specification (SRS). The STD encompasses:
- Unit Testing: isolated verification of logical state machines, queue buffers, and string parsers.
- Integration Testing: verification of data contracts across CameraX, MediaPipe Tasks, TFLite, and audio engines.
- Functional Black-Box Testing: boundary value analysis and equivalence partitioning across end-to-end user flows.

### 1.2 User Acceptance Testing Definition (UAT)
User Acceptance Testing (UAT) is the final testing phase where intended end users, clients, or domain partners evaluate software behavior in realistic operational settings before general release.

UAT addresses the **Validation** requirement (*"Are we building the right product?"*). Validation demonstrates that the system solves the target problem, provides intuitive ergonomics, and adheres to commitments in project agreements. For SignToSpeech, UAT confirms that the app facilitates clear two-way communication between Deaf signers and hearing service personnel.

### 1.3 Comparative Analysis: STD vs. UAT

| Comparison Dimension | Software Test Document (STD) | User Acceptance Testing (UAT) |
| :--- | :--- | :--- |
| Primary Objective | Technical verification of code, algorithms, and latency. | Operational validation of workflows, usability, and user intent. |
| Core Question | "Are we building the product right?" | "Are we building the right product?" |
| Execution Team | Internal Software Engineers and QA Leads. | External User Partner (MoU First Party) and End Users. |
| Testing Level | Unit Testing, Integration Testing, System Testing. | Acceptance Testing, Field Usability Testing. |
| Test Technique | White-Box Code Coverage and Black-Box Test Cases. | Scenario-Based User Journeys and Likert Rating Surveys. |
| Test Setting | Android Emulator (AVD Pixel 10 Pro XL) and JVM Test Harness. | Realistic operational settings and live interaction trials. |
| Exit Criteria | 100% Test Cases Passed, Zero Severity 1 or 2 Defects. | 100% Scenarios Completed, Mean Likert Usability Score >= 4.00. |
| Standard Reference | IEEE 829-2008 / ISO/IEC/IEEE 29119-3. | ISO 9241-11 (Usability and Ergonomics). |
| Document Output | Test Case Matrix, Traceability Tables, Defect Log. | UAT Scenario Records, Likert Questionnaire, Sign-Off Sheet. |

### 1.4 Standards and Regulatory References
1. IEEE Std 829-2008: Standard for Software and System Test Documentation.
2. ISO/IEC 25010:2011: Systems and software engineering - Systems and software Quality Requirements and Evaluation (SQuaRE).
3. Memorandum of Understanding (MoU): Sign-to-Speech Mobile Application Cooperation Agreement between Raihan Muhammad Nafis Al-Kautsar (First Party) and Group 5 Engineering Team (Second Party), October 2026.

---

## SECTION II: SYSTEM ARCHITECTURE AND TEST ITEMS

### 2.1 Component Architecture (SignToSpeech v0.5.0)
SignToSpeech operates completely offline using on-device edge AI, protecting user visual privacy and operating without network connectivity:
- Vision Landmark Pipeline (CameraX + MediaPipe): Captures camera frames at 30 FPS and extracts 21 3D hand landmark coordinates within 30 ms per frame.
- SIBI Static Classifier (Edge TFLite): Quantized feedforward neural network classifying 21 coordinates into 36 gesture classes in 1.2 ms per frame.
- Temporal Rolling Buffer: Circular 30-frame FIFO queue capturing dynamic temporal motions for greetings and phrases ("Halo", "Terima kasih", "Tolong").
- Speech Synthesis Engine (Android TextToSpeech API): Converts accumulated sign letters into natural spoken Indonesian.
- Speech Recognition Engine (Android SpeechRecognizer API): Transcribes spoken partner responses in Direction 2 into visual cards with high-contrast typography.
- Bidirectional State Manager: Coordinates Direction 1 to Direction 2 transitions while stopping the camera in Direction 2 to conserve battery.
- Circular Ergonomic Controls (v0.5.0 Update): Text-free round control buttons, featuring a circular blue microphone and a circular red stop button containing a balanced white rounded square.

### 2.2 Features to be Tested
- CameraX initialization, preview rendering, and target 30 FPS throughput.
- MediaPipe hand landmark tracking for 21 points across varied hand orientations.
- Static gesture recognition across 36 SIBI classes (letters A-Z and digits 1-9).
- Text accumulation buffer, single-character deletion (FIFO Backspace), and complete buffer clearing.
- One-tap quick word suggestions above the keyboard bar.
- Text-to-Speech Indonesian voice output clarity and zero-latency synthesis.
- Direction 2 Speech-to-Text transcription fidelity under standard indoor acoustic levels.
- High-contrast visual communication cards and emergency preset selection.
- Circular action buttons without text clipping or overlapping controls.
- Direction toggle transitions and Android lifecycle pauses and resumes.

### 2.3 Features Not to be Tested
- Cloud database account synchronization (the application operates strictly offline).
- Large Language Model NLP grammar correction beyond the local dictionary lookup.

---

## SECTION III: TEST APPROACH AND STRATEGY

### 3.1 Testing Levels
Testing follows four sequential engineering tiers:
- Tier 1 - Unit Testing (JVM / JUnit 4 and Robolectric): 33 automated tests validating queue behavior, string sanitation, and state machines in isolation.
- Tier 2 - Machine Learning Parity Testing: Automated numerical validation comparing Keras training outputs against quantized TFLite inference outputs using smoke_test_dynamic_pipeline.py (maximum absolute difference: 0.000000).
- Tier 3 - Functional and Integration Testing (STD): 25 black-box test cases on the Google Pixel 10 Pro XL emulator covering boundary values and fault injection.
- Tier 4 - User Acceptance Testing (UAT): Direct operational trials by the MoU client across 3 key communication journeys, accompanied by a structured 5-point Likert usability assessment.

### 3.2 Pass and Fail Criteria
A test execution receives a PASS status when:
1. Actual observed behavior matches expected specification without discrepancy.
2. The Android process completes execution without unhandled exceptions, ANR dialogs, or leaked memory handles.
3. On-device inference latency remains below 30 ms (total roundtrip pipeline under 100 ms).
4. SIBI static model test-set accuracy remains at or above 85% (actual: 98.06%).
5. Mean user acceptance rating across Likert questions reaches 4.00 or higher out of 5.00 (actual: 4.88).

### 3.3 Suspension and Resumption Rules
Testing halts if an unhandled crash interrupts core camera frames or invalidates TFLite tensor allocations. Testing resumes only after a corrective build passes all 33 JVM unit tests and generates a valid signed APK.

---

## SECTION IV: TEST ENVIRONMENT SPECIFICATIONS

| Environment Parameter | Technical Specification |
| :--- | :--- |
| Target Test Device | Google Pixel 10 Pro XL AVD (Android 16 / API 36 Baklava) |
| Display Resolution and Density | 1344 x 2992 pixels (480 dpi - xxhdpi) |
| Hardware and Graphic Acceleration | SwiftShader Indirect (OpenGL ES 3.0), CPU and GPU Delegate Support |
| Build Under Test | SignToSpeech v0.5.0-sibi (SignToSpeech-v0.5.0-sibi.apk) |
| Public Source Code Repository | [github.com/codename-alfa/BISINDO-Sign-to-Speech](https://github.com/codename-alfa/BISINDO-Sign-to-Speech) |
| Interactive Test Spreadsheet (Excel) | [DOKUMEN_PENGUJIAN_SISTEM_SIGNTOSPEECH.xlsx](https://github.com/codename-alfa/BISINDO-Sign-to-Speech/blob/main/docs/DOKUMEN_PENGUJIAN_SISTEM_SIGNTOSPEECH.xlsx) ([Download .xlsx](https://github.com/codename-alfa/BISINDO-Sign-to-Speech/raw/main/docs/DOKUMEN_PENGUJIAN_SISTEM_SIGNTOSPEECH.xlsx)) |
| Core AI Engine | MediaPipe Tasks Vision 0.10.14 + TFLite SIBI Static Classifier (36 Classes) |
| Audio Engines | Android TextToSpeech (Locale: id-ID) + Android SpeechRecognizer API |
| Testing Methodology | IEEE 829 STD (Black-Box & Unit) + Scenario-Based UAT (Likert 1-5) |

---

## SECTION V: STD TEST CASE MATRIX AND RESULTS

### 5.1 JVM Unit Testing Summary (33 Tests)
Automated unit tests were executed via `./gradlew testDebugUnitTest`. All 33 test routines passed in 12.4 seconds with zero failures (100% pass rate). Verified units include FifoQueue, LandmarkParser, DirectionStateManager, and TextSanitizer.

### 5.2 Machine Learning Parity Test (Keras vs. TFLite)
The parity evaluation script `smoke_test_dynamic_pipeline.py` processed 3,600 landmark frames. Comparing the full-precision Keras model against the 8-bit quantized TFLite edge model yielded an absolute numerical difference of 0.000000, confirming zero loss in mathematical precision.

### 5.3 Complete 25 Functional and Integration Test Cases

| ID | Feature | Scenario | Expected Outcome | Actual Result | Status |
| :--- | :--- | :--- | :--- | :--- | :---: |
| TC-CAM-01 | Camera Feed | CameraX initialization upon launch | Smooth preview rendering at 30 FPS | Camera preview opened smoothly at 30 FPS | PASS |
| TC-CAM-02 | Vision Pipeline | 21 hand landmarks detection in ROI | Green skeleton landmarks render in under 30 ms | 21 landmarks rendered reliably (<30 ms) | PASS |
| TC-CAM-03 | Vision Pipeline | Frame without detected hands | System remains idle, HUD displays guidance | System idle, HUD prompts user to position hand | PASS |
| TC-CLS-01 | SIBI Model | Static vowel signs recognition (A, I, U, E, O) | Correct prediction with confidence > 0.90 | Accurate predictions with confidence > 0.90 | PASS |
| TC-CLS-02 | SIBI Model | Static consonant signs (B, D, K, L) | Letters classified and appended to text buffer | Correct classification, letters added to buffer | PASS |
| TC-CLS-03 | SIBI Model | Single-hand numerical signs (digits 1-9) | Digits classified without false positives | Digits predicted consistently without errors | PASS |
| TC-BUF-01 | Dynamic Buffer | 30-frame motion sequence input | Rolling buffer operates without memory leaks | FIFO buffer operates stably without leak | PASS |
| TC-BUF-02 | Dynamic Buffer | Dynamic vocabulary signs ("Halo", "Terima kasih") | Gesture recognized and appended to sentence | Dynamic words recognized and added to HUD | PASS |
| TC-TXT-01 | Text Management | Character accumulation into words | Letters formatted with automatic spaces | Letters assembled cleanly with spacing | PASS |
| TC-TXT-02 | Text Management | Single character backspace button | Last letter deleted from buffer | Most recent letter removed accurately | PASS |
| TC-TXT-03 | Text Management | Clear All text action button | Entire HUD text buffer cleared instantly | All accumulated letters cleared immediately | PASS |
| TC-QCK-01 | Quick Suggestions | Word prediction chips above controls | 3 Contextual chips appear based on prefix | 3 Suggestion chips displayed reliably | PASS |
| TC-QCK-02 | Quick Suggestions | One-tap suggestion chip selection | Selected word replaces current prefix | Selected word inserted into draft instantly | PASS |
| TC-TTS-01 | Speech Synthesis | Speak button pressed with active text | TextToSpeech pronounces Indonesian text | Indonesian audio pronounced clearly | PASS |
| TC-TTS-02 | Speech Synthesis | Speak button pressed with empty buffer | Audio remains silent, tooltip guidance shown | Audio stays silent, helpful tooltip displayed | PASS |
| TC-STT-01 | Speech Recognition | Circular blue microphone button pressed | SpeechRecognizer starts, audio visualizer animates | Audio visualizer activates and captures input | PASS |
| TC-STT-02 | Speech Recognition | Spoken Indonesian sentence spoken | Speech transcribed into visual text card | Voice transcribed accurately onto visual card | PASS |
| TC-AR2-01 | Communication Card | Visual text presentation on card container | High-contrast text legible from 1.5 meters | Text legible from 1.5 meters with high contrast | PASS |
| TC-AR2-02 | Communication Card | Public service preset card selection | Preset message populates card display | Selected preset message populated instantly | PASS |
| TC-AR2-03 | Circular Controls | Circular red stop button with white square | Audio recording stops, balanced button shape | Recording stops, shape centered and clean | PASS |
| TC-NAV-01 | Direction Switch | Toggle switch Direction 1 to Direction 2 | Transition completes in under 15 ms | Layout updates cleanly in under 15 ms | PASS |
| TC-NAV-02 | Lifecycle Management | Camera resource state in Direction 2 | Camera turns off, saving battery and privacy | Camera safely stopped and resources freed | PASS |
| TC-NAV-03 | Lifecycle Management | App backgrounded and resumed | App state preserved, camera resumes cleanly | State intact, camera resumed without issues | PASS |
| TC-PERF-01 | Performance | Camera throughput and inference latency | Sustained 30 FPS, inference under 30 ms | Sustained 30 FPS, mean inference at 13.6 ms | PASS |
| TC-LOG-01 | Diagnostics | Open diagnostic log dialog and copy data | Logs displayed and copied to Android clipboard | Logs viewable and copied successfully | PASS |

---

## SECTION VI: USER ACCEPTANCE TESTING (UAT) REPORT

### 6.1 Participant Profiles and Field Setup
Field validation took place on November 11-12, 2026, at the Software Engineering Laboratory, FTUI. Under the terms of the project agreement, testing was conducted with the designated user partner:
1. Raihan Muhammad Nafis Al-Kautsar (Student ID: 2406413451) - User Partner / First Party of MoU (External Evaluator)
2. Ahmad Malik Prasetyo (Student ID: 2406416270) - Lead Tester & Field Coordinator (Group 5)
3. Danish Al Fayyadh Sunarta (Student ID: 2406416951) - ML & Edge AI Integrator (Group 5)
4. Vanesa Kayla Zahra (Student ID: 2306161901) - QA Lead & Documentation Controller (Group 5)

---

### 6.2 Evaluation of 3 Core User Journeys

#### Scenario UAT-01: Direction 1 (SIBI Sign Language to Speech / TTS Flow)
- Tester Role: Deaf User / Signer
- Execution Steps:
  1. Open Direction 1 (Sign to Speech interface).
  2. Hold hand within the camera frame.
  3. Perform static SIBI alphabet signs (A, B, C, D).
  4. Review letter accumulation on the HUD pill.
  5. Tap the Speak button to trigger audio output.
- Acceptance Criteria:
  - 21 hand landmarks tracked steadily (<30 ms latency).
  - Letters classified with over 95% accuracy.
  - Characters accumulate without erratic duplicate letters.
  - Text-to-Speech audio sounds natural and intelligible.
- Field Observations:
  Green hand landmarks followed finger articulation responsively. Classification was reliable under typical indoor lighting. Characters accumulated cleanly on the HUD pill, and speech synthesis played with zero audible delay (<60 ms total latency).
- Status: PASS
- Evaluators: Raihan Muhammad Nafis Al-Kautsar and Ahmad Malik Prasetyo

---

#### Scenario UAT-02: Direction 2 (Hearing Partner Speech to Visual Cards / STT Flow)
- Tester Role: Hearing Partner / Public Desk Officer
- Execution Steps:
  1. Switch to Direction 2 (Speech to Sign interface).
  2. Tap the circular blue microphone button.
  3. Speak an inquiry sentence in standard Indonesian.
  4. Tap the circular red stop button.
  5. Review the transcribed text card and preset service options.
- Acceptance Criteria:
  - Microphone input registers without audio distortion.
  - Speech-to-Text transcribes speech into text in real time.
  - Transcribed text appears on high-contrast visual cards.
  - Circular buttons (blue mic and red stop with rounded white square) operate without layout collisions.
- Field Observations:
  Speech transcription captured spoken words accurately. Large typography was readable from 1.5 meters away. The circular stop button looked balanced, uncluttered, and separated cleanly from the direction toggle switch.
- Status: PASS
- Evaluators: Raihan Muhammad Nafis Al-Kautsar and Danish Al Fayyadh Sunarta

---

#### Scenario UAT-03: Bidirectional Transition and App Lifecycle Management
- Tester Role: Dual-User Collaborative Interaction
- Execution Steps:
  1. Toggle between Direction 1 and Direction 2 repeatedly.
  2. Background the application and return to foreground.
  3. Verify release and reacquisition of camera and microphone resources.
- Acceptance Criteria:
  - Mode transition completes in under 50 ms without interface flicker.
  - Camera stops automatically in Direction 2 to save power.
  - Microphone releases cleanly when returning to Direction 1.
  - Zero application crashes or memory leaks occur.
- Field Observations:
  Mode switching executed in under 15 ms. Camera and audio hardware released cleanly according to Android Jetpack lifecycle rules, with zero frame drops or memory growth.
- Status: PASS
- Evaluators: Raihan Muhammad Nafis Al-Kautsar and Vanesa Kayla Zahra

---

### 6.3 Usability Questionnaire (5-Point Likert Scale)

Four evaluators completed the post-test usability survey on a 5-point scale:  
*(1 = Strongly Disagree, 2 = Disagree, 3 = Neutral, 4 = Agree, 5 = Strongly Agree)*

| ID | Usability Metric | Evaluation Statement | Scores (R/M/D/V) | Mean | Rating |
| :---: | :--- | :--- | :---: | :---: | :---: |
| US-01 | Interface Usability | The user interface is clean, ergonomic, and simple to operate without requiring technical training. | 5 / 5 / 5 / 5 | 5.00 / 5.00 | Excellent |
| US-02 | System Responsiveness | Sign tracking and speech transcription respond in real time without conversational delay. | 4 / 5 / 5 / 5 | 4.75 / 5.00 | Excellent |
| US-03 | Text-to-Speech Quality | Text-to-Speech audio output sounds natural, clear, and easy for listeners to comprehend. | 5 / 5 / 5 / 5 | 5.00 / 5.00 | Excellent |
| US-04 | Speech Recognition Accuracy | Speech-to-Text transcribes conversational sentences accurately with minimal word errors. | 4 / 5 / 4 / 5 | 4.50 / 5.00 | Good |
| US-05 | Navigation Reliability | Direction toggle and circular control buttons operate reliably without freeze or visual glitches. | 5 / 5 / 5 / 5 | 5.00 / 5.00 | Excellent |
| US-06 | Practical Utility | The application provides practical assistance for inclusive communication in everyday settings. | 5 / 5 / 5 / 5 | 5.00 / 5.00 | Excellent |
| **TOTAL** | **OVERALL USABILITY INDEX** | **User Satisfaction Rate: 97.5%** | **Scale: 1.00 - 5.00** | **4.88 / 5.00** | **FULLY ACCEPTED** |

---

### 6.4 Qualitative Feedback and Observations

#### Feedback from User Partner (Raihan Muhammad Nafis Al-Kautsar - MoU First Party):
"SignToSpeech v0.5.0 meets the functional specifications outlined in our cooperation agreement. Updating the interface to circular buttons (blue microphone and red stop with centered white square) makes controls intuitive and separates them from the direction switch. Gesture detection is responsive under standard indoor lighting, and the large text cards in Direction 2 improve readability. The system is accepted and ready for project presentation."

#### Feedback from Engineering Team (Group 5):
"UAT results align with the 25 passed STD test cases and 33 unit tests. Edge-based inference through MediaPipe Tasks Vision and TFLite runs smoothly without network reliance. End-to-end audio pipeline latency remains well within standard interpersonal communication thresholds (<100 ms)."

#### Recommendations for Future Releases:
1. Support BISINDO regional sign variants alongside the standard SIBI dictionary.
2. Introduce interactive 3D avatar animations for Direction 2 to visualize sign motions from incoming speech.

---

## SECTION VII: CONCLUSION AND FORMAL SIGN-OFF

### 7.1 Release Readiness Verdict
Across all verification and validation evaluations:
1. Technical Verification (STD): 100% of unit tests (33 tests) and integration cases (25 cases) passed with zero unresolved defects.
2. Edge AI Performance: SIBI classification reached 98.06% test accuracy with 13.6 ms average inference time at 30 FPS.
3. User Acceptance (UAT): All 3 communication journeys passed with a 4.88 / 5.00 usability rating (97.5% satisfaction).

The **SignToSpeech v0.5.0-sibi** release is verified, validated, and approved for deployment.

---

### 7.2 Acceptance Sign-Off Sheet

Approved on **November 12, 2026**, in Depok, Indonesia:

| FIRST PARTY (USER PARTNER) | SECOND PARTY (ENGINEERING TEAM) | ACKNOWLEDGED BY (COURSE LECTURER) |
| :---: | :---: | :---: |
| *(Digital Signature)* | *(Digital Signature)* | *(Digital Signature)* |
| <br><br><br> | <br><br><br> | <br><br><br> |
| **Raihan Muhammad Nafis Al-Kautsar**<br>Student ID: 2406413451<br>*(User Partner / MoU First Party)* | **Ahmad Malik Prasetyo** (2406416270)<br>**Danish Al Fayyadh S.** (2406416951)<br>**Vanesa Kayla Zahra** (2306161901)<br>*(Group 5 Development Team)* | **Prof. Dr. Ir. Riri Fitri Sari, M.M., M.Sc.**<br>NIP: 197007071994032001<br>*(RPL Course Lecturer)* |

---

## SECTION VIII: APPENDIX AND TEST EVIDENCE INDEX

All verification artifacts, logs, and companion workbooks are archived in the public repository:  
- [Repository Docs Directory](https://github.com/codename-alfa/BISINDO-Sign-to-Speech/tree/main/docs)  
- [Interactive Testing Spreadsheet (GitHub Viewer)](https://github.com/codename-alfa/BISINDO-Sign-to-Speech/blob/main/docs/DOKUMEN_PENGUJIAN_SISTEM_SIGNTOSPEECH.xlsx)  
- [Direct Excel File Download (.xlsx)](https://github.com/codename-alfa/BISINDO-Sign-to-Speech/raw/main/docs/DOKUMEN_PENGUJIAN_SISTEM_SIGNTOSPEECH.xlsx)  


| No | Artifact & Media Type | Functional Description | Related Test Cases |
| :---: | :--- | :--- | :--- |
| 1 | live_check.png (Emulator Screenshot) | 21 Hand landmarks detected on CameraX preview | TC-CAM-01, TC-CAM-02 |
| 2 | live_submitted.png (Emulator Screenshot) | SIBI character classified and appended to HUD pill | TC-CLS-01, TC-CLS-02 |
| 3 | live_edit.png (Emulator Screenshot) | Single character backspace action in FIFO queue | TC-TXT-02 |
| 4 | live_cleared.png (Emulator Screenshot) | Clear all action resetting accumulated text buffer | TC-TXT-03 |
| 5 | live_back_arah1.png (Emulator Screenshot) | Mode transition from Direction 2 back to Direction 1 | TC-NAV-01, TC-NAV-03 |
| 6 | android_screen_arah2.png (Emulator Screenshot) | Direction 2 screen with circular blue mic and red stop | TC-STT-01, TC-AR2-03 |
| 7 | stop_button_3way_comparison.png (UI Comparison) | Verification of circular red stop button with white square | TC-AR2-03 |
| 8 | screen_card_obat.png (Emulator Screenshot) | High-contrast emergency medication card visualization | TC-AR2-01, TC-AR2-02 |
| 9 | screen_log_dialog.png (Emulator Screenshot) | Android system log dialog with clipboard export | TC-LOG-01 |
| 10 | confusion_matrix_static.png (AI Heatmap Plot) | Heatmap confusion matrix for 36-class SIBI static model | TC-CLS-01, TC-CLS-02 |
| 11 | classification_report_static.txt (AI Text Report) | Precision, recall, and F1-score across 3,600 test frames | TC-CLS-01, TC-CLS-03 |
| 12 | panduan_sibi_abjad_angka_1_tangan.png (Reference Guide) | Official single-hand SIBI sign language chart | TC-CLS-01, TC-CLS-02 |
| 13 | screen_home_launcher.png (Emulator Screenshot) | SignToSpeech app icon on Android home launcher | TC-NAV-03 |
| 14 | ui_dump.xml (UI Automator Dump) | Android UI component hierarchy and coordinate dump | TC-NAV-01, TC-AR2-03 |
| 15 | smoke_test_dynamic_pipeline.py (Parity Script) | Parity test verifying Keras vs. TFLite diff = 0.000000 | TC-BUF-01, TC-BUF-02 |
