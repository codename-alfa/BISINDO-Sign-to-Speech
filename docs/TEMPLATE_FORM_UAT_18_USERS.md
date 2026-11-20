# SignToSpeech v0.6.0 User Acceptance Testing (UAT) Field Form and Questionnaire

Document ID: `STD-UAT-STS-2026-V0.6-FORM`
Status: `PENDING_UAT_RUN`
Target Software Release: `SignToSpeech v0.6.0` (Android APK, Offline Edge AI)
Standards Alignment: ISO 9241-11:2018 (Usability), Brooke System Usability Scale (SUS), and ISO/IEC 25010:2023

## 1. Participant Cohort Structure (22 Total Evaluators)

Field evaluation is structured into three separate respondent cohorts to prevent role bias between client validation, developer internal reviews, and uncoached external users.

| Group | Role and Cohort Description | Count | Session Target Date | Evaluation Scope |
| :--- | :--- | :---: | :--- | :--- |
| Group 1 | First Party Client (Raihan Muhammad Nafis Al-Kautsar, NPM 2406413451) | 1 | Pre-release UAT Window (Nov-Dec 2026) | MoU Article 1 & 2 acceptance, all 5 core user journeys, final sign-off decision |
| Group 2 | Second Party Internal Engineering Team (Ahmad, Danish, Vanesa) | 3 | Pre-release Internal Audit | Edge-case regression, realistic defect surfacing (target realism benchmark: 83-87% / 4.15-4.35 out of 5.00) |
| Group 3 | External Respondents (R01-R18 across Deaf/HoH users, JBI interpreters, hearing service staff) | 18 | Field / Campus UAT Window | Uncoached first-time usability, ISO 9241-11 task efficiency, Likert & SUS scoring |

Internal team scores (Group 2) serve only as an engineering calibration check against realistic defect pressure and are excluded from external end-user acceptance averages (Group 3) and client sign-off (Group 1).

## 2. Moderator Protocol and UAT Execution Script

1. Prepare a clean Android 8.0+ smartphone with `SignToSpeech v0.6.0` installed, airplane mode verified for offline trials, and the printed SIBI single-hand reference chart nearby for new signers.
2. Brief the participant for 2 minutes on safety and privacy (100% local camera and microphone processing, zero cloud video upload, option to withdraw at any time). Do not coach finger angles during timed runs.
3. Have the participant execute the five standardized UAT tasks below while the observer records pass/fail completion, elapsed seconds, and error recoveries.
4. Collect ratings immediately after task execution while interaction memory is fresh.

## 3. ISO 9241-11 Task Execution Log (Complete One Row per Participant)

Tasks evaluated:
- **UAT-01**: Spell the word `"HALO"` using Direction 1 Letter Mode (SIBI) and verify voice playback (`TTS`).
- **UAT-02**: Switch to Direction 1 Word Mode (BISINDO), perform `"Terima kasih"`, then hold a relaxed rest pose (`_idle`) for 3 seconds to verify zero phantom speech triggers.
- **UAT-03**: Switch to Direction 2 (`SPEECH -> CARD`), test voice dictation (or inline keyboard fallback after `SecurityException`), and trigger the `"Kondisi darurat IGD"` preset card.
- **UAT-04**: Enable Airplane Mode mid-session and repeat a static sign, keyboard card entry, and TTS playback without network dependency.
- **UAT-05**: Trigger orientation change / background-to-foreground resume and verify committed transcript, mute toggle, and current card remain intact.

| Participant ID | Group (G1/G2/G3) | Role (Deaf / JBI / Staff / Internal / Client) | Device Model & Android Ver | UAT-01 (Pass/Fail, sec) | UAT-02 (Pass/Fail, sec) | UAT-03 (Pass/Fail, sec) | UAT-04 (Pass/Fail, sec) | UAT-05 (Pass/Fail, sec) | Observer Notes |
| :--- | :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| `C01` | G1 | Client (Raihan) | | | | | | | |
| `T01` | G2 | Internal (Ahmad) | | | | | | | |
| `T02` | G2 | Internal (Danish) | | | | | | | |
| `T03` | G2 | Internal (Vanesa) | | | | | | | |
| `R01` | G3 | | | | | | | | |
| `R02` | G3 | | | | | | | | |
| `R03` | G3 | | | | | | | | |
| `R04` | G3 | | | | | | | | |
| `R05` | G3 | | | | | | | | |
| `R06` | G3 | | | | | | | | |
| `R07` | G3 | | | | | | | | |
| `R08` | G3 | | | | | | | | |
| `R09` | G3 | | | | | | | | |
| `R10` | G3 | | | | | | | | |
| `R11` | G3 | | | | | | | | |
| `R12` | G3 | | | | | | | | |
| `R13` | G3 | | | | | | | | |
| `R14` | G3 | | | | | | | | |
| `R15` | G3 | | | | | | | | |
| `R16` | G3 | | | | | | | | |
| `R17` | G3 | | | | | | | | |
| `R18` | G3 | | | | | | | | |

## 4. Part A: Domain-Specific 5-Point Likert Usability Questionnaire

Scale: `1` = Strongly Disagree, `2` = Disagree, `3` = Neutral, `4` = Agree, `5` = Strongly Agree.

| Item ID | Metric Dimension | Questionnaire Statement |
| :--- | :--- | :--- |
| `Q1` | Ease of Communication | The bidirectional app helps Deaf and hearing speakers communicate without needing a third-party interpreter. |
| `Q2` | Detection Responsiveness | Sign language predictions in Letter Mode (SIBI) and Word Mode (BISINDO) respond quickly and remain stable. |
| `Q3` | Audio and Visual Clarity | Indonesian speech output (`TTS`) and high-contrast visual cards in Direction 2 are easy to hear and read in service counters. |
| `Q4` | Interface Learnability | Navigation toggles, quick presets, correction suggestions, and backspace/clear buttons are easy to understand on first use. |
| `Q5` | Offline Readiness | On-device translation and emergency quick presets work reliably even without mobile internet access. |
| `Q6` | Adoption Confidence | I feel confident using SignToSpeech in daily public-service scenarios such as clinics, campus counters, or pharmacies. |

| Participant ID | Group | Q1 (1-5) | Q2 (1-5) | Q3 (1-5) | Q4 (1-5) | Q5 (1-5) | Q6 (1-5) | Mean Score |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `C01` | G1 | | | | | | | |
| `T01` | G2 | | | | | | | |
| `T02` | G2 | | | | | | | |
| `T03` | G2 | | | | | | | |
| `R01` | G3 | | | | | | | |
| `R02` | G3 | | | | | | | |
| `R03` | G3 | | | | | | | |
| `R04` | G3 | | | | | | | |
| `R05` | G3 | | | | | | | |
| `R06` | G3 | | | | | | | |
| `R07` | G3 | | | | | | | |
| `R08` | G3 | | | | | | | |
| `R09` | G3 | | | | | | | |
| `R10` | G3 | | | | | | | |
| `R11` | G3 | | | | | | | |
| `R12` | G3 | | | | | | | |
| `R13` | G3 | | | | | | | |
| `R14` | G3 | | | | | | | |
| `R15` | G3 | | | | | | | |
| `R16` | G3 | | | | | | | |
| `R17` | G3 | | | | | | | |
| `R18` | G3 | | | | | | | |

## 5. Part B: Standardized System Usability Scale (Brooke SUS, 10 Items)

Rate each statement from `1` (Strongly Disagree) to `5` (Strongly Agree). Scoring follows Brooke (1996): odd items contribute `(score - 1)`, even items contribute `(5 - score)`, and the sum is multiplied by `2.5` to produce a 0-100 SUS score. Target acceptance threshold is `>= 68.0` (above average) and `>= 75.0` for release readiness.

1. `SUS1 (+)`: I think that I would like to use this system frequently.
2. `SUS2 (-)`: I found the system unnecessarily complex.
3. `SUS3 (+)`: I thought the system was easy to use.
4. `SUS4 (-)`: I think that I would need the support of a technical person to be able to use this system.
5. `SUS5 (+)`: I found the various functions in this system were well integrated.
6. `SUS6 (-)`: I thought there was too much inconsistency in this system.
7. `SUS7 (+)`: I would imagine that most people would learn to use this system very quickly.
8. `SUS8 (-)`: I found the system very cumbersome to use.
9. `SUS9 (+)`: I felt very confident using the system.
10. `SUS10 (-)`: I needed to learn a lot of things before I could get going with this system.

| Participant ID | Group | S1 | S2 | S3 | S4 | S5 | S6 | S7 | S8 | S9 | S10 | SUS Total (0-100) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `C01` | G1 | | | | | | | | | | | |
| `T01` | G2 | | | | | | | | | | | |
| `T02` | G2 | | | | | | | | | | | |
| `T03` | G2 | | | | | | | | | | | |
| `R01` | G3 | | | | | | | | | | | |
| `R02` | G3 | | | | | | | | | | | |
| `R03` | G3 | | | | | | | | | | | |
| `R04` | G3 | | | | | | | | | | | |
| `R05` | G3 | | | | | | | | | | | |
| `R06` | G3 | | | | | | | | | | | |
| `R07` | G3 | | | | | | | | | | | |
| `R08` | G3 | | | | | | | | | | | |
| `R09` | G3 | | | | | | | | | | | |
| `R10` | G3 | | | | | | | | | | | |
| `R11` | G3 | | | | | | | | | | | |
| `R12` | G3 | | | | | | | | | | | |
| `R13` | G3 | | | | | | | | | | | |
| `R14` | G3 | | | | | | | | | | | |
| `R15` | G3 | | | | | | | | | | | |
| `R16` | G3 | | | | | | | | | | | |
| `R17` | G3 | | | | | | | | | | | |
| `R18` | G3 | | | | | | | | | | | |

## 6. Qualitative Feedback and Sign-Off Verification

- What interaction worked well during your session?
- Which gesture, voice input, or screen element caused hesitation or errors?
- Any requested additions for post-release updates?

Transfer recorded values directly into the live formula cells on sheet `UAT Package (3 Groups)` of `DOKUMEN_PENGUJIAN_SISTEM_SIGNTOSPEECH.xlsx` after session completion.
