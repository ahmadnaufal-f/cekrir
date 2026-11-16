# Smart Package Delivery Checker

> Imported from [Notion](https://app.notion.com/p/4173556fda92812883d3d9df0b538ea9) on 2026-11-16. Source last edited: 2026-11-15T14:31:31.979Z.
>
> This is a planning snapshot. Decision labels and historical statements are preserved from the source. See the [repository README](../README.md) and engineering documentation for current implementation status.

**Status:** Initial PRD for collaborative review

**Team:** Two people

**Context:** Internal IoT hackathon organised by the user's manager

**Planning stage:** Product definition. Frontend and ESP32 direction are recorded. Backend preferences and remaining integration decisions need validation. Implementation has not started in this planning session.

**Confirmed hackathon window:** Starts 2026-11-13. The demonstration must be ready by 2026-11-28. The user describes this as a two week hackathon. User facing dates use Asia/Jakarta. Both teammates are available full time on weekends and at night on weekdays. They use Codex and can delegate coding tasks during weekday working hours. Exact daily hours are not fixed.

> Decision labels
>
> **Confirmed** means explicitly requested in the initial brief or agreed during subsequent planning. **Suggested** means a proposal for discussion. **Undecided** means a choice still needs to be made. **Assumption** means an unverified condition. A confirmed workflow requirement does not confirm a particular implementation.

## 1. Product overview

**Confirmed:** Build a Smart Package Delivery Checker that connects a physical package scan to a delivery photo, shipping information, and a push notification to the intended recipient. Prioritise a working demonstration of the complete flow that two people can build within the hackathon timeframe.

**Confirmed:** The first demonstration represents a household. The existing BARDI Indoor PTZ camera running firmware 5.7.4 is the preferred hardware candidate, pending successful testing.

**Confirmed:** The hackathon targets a household user with an ESP32 equipped with a camera or a barcode scanner module, plus BARDI CCTV. Users register products in the app, may register multiple CCTV cameras, and may use only one ESP32. ESP32 source code and setup guidance are part of the experience. Push notifications are mandatory.

**Confirmed:** Admins sign up and create member accounts directly. Members do not need to complete self registration. Accounts have an admin or member role. Admins register devices and manage member creation. Delivery notifications go to the associated household's admin and members.

**Confirmed usability goal:** Member registration must be as simple as possible because members may include household helpers (ART) and parents who are less comfortable with technology. The admin handles account creation and can assist with each member's initial app setup on their phone. Exact authentication, first sign in steps, and notification permission setup remain undecided.

**Undecided:** Admin signup mechanics, member first sign in and device setup, role assignment, number of admins and members, phones per account, exact daily development hours, total budget, exact courier coverage and API access, camera timeout and retry policy, exact ESP32 hardware, and remaining technology integrations. Stated stack choices and ownership are recorded in Repository, stack, and initial ownership.

## 2. Problem statement

**Suggested problem framing:** People receiving packages need a timely way to know that a delivery has arrived, identify the shipment, and see a photo of the delivery. At a shared receiving point, someone may otherwise need to manually identify and notify the recipient.

**Assumption:** Delayed notifications and manual coordination are meaningful problems for the intended users. The household setting is confirmed. The current receiving process and specific pain points need validation.

**Boundary:** A scan and photo record a delivery event. Whether a package was handed over, left safely, or later collected requires a separate definition and is undecided.

## 3. Objectives and success criteria

| Objective                                             | Status    | Evidence of success                                                                                                                                                                                     |
| ----------------------------------------------------- | --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Demonstrate the complete scan to notification journey | Confirmed | A physical scan leads to a delivery photo, a shipping API result, and a household push notification. Tapping the notification opens the relevant delivery page with its photo and package details       |
| Keep the project achievable by two people             | Confirmed | Demonstration is ready by November 28, 2026, for the hackathon starting November 13, 2026. Scope must fit full weekend availability and weekday nights, with Codex assisted coding during working hours |
| Use an affordable, programmable CCTV camera           | Confirmed | Camera is available in Indonesia, supports programmatic image capture, and preferably costs Rp300,000 to Rp1,000,000                                                                                    |
| Make the demonstration repeatable                     | Suggested | Repeat the journey successfully with several prepared packages                                                                                                                                          |
| Establish measurable performance targets              | Undecided | Agree notification latency and demonstration reliability targets after understanding constraints                                                                                                        |

**Confirmed:** Tapping the delivery notification navigates to the relevant delivery page, which displays the captured photo alongside package details from the resi lookup. An inline photo in the notification is not required for the MVP.

**Undecided:** Exact notification text, package detail fields, and whether any simulated integrations are acceptable under hackathon rules. A simulation would need to be disclosed and would not establish a live integration.

## 4. Target users

| User                            | Status                                                     | Need                                                                                                                                                                                                     |
| ------------------------------- | ---------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Courier                         | Confirmed actor in the proposed workflow                   | Scan a package at the receiving point                                                                                                                                                                    |
| Admin                           | Confirmed household role                                   | Sign up, register devices, register members, follow setup guides, and receive delivery push notifications                                                                                                |
| Member                          | Confirmed household role                                   | Use an account created by the admin and receive household delivery push notifications. May be a household helper or a parent with limited confidence using technology. Self registration is not required |
| Intended package recipient      | Package addressee may be an admin or a member              | Notification routing uses the household device and membership association. All associated admins and members receive the alert                                                                           |
| Receptionist or receiving staff | Earlier suggestion, outside the current household scenario | Retained for context. No receiving staff role is currently required                                                                                                                                      |
| Demo operator                   | Suggested                                                  | See whether a scan succeeded and recover from an integration failure                                                                                                                                     |

**Confirmed:** The first demonstration serves a household.

**Confirmed:** The admin and registered members receive delivery push notifications for the associated household. Matching a package label to one individual is not required to determine the notification audience.

**Confirmed:** The admin creates member accounts directly. Invitation followed by member self registration is outside the chosen MVP registration journey.

**Undecided:** How a member first signs in and connects their phone, required account fields, how admin roles are assigned, whether more than one admin is allowed, account and membership limits, and support for multiple phones per account.

## 5. Proposed user journey

### Setup journey

**Confirmed target user:** A household user who owns an ESP32 equipped with either a camera or a barcode scanner module, and a BARDI CCTV camera.

1. An admin signs up before using the app. Accounts have an admin or member role. Admin signup and role assignment details remain undecided.
2. The admin registers household devices. Multiple CCTV cameras are allowed, while only one ESP32 can be used in the setup. The admin designates one registered CCTV as the delivery camera during setup.
3. The admin creates member accounts directly and assists with initial app setup on each member's phone. Members do not complete a self registration or invitation acceptance flow. Required member information, authentication, and exact setup steps remain undecided.
4. The app provides the ESP32 firmware source code and setup guide. For the MVP, the admin sets the WiFi credentials and backend address in the firmware configuration, then builds and flashes it. Configuration through the Android app is deferred.
5. The app provides a BARDI CCTV setup guide. The user leading this project will first test their existing CCTV and then supply the validated guide.
6. After setup, a delivery scan starts the delivery flow. The household's admin and registered members receive push notifications.

**Confirmed:** The ESP32 camera uploads barcode images for Python backend decoding. WiFi credentials and backend address are configured before flashing; Android based WiFi provisioning is outside the MVP.

**Undecided:** User authentication, device identity and household linking, exact ESP32 board and camera, firmware framework, and flashing tools. Device capture quality still needs validation.

### Delivery journey

The following sequence retains the **requested initial delivery workflow**, updated for ESP32 input and admin and member notification recipients. Household membership determines the notification audience. The admin selects one delivery camera during setup.

1. A courier arrives at the delivery point with a package.
2. The courier scans the package barcode through the ESP32 input, using either a camera or a barcode scanner module. The MVP input option is still undecided.
3. The ESP32 sends the scan data to the backend through a connection method that is still undecided.
4. The backend captures a photo from the single delivery CCTV selected by the admin during setup. Other registered cameras are not captured for this scan. Extracting a frame from RTSP remains an acceptable approach, with the final integration pending validation.
5. The backend queries a shipping tracking API using the shipment identifier and any other required inputs.
6. The system associates the scan with its registered ESP32 and household setup, then determines the associated admin and registered members.
7. The system sends the household admin and members delivery push notifications. Matching the addressee name is not needed to determine this audience.
8. Tapping a notification opens the corresponding delivery page in the app, showing the captured photo alongside package details retrieved from the resi lookup.

**Assumptions to validate:** The selected barcode contains a usable tracking number, the courier can find the correct barcode, and the package remains in the camera's view during capture. Notification destinations must be associated with admin accounts or admin created member accounts and household membership. The tracking API must not be assumed to provide an app identity or notification destination.

**Suggested exception journey:** Show a clear failure or unresolved state for invalid scans, unavailable tracking information, failed image capture, unmatched recipients, and failed notifications. Exact behaviour remains open.

## 6. Functional requirements

| ID   | Requirement                                                                                                       | Status                                                                                                                           | Initial acceptance criterion                                                                                                                                                                                                                                                                                                                                          |
| ---- | ----------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| FR1  | Capture a package barcode image on ESP32 and decode it in the Python backend                                      | Confirmed MVP processing choice                                                                                                  | A proximity triggered ESP32 camera capture is uploaded to the Python backend, which decodes the barcode and returns the result. Local ESP32 decoding and dedicated scanner modules are outside the MVP. Exact camera board and decoder library remain undecided                                                                                                       |
| FR2  | Use the shipping tracking number, or resi, from the scan                                                          | Confirmed intent, extraction undecided                                                                                           | Selected label formats produce the expected tracking number                                                                                                                                                                                                                                                                                                           |
| FR3  | Attempt image capture after a scan and handle camera failure                                                      | Confirmed                                                                                                                        | Capture the selected CCTV's current view for the delivery event. If capture fails, continue delivery notification and show Photo unavailable on its delivery page. Historical recordings and playback are not required. Timeout and retry policy remain undecided                                                                                                     |
| FR4  | Attempt shipping tracking lookup and handle lookup failure                                                        | Confirmed                                                                                                                        | Retrieve available package details for a supported resi. If lookup fails, still send the delivery notification using the scanned resi and any available photo, and show Tracking details unavailable on the delivery page. Timeout and retry policy remain undecided                                                                                                  |
| FR5  | Route a device's delivery event to its household admin and registered members                                     | Confirmed                                                                                                                        | Notification recipients are selected from device registration and household membership, rather than matching the package label to an individual                                                                                                                                                                                                                       |
| FR6  | Send delivery push notifications to the admin and members despite CCTV or tracking lookup failure                 | Confirmed and mandatory                                                                                                          | Notify the associated household using the scanned resi and any available photo and tracking details. CCTV or tracking failure must not block the notification, including when both fail. Tapping it opens the corresponding delivery page with explicit unavailable states                                                                                            |
| FR7  | Keep the scan, tracking result, photo, and recipient associated                                                   | Suggested                                                                                                                        | Two successive scans do not mix up their information                                                                                                                                                                                                                                                                                                                  |
| FR8  | Provide visual and audible scan success feedback immediately after successful barcode decoding                    | Confirmed hardware and success condition                                                                                         | A successfully decoded barcode triggers the light and buzzer without waiting for CCTV capture, tracking lookup, or push notification completion. A CCTV failure must not prevent or reverse scan success feedback. Proximity detection or image capture alone is insufficient. Signal patterns, scan failure feedback, and acknowledgement transport remain undecided |
| FR9  | Suppress duplicate deliveries and handle partial failures                                                         | Duplicate suppression and camera and tracking failure outcomes confirmed. Timeout and retry values remain implementation details | Treat repeated scans of the same resi within a short period as one delivery within the same household, without additional notifications. Preserve the existing event rather than create duplicates. Camera or tracking failure does not suppress the initial alert. Use explicit unavailable states                                                                   |
| FR10 | Allow demo recipients and notification destinations to be configured                                              | Suggested                                                                                                                        | Prepared recipients can be used without changing application code                                                                                                                                                                                                                                                                                                     |
| FR11 | Allow the admin to register products in the app                                                                   | Confirmed                                                                                                                        | The admin can register BARDI CCTV cameras and an ESP32. Pairing and ownership verification method remain undecided                                                                                                                                                                                                                                                    |
| FR12 | Support multiple registered CCTV cameras, one selected delivery camera, and only one ESP32 in the household setup | Confirmed                                                                                                                        | The admin can register several cameras and designate exactly one for delivery capture. Each scan captures from that selected camera. Maximum registered camera count, changing the selection, and device replacement behaviour remain undecided                                                                                                                       |
| FR13 | Provide ESP32 source code and a firmware configuration and flashing guide through the app                         | Confirmed                                                                                                                        | The admin can access the firmware, configure WiFi credentials and the backend address, and build and flash the device following the guide. Android based WiFi provisioning is deferred. Exact tools and source delivery format remain undecided                                                                                                                       |
| FR14 | Provide a BARDI CCTV setup guide through the app                                                                  | Confirmed, content pending                                                                                                       | Publish the guide supplied by the project initiator after testing the existing camera. Do not present unverified steps as validated                                                                                                                                                                                                                                   |
| FR15 | Support admin signup, admin created member accounts, and admin and member roles                                   | Confirmed                                                                                                                        | The admin signs up and can create member accounts. Members can use their accounts without completing self registration. Authentication technology, role assignment, account verification, and first phone sign in remain undecided                                                                                                                                    |
| FR16 | Allow the admin to create household member accounts directly                                                      | Confirmed                                                                                                                        | The admin creates a member account and associates it with the household notification audience. Member self registration is not required. Required fields and initial sign in mechanics remain undecided                                                                                                                                                               |
| FR17 | Open the corresponding delivery page when a notification is tapped                                                | Confirmed                                                                                                                        | Show the scanned resi, photo or Photo unavailable, and lookup derived package details or Tracking details unavailable. If both dependencies fail, show both unavailable states. Exact successful lookup fields remain undecided                                                                                                                                       |

## 7. Nonfunctional requirements

| Area                        | Requirement or consideration                                                                                                                                        | Status                                                                                                                                        |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| Delivery feasibility        | Buildable by two people during the hackathon starting November 13, 2026, with the demonstration ready by November 28, 2026                                          | Dates and qualitative availability confirmed. Exact daily hours are not fixed                                                                 |
| Camera integration          | Programmatic image capture is required. RTSP with frame extraction is acceptable                                                                                    | Confirmed                                                                                                                                     |
| Camera cost and procurement | Prefer an Indonesia available camera priced Rp300,000 to Rp1,000,000 if a purchase is necessary. Reusing the existing BARDI camera could eliminate this purchase    | Confirmed original price preference. BARDI is the preferred existing candidate, pending successful testing                                    |
| Reliability                 | Use explicit processing states and limited retries so a failed dependency is visible                                                                                | Suggested                                                                                                                                     |
| Performance                 | Agree acceptable scan to notification latency                                                                                                                       | Undecided                                                                                                                                     |
| Privacy                     | Limit who can view delivery photos and recipient information and agree a retention period                                                                           | Suggested, policy undecided                                                                                                                   |
| Security                    | Protect camera credentials and API keys and restrict photo access                                                                                                   | Suggested                                                                                                                                     |
| Network                     | Laptop backend, ESP32, and selected BARDI CCTV share the demo WiFi. Internet connectivity supports tracking lookup and push delivery                                | Demo topology confirmed. Actual camera reachability, WiFi device isolation, external services, and recipient phone access remain to be tested |
| Capacity                    | Multiple CCTV cameras are allowed and only one ESP32 can be used in a user's setup. Recipient count, package volume, and maximum CCTV count remain open             | Device support and ESP32 limit confirmed. Other limits undecided                                                                              |
| Client experience           | Android first MVP using Vue, Vite, and Capacitor with a mobile first UI and mandatory push notifications. Future iOS expansion can reuse the shared web application | Android confirmed for the hackathon. iOS implementation and testing deferred. Push provider remains undecided                                 |
| Member onboarding usability | Admin creates member accounts and can assist with initial app setup on their phones. Members do not need to self register                                           | Confirmed goal and assisted setup. Required fields, authentication, and exact phone setup steps remain undecided                              |
| Operability                 | Make failures diagnosable and allow a clean demonstration reset                                                                                                     | Suggested                                                                                                                                     |

## 8. MVP scope

**Confirmed core outcome**

- App based product registration with multiple CCTV cameras allowed and one ESP32 only.
- ESP32 setup guide and firmware source code available through the app.
- BARDI CCTV setup guide supplied by the project initiator after camera testing.
- Physical package barcode scan through an ESP32 equipped with a camera or a barcode scanner module. MVP input option remains undecided.
- Backend receives scan data from the ESP32.
- A proximity sensor automatically triggers a scan attempt when a package is presented.
- A light and a buzzer inform the courier immediately after successful barcode decoding, independently of CCTV capture, shipping lookup, and push delivery.
- Programmatic delivery photo capture. Only a snapshot of the current view is required. Historical recordings and playback are outside the MVP.
- Shipping tracking API lookup.
- Admin signup and admin and member roles. The admin registers devices and creates member accounts directly. Member self registration is not required.
- The associated household's admin and members receive mandatory delivery push notifications. Tapping a notification opens its delivery page with the photo and package details from the resi lookup.

**Suggested scope limits, awaiting agreement**

- One household receiving location. Multiple CCTV cameras can be registered, with one ESP32 only. The admin selects one delivery camera during setup, and each scan captures from that camera only.
- A small set of prepared recipients and shipments.
- Current MVP refinement proposed by the user: support one courier service for the hackathon. SPX Express is now the proposed test courier, pending API and label validation. Testing packages and API provider remain undecided. Broad courier support remains a future product goal.
- Minimal recipient setup and operator feedback.
- Defer package collection tracking, continuous video recording, OCR, and face recognition. Under the proposed one courier MVP, multi courier coverage and automatic courier identification are also deferred.

**Undecided:** Whether package specific recipient preregistration or a prepared tracking number to person mapping is needed. Mobile app direction is confirmed as Vue, Vite, and Capacitor, with Android selected for the hackathon and iOS deferred as a future extension. Whether any fallback data is permitted in the demonstration remains undecided.

## 9. Assumptions to validate

- Suitable labelled packages can be used for testing.
- A tracking API can be accessed within the budget and timeframe.
- The API provides useful shipment fields for the selected courier.
- The barcode yields the tracking number, rather than a different internal shipment identifier.
- A recipient can be linked to a notification destination using an agreed source of truth.
- The camera and backend can communicate on the venue's network.
- A recipient device can receive the chosen type of push notification.
- The team has enough time to procure, configure, and test hardware.

None of these assumptions is a confirmed capability.

## 10. Technical considerations and decision register

These are evaluation topics, not an approved architecture.

| Topic                    | Current position                                                                                                                                                                  | Status or next validation                                                                                                                                                                                                                      |
| ------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| CCTV                     | Existing BARDI Smart IP Camera Indoor PTZ, firmware 5.7.4, is the preferred candidate pending successful testing. TP Link Tapo C210 remains an alternative from the initial brief | Final selection undecided. See CCTV Integration Research for findings and validation questions                                                                                                                                                 |
| CCTV capture approach    | Proposed RTSP and FFmpeg extraction of a current frame to JPEG. Start with an on demand connection and investigate a persistent connection if latency is problematic              | Proposal only. Capture access and latency on the owned camera remain unverified                                                                                                                                                                |
| Barcode input            | ESP32 camera captures the label image. Python backend performs barcode decoding                                                                                                   | Confirmed for the MVP. Code 128 is required for the supplied SPX sample. Exact board, sensor, decoder library, preprocessing, and image settings remain undecided                                                                              |
| Microcontroller          | ESP32, only one permitted in the household setup. Configure WiFi and backend address in firmware before flashing                                                                  | Device family and firmware based setup confirmed. Board, firmware framework, device authentication, and request protocol remain undecided                                                                                                      |
| Shipping API             | User now proposes one courier for the MVP. Broad support remains a future goal. No courier or provider selected                                                                   | Validate access, required verification inputs, returned fields, price, and limits for the chosen courier. A multi courier provider may still serve the one courier MVP. See Multi courier tracking research and coverage                       |
| Notification audience    | Notify the household's admin and registered members for each delivery event from its ESP32                                                                                        | Confirmed audience. Exact signup, membership, device pairing, and notification destination association remain undecided                                                                                                                        |
| Push notifications       | Mandatory in the Android MVP built with Vue, Vite, and Capacitor                                                                                                                  | Android confirmed. Tapping a notification opens the relevant delivery page showing photo and package details. Provider, phone count, and notification text remain undecided. Future iOS delivery requires its own setup and testing            |
| Backend and frontend     | Frontend uses Vue, Vite, and Capacitor. Teammate handles backend and prefers Python, FastAPI, PostgreSQL, and Prisma                                                              | Frontend direction confirmed. Backend preference recorded. Prisma's role and Python integration require validation                                                                                                                             |
| Repository               | Existing monorepo with frontend, backend, and ESP32 firmware apps                                                                                                                 | Confirmed by the user. Repository URL and files not inspected                                                                                                                                                                                  |
| Setup guides             | App provides ESP32 source code and setup steps plus BARDI setup steps                                                                                                             | Confirmed. Camera guide awaits the project initiator's testing and supplied content                                                                                                                                                            |
| Hosting and connectivity | Run the Python backend on a laptop connected to the same WiFi as the ESP32 and BARDI CCTV for the hackathon demonstration                                                         | Confirmed demo deployment. Internet is needed for tracking and push services. Venue connectivity, client isolation, and phone access from outside the LAN still need validation. Remote access mechanism and database hosting remain undecided |
| Photos and event data    | Storage, access rules, and retention not selected                                                                                                                                 | Undecided                                                                                                                                                                                                                                      |
| Processing order         | Requested sequence is capture, lookup, then notify                                                                                                                                | Confirmed initial workflow. Any change to concurrency or failure behaviour requires discussion                                                                                                                                                 |

**Research status:** CCTV documentation findings and user supplied research are recorded in CCTV Integration Research. The owned camera's firmware specific behaviour, stream access, and capture latency remain unverified. Frontend and ESP32 direction have now been supplied by the user. Hardware integration has not been tested in this planning session. Shipping API documentation findings are recorded in Multi courier tracking research and coverage. Actual API access and live package behaviour remain unverified. Replacement camera procurement remains unverified.

## 11. Risks

| Risk                                                                  | Consequence                                           | Suggested response                                                                                                                                                                                        |
| --------------------------------------------------------------------- | ----------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Recipient cannot be derived from tracking data                        | Correct notification routing is blocked               | Define the recipient mapping early                                                                                                                                                                        |
| Barcode contains a different identifier or several labels are present | Lookup fails or references the wrong shipment         | Test representative physical labels before choosing scanner behaviour                                                                                                                                     |
| Camera access or compatibility differs from expectations              | Photo capture is blocked                              | Validate capture on the exact device before purchase commitment where possible                                                                                                                            |
| Backend cannot reach the camera at the venue                          | End to end demonstration fails                        | Validate network placement and access restrictions early                                                                                                                                                  |
| Chosen courier's API access or required inputs are insufficient       | Tracking lookup cannot complete even with one courier | Validate a real sample and any required verification inputs for the chosen courier and agree a fallback. The user will select the courier later                                                           |
| Notification setup or photo rendering takes longer than expected      | Recipient experience remains incomplete               | Validate one real recipient device early                                                                                                                                                                  |
| Dependencies respond slowly or fail                                   | Inconsistent demonstration                            | Agree timeout, retry, and visible failure behaviour                                                                                                                                                       |
| Photos or recipient data are exposed unnecessarily                    | Privacy concerns                                      | Use controlled demo data and agree access and retention                                                                                                                                                   |
| Hardware procurement consumes the schedule                            | Too little integration time                           | Establish deadline and available equipment before committing                                                                                                                                              |
| Two person scope expands                                              | Working complete flow is delayed                      | Agree a narrow MVP before adding features                                                                                                                                                                 |
| Selected delivery camera is unavailable or points at the wrong area   | Delivery photo cannot be captured correctly           | Validate its view during setup. If capture fails, still notify the household and show Photo unavailable. Timeout and retry policy remain open. Automatic capture from other cameras has not been selected |
| ESP32 camera barcode reading does not meet demo needs                 | Physical scan flow is blocked                         | Validate the chosen input option before committing to a module                                                                                                                                            |
| Prisma's intended role in a Python backend is unclear                 | Database integration work may exceed the schedule     | Clarify whether the teammate intends the archived Prisma Client Python or another approach before finalisation                                                                                            |

## 12. Open questions

1. Resolved: admins sign up, register devices, and create member accounts directly. Both admin and members receive the household's delivery notifications, without needing addressee matching.
2. Schedule and availability resolved for initial planning: November 13 to November 28, 2026, with full time weekends and weekday nights for both teammates. Codex can handle delegated coding during their working hours. Exact hours can be estimated later if milestones require them.
3. Deferred: total hardware budget awaits the user's discussion with their teammate. Do not assume a spending cap or approved purchases. The existing BARDI Indoor PTZ camera running firmware 5.7.4 is available for reuse pending validation. Revisit the budget after that discussion.
4. Account creation and setup assistance resolved: the admin creates member accounts and can help set up the app on each member's phone. Exact authentication and first sign in mechanics remain open.
5. Current MVP proposal: support one courier service and defer broad coverage. SPX Express is the proposed test courier, pending validation. API provider, real test labels, barcode formats, verification inputs, and behaviour for unsupported shipments remain open.
6. Notification navigation and failure display resolved: open the corresponding delivery page with the scanned resi, available photo and package details, and explicit Photo unavailable or Tracking details unavailable states when needed. What exact fields belong in the notification summary and successful tracking detail display?
7. Platform and photo navigation resolved: Android for the hackathon. Tapping a notification opens the delivery page to view the photo and resi derived package details. Mention iOS as a future extension enabled by shared Capacitor web code, with iOS configuration, push setup, and testing still required.
8. Demo backend placement resolved: a laptop on the same WiFi as ESP32 and CCTV, with internet for tracking and push. Remote phone access and an HTTPS tunnel are deferred pending discussion with the teammate. Venue connectivity and device isolation still require validation.
9. What counts as a delivery event, and where should the courier position the package?
10. Courier feedback and dependency failure outcomes resolved: successful decoding triggers the light and buzzer independently of later processing. Notify admin and members even if CCTV capture, tracking lookup, or both fail. Show Photo unavailable and/or Tracking details unavailable on the delivery page. Duplicate suppression is confirmed: repeated scans of the same resi within a short period form one household delivery and do not send repeated notifications. Exact timeout, retry, and deduplication window values will use documented working defaults.
11. What rules govern external services, test data, and simulated fallbacks?
12. What latency, repeatability, and privacy expectations define a successful demo?
13. Does the owned BARDI camera running firmware 5.7.4 provide usable ONVIF and RTSP, and must either be enabled in the app?
14. What RTSP URL and authentication does this camera require, and is a direct HTTP snapshot endpoint available?
15. How long does scan triggered capture take, and is an on demand connection sufficient? See CCTV Integration Research for the validation checklist.
16. Resolved: the admin selects one delivery CCTV during setup. Each scan captures from that camera only. If capture fails, still send the household notification and show Photo unavailable on the delivery page. Exact timeout and retry policy remain open.
17. Input and processing resolved: ESP32 camera capture with Python backend decoding. Exact board, camera, decoder library, image settings, and hardware wiring remain open.
18. Firmware setup resolved: the admin configures WiFi credentials and backend address before flashing, using the provided source and guide. App based WiFi provisioning is deferred. Household linking, device authentication, flashing tools, and device replacement remain open.
19. What role does the teammate intend for Prisma in the Python backend, given the archived status of Prisma Client Python?

## 13. Collaborative planning process

**Confirmed:** Ask one or two focused questions at a time, discuss technology options before finalising them, and update this same PRD as decisions are made.

**Updated collaboration preference:** Skip obvious confirmation questions. Apply and document reasonable defaults for routine behaviour, and focus questions on meaningful scope, architecture, cost, and user experience tradeoffs. Continue respecting explicitly deferred decisions and discussing technology choices before finalisation.

**Duplicate handling working default:** Use a five minute suppression window keyed by household and normalised tracking number as a starting value for testing. The user confirmed suppression within a short period, not this exact duration. The duration is a provisional implementation default and can be tuned without a separate product approval question.

**Suggested discussion order:** Receiving scenario and recipient matching, then time and budget constraints, then MVP boundaries and acceptance criteria, then technology evaluation.

After the PRD is sufficiently defined, collaboratively plan the system architecture, hardware requirements, development milestones, and division of responsibilities. Detailed architecture and milestones have not yet been created. The responsibility split is confirmed: the project initiator owns PM, frontend, and CCTV setup. The teammate owns backend and ESP32 firmware and hardware integration. Detailed integration tasks will follow the architecture.

## 14. Decision history

| Decision                                                                                                                                          | Status                                                                                | Basis                                                                                                                        |
| ------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| Two person internal IoT hackathon project                                                                                                         | Confirmed                                                                             | Initial brief                                                                                                                |
| Hackathon starts November 13, 2026. Demonstration must be ready by November 28, 2026                                                              | Confirmed                                                                             | User supplied schedule. Described as a two week hackathon                                                                    |
| Both teammates can work full time on weekends and at night on weekdays, and use Codex for delegated coding during working hours                   | Confirmed working arrangement                                                         | Subsequent user clarification                                                                                                |
| Prioritise the complete working demonstration                                                                                                     | Confirmed                                                                             | Initial brief                                                                                                                |
| Broad support for all courier services                                                                                                            | Earlier product goal, retained for future scope                                       | User subsequently proposed a one courier MVP                                                                                 |
| Support one courier service for the hackathon MVP                                                                                                 | Current user proposal, recommended for the timeline                                   | Courier and API provider selection remain open                                                                               |
| Courier used for testing                                                                                                                          | SPX Express now proposed, pending validation                                          | User requested evaluation of SPX API availability                                                                            |
| Physical scan, photo, tracking lookup, and recipient push notification form the core journey                                                      | Confirmed initial workflow                                                            | Initial brief                                                                                                                |
| Prefer an Indonesia available CCTV costing Rp300,000 to Rp1,000,000                                                                               | Confirmed preference                                                                  | Initial brief                                                                                                                |
| RTSP frame extraction is acceptable                                                                                                               | Confirmed                                                                             | Initial brief                                                                                                                |
| Initial scanner, microcontroller, API, and stack selections                                                                                       | Earlier open decisions, partly resolved below                                         | ESP32 and frontend choices now supplied by the user. Exact input hardware, shipping API, and integration choices remain open |
| Household demonstration setting                                                                                                                   | Confirmed                                                                             | Subsequent user decision                                                                                                     |
| Existing BARDI Indoor PTZ camera, firmware 5.7.4                                                                                                  | Preferred candidate, pending successful testing                                       | User supplied CCTV research                                                                                                  |
| Current view snapshot only. Historical recordings and playback are not required                                                                   | Confirmed                                                                             | Subsequent user requirement                                                                                                  |
| RTSP and FFmpeg with an on demand connection, with persistent connection considered if needed                                                     | Proposed, not final architecture                                                      | User supplied integration proposal                                                                                           |
| Household user owning an ESP32 with a camera or barcode scanner module and BARDI CCTV                                                             | Confirmed target user                                                                 | Subsequent user specification                                                                                                |
| App registration, multiple CCTV cameras, and only one ESP32                                                                                       | Confirmed                                                                             | Subsequent user specification                                                                                                |
| Admin designates one delivery CCTV during setup. Each scan captures from that selected camera only                                                | Confirmed                                                                             | User selected option 1 on November 14, 2026                                                                                  |
| App provides ESP32 guide with source code and a BARDI guide supplied after the project initiator tests the camera                                 | Confirmed requirement, guide content pending                                          | Subsequent user specification                                                                                                |
| Registered user receives mandatory delivery push notifications                                                                                    | Confirmed, expanded to admin and member audience below                                | Subsequent user specification                                                                                                |
| Admin signup, admin and member roles, and admin registration of devices and members                                                               | Confirmed                                                                             | Subsequent user clarification                                                                                                |
| Admin creates member accounts directly. Members do not self register                                                                              | Confirmed                                                                             | User prioritises simple registration for household helpers and parents with limited confidence using technology              |
| Admin can assist with initial app setup on each member's phone                                                                                    | Confirmed                                                                             | User agreed to admin assisted initial setup. Exact authentication method remains undecided                                   |
| Delivery notifications go to the associated household's admin and registered members                                                              | Confirmed                                                                             | Subsequent user clarification                                                                                                |
| Tapping a notification opens its delivery page with the photo alongside package details from resi checking                                        | Confirmed                                                                             | User decision before pausing planning on November 13, 2026                                                                   |
| Light and buzzer signal successful barcode decoding without waiting for CCTV capture, tracking lookup, or push delivery                           | Confirmed                                                                             | User wants to avoid courier confusion when the CCTV connection fails                                                         |
| ESP32 captures the barcode image and the Python backend decodes it and returns the result for courier feedback                                    | Confirmed MVP architecture decision                                                   | User selected Python backend decoding on November 14, 2026                                                                   |
| Admin configures ESP32 WiFi credentials and backend address in firmware before flashing. Android based WiFi provisioning is deferred              | Confirmed MVP setup decision                                                          | User accepted firmware configuration on November 14, 2026                                                                    |
| CCTV capture failure does not block notifications to the admin and members. Delivery page shows Photo unavailable                                 | Confirmed                                                                             | User accepted the camera failure fallback on November 14, 2026                                                               |
| Tracking lookup failure does not block delivery notification. Use the scanned resi and any available photo, and show Tracking details unavailable | Confirmed                                                                             | User accepted the tracking failure fallback on November 14, 2026                                                             |
| Repeated scans of the same resi within a short period count as one household delivery and do not generate additional notifications                | Confirmed                                                                             | User accepted duplicate suppression on November 14, 2026. Exact duration is a tunable working default                        |
| Skip obvious questions and use documented defaults for routine behaviour                                                                          | Confirmed planning preference                                                         | User instruction on November 14, 2026                                                                                        |
| Existing monorepo with frontend, backend, and ESP32 apps                                                                                          | Confirmed by user, repository not inspected                                           | Subsequent user specification                                                                                                |
| Vue, Vite, Capacitor, and mobile first frontend                                                                                                   | Confirmed                                                                             | Subsequent user specification                                                                                                |
| Android is the hackathon MVP platform. iOS is a future extension to mention in the demonstration                                                  | Confirmed                                                                             | Subsequent user decision. Shared code enables reuse, while iOS setup and testing remain necessary                            |
| Backend owned by teammate, who prefers Python, FastAPI, PostgreSQL, and Prisma                                                                    | Ownership confirmed, stack preference recorded, Prisma integration pending validation | Subsequent user specification                                                                                                |
| Project initiator owns PM, frontend, and CCTV setup. Teammate owns backend and ESP32                                                              | Confirmed responsibility split                                                        | User specified ownership on November 14, 2026                                                                                |
| Run the backend on a laptop sharing the ESP32 and CCTV WiFi for the hackathon demonstration                                                       | Confirmed                                                                             | User agreed on November 14, 2026. Internet remains needed for tracking and push. Remote phone access is not yet defined      |

## 15. CCTV Integration Research

**Research update:** 2026-11-13

### Existing hardware and preference

**Confirmed by the user:** A BARDI Smart IP Camera Indoor PTZ is already owned and currently runs firmware **5.7.4**. It is the **preferred existing hardware candidate, pending successful testing**.

**Potential saving:** Successful reuse could eliminate the need to purchase another CCTV camera. The original Rp300,000 to Rp1,000,000 camera price preference remains relevant if a replacement is needed. Tapo C210 remains an alternative candidate from the initial brief.

### Confirmed findings and evidence boundaries

| Finding                                                                   | Evidence and status                                                                                                                                                                                   | Boundary                                                                                                                                                                                            |
| ------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| BARDI lists ONVIF support for Indoor PTZ                                  | Confirmed documentation finding. See [BARDI camera comparison](https://bardi.co.id/compare-product/camera/)                                                                                           | Documentation alone does not establish unit compatibility. The November 15 user test below confirms local ONVIF and RTSP playback in one configuration                                              |
| BARDI documentation states that its IP cameras support RTSP               | Confirmed documentation finding. See the RTSP entry in [BARDI support FAQ](https://faq.bardi.co.id/Faq/search/47)                                                                                     | The November 15 user test establishes a working stream URI, username, and playback configuration. Authentication protocol details and other restrictions remain unverified                          |
| BARDI is powered by Tuya, and Tuya provides camera snapshot functionality | Confirmed documentation findings from [BARDI support FAQ](https://faq.bardi.co.id/Faq/search/47) and [Tuya Camera SDK](https://developer.tuya.com/en/docs/app-development/ipc?id=Kf5fxtjv15t98)       | The linked Tuya page documents a HarmonyOS app SDK snapshot during video preview. This does not prove a backend HTTP snapshot API or SDK access to this BARDI unit                                  |
| FFmpeg can extract a JPEG from an accessible, decodable RTSP stream       | Confirmed general capability. See [FFmpeg RTSP documentation](https://ffmpeg.org/ffmpeg-protocols.html#rtsp) and [FFmpeg image output documentation](https://ffmpeg.org/ffmpeg-formats.html#image2-2) | The user relayed a successful local FFmpeg JPEG capture and visual verification, with a reported duration of 2.733 seconds for one test. Repeated capture and backend integration remain unverified |
| Only a snapshot of the current camera view is needed                      | Confirmed product requirement from the user                                                                                                                                                           | Historical recordings and playback are not required                                                                                                                                                 |

Additional product reference: [BARDI Indoor PTZ product](https://bardi.co.id/product/ip-camera-indoor-ptz/). Product family documentation does not substitute for testing the exact owned unit.

### Owned camera validation checkpoint

**User reported result:** 2026-11-15. Tested on the owned BARDI Indoor PTZ, reported firmware 5.7.4, from the user's Windows PC.

- ONVIF Device Manager discovers the camera. Login succeeds with username `admin` and the password configured in the BARDI app's ONVIF settings.
- Pan and tilt control through ODM works.
- `Test-NetConnection` to camera port 8554 reports `TcpTestSucceeded: True`.
- The observed stream URI is `rtsp://192.168.18.23:8554/Streaming/Channels/101`. This is the current LAN address and may change with network configuration.
- ODM Live video showed NO SIGNAL. VLC using the plain URI also failed without prompting for credentials.
- The user reports that VLC playback works when launched with explicit ONVIF credentials and `--rtsp-tcp`. The successful command used `--rtsp-user admin` and `--rtsp-pwd` with the locally entered password.
- No actual password is recorded here. Both credentials and transport were changed together, so this test does not isolate which change resolved playback.

**Established:** Local ONVIF discovery, authenticated access, PTZ control, RTSP playback, and a local FFmpeg JPEG capture now have user supplied test evidence on this unit. A single capture duration is recorded below. Unrestricted protocol support, an HTTP snapshot endpoint, repeated reliability, and backend compatibility remain unverified.

**Next validation:** Repeat independent FFmpeg captures, inspect freshness and reliability, then test the intended backend environment. RTSP with FFmpeg remains a proposed integration rather than a finalized architecture.

### Local JPEG snapshot result

**Evidence source:** Local Work Mode test report relayed by the user on 2026-11-15. The local agent reports that it opened and visually verified the resulting image. This planning assistant has not independently inspected that local file.

| Item                            | Observed result                                                                                                                             |
| ------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| Camera                          | Owned BARDI Indoor PTZ, reported firmware 5.7.4                                                                                             |
| Tool                            | FFmpeg 9.0.2, Gyan full build on Windows                                                                                                    |
| Stream                          | `rtsp://192.168.18.23:8554/Streaming/Channels/101`                                                                                          |
| Authentication                  | Username `admin` with the BARDI ONVIF password entered through a local masked prompt                                                        |
| Successful input options        | `-rtsp_transport tcp -timeout 10000000`                                                                                                     |
| Credential handling             | Password special characters were URL encoded. No credentials included in chat, saved scripts, or shared logs, according to the local report |
| Exit status                     | 0                                                                                                                                           |
| Reported capture duration       | 2.733 seconds for this one test                                                                                                             |
| Output                          | JPEG, 2880 × 1620 pixels, 688,205 bytes                                                                                                     |
| Visual result                   | Image opened successfully and was visually verified locally                                                                                 |
| Reported option incompatibility | This build rejected `-rw_timeout` in the test invocation. The successful invocation used `-timeout 10000000`                                |
| Changes made                    | Local snapshot test only. No repository or backend changes                                                                                  |

**Local output reference:** `C:\Users\ahmed\AppData\Local\Temp\BARDI-snapshot-20261115-212824-fee0d9a28d.jpg`. This is a file on the user's Windows PC, rather than an uploaded Notion attachment.

**Meaning:** The owned camera can supply a JPEG through a fresh local FFmpeg invocation in the tested configuration. The result strengthens the case for reusing it and evaluating on demand capture for the MVP.

**Limits:** This is one successful sample. It does not establish typical or worst case latency, repeated capture reliability, freshness across successive deliveries, performance in the final backend environment, or time from an ESP32 scan to a delivered notification. A direct HTTP snapshot endpoint is still unverified. Camera selection and connection strategy remain planning decisions.

**Next validation:** Repeat independent captures, verify that a changed scene appears in each new image, and record durations and failures before integrating with the backend. No persistent stream is selected by this result.

### Proposed integration, pending validation and discussion

**Proposed solution, not a final architectural decision:** When the backend receives a barcode scan event, it connects to the BARDI camera's RTSP stream, uses FFmpeg to extract the current frame, and saves the resulting JPEG associated with that delivery event. Backend hosting for the demonstration is confirmed as a laptop on the same WiFi as the ESP32 and CCTV. Storage location, credentials, capture integration, and phone access from outside the LAN remain undecided. Multiple cameras may be registered. The admin designates one delivery CCTV during setup, and each scan captures only from that selected camera.

**Proposed initial connection strategy:** Establish an RTSP connection on demand for each scan. Measure connection and capture latency before accepting the approach. If latency is a problem, investigate a persistent stream connection as an alternative.

A persistent connection would not require saving continuous video or historical recordings. Neither connection strategy has been approved as the final architecture.

### Technical validation checklist

The user has completed initial local camera tests, recorded below. Remaining unchecked items still need validation. The project initiator will supply the setup guide. The assistant has documented the reported results and has not operated the physical camera.

- [ ] Confirm the exact hardware variant and whether firmware 5.7.4 supports usable ONVIF and RTSP without restrictions.
- [ ] Determine whether ONVIF or RTSP must be manually enabled in the BARDI Smart Home application.
- [x] Verify a working local RTSP URI, port and stream path with VLC playback using explicit ONVIF credentials and TCP transport.
- [x] Verify ONVIF discovery, login with username admin, and pan and tilt control through ODM.
- [ ] Establish the precise authentication mechanism and whether credentials, TCP transport, or both were necessary to resolve the initial failure.
- [ ] Determine whether the camera exposes a direct HTTP snapshot endpoint.
- [ ] Measure time from receipt of a barcode scan event to a usable saved JPEG, including connection and capture time.
- [x] Extract one JPEG using FFmpeg over RTSP/TCP and visually verify the image locally, as reported by Local Work Mode.
- [x] Record one local capture duration, image dimensions, file size, and exit status.
- [ ] Validate freshness across changed scenes, repeated captures, and actual delivery events.
- [ ] Confirm that the intended backend environment can reach and decode the stream.
- [ ] If on demand capture is too slow for the agreed experience, compare it with a persistent connection.

**Open decision:** Final camera selection and capture architecture remain pending successful validation and discussion. No implementation has started in this planning session.

## 16. Repository, stack, and ownership

**Confirmed by the user:** The repository is [ahmadnaufal-f/cekrir](https://github.com/ahmadnaufal-f/cekrir), organised as apps/frontend, apps/backend, and apps/esp32. A static source review on 2026-11-15 examined main at bc45600de0906a4b7995ac71118025259072c8a5. The entries below preserve the user's stated scope and preferences. Actual scaffold findings and required corrections are documented in [Repository Scaffold Alignment and Codex Instructions](https://app.notion.com/p/4193556fda9281529832f3dc60f54fb5). Existing code does not establish that new product choices or integrations have been approved or tested.

| App      | Stated scope and technology                                                                                                                                              | Status                                                                                                                                      | Ownership         |
| -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------- | ----------------- |
| Frontend | Vue with Vite and Capacitor, Android first mobile UI, product registration, setup guides, and mandatory push notifications                                               | Android confirmed for the hackathon. Future iOS extension can reuse the web application. Push provider remains undecided                    | Project initiator |
| Backend  | Python with FastAPI and PostgreSQL, with Prisma preferred for database tooling                                                                                           | Teammate's stated stack preference. Prisma integration details require validation before finalisation                                       | Teammate          |
| ESP32    | Firmware for proximity triggered camera capture, image upload, and feedback based on the Python decode result. Admin sets WiFi and backend configuration before flashing | Scope and firmware based setup confirmed. Board, language and framework, device authentication, and communication protocol remain undecided | Teammate          |

### Confirmed responsibility split

| Team member       | Owned areas                                         |
| ----------------- | --------------------------------------------------- |
| Project initiator | Product management, frontend, and CCTV setup        |
| Teammate          | Backend and ESP32 firmware and hardware integration |

**Confirmed CCTV responsibility:** The project initiator will test the existing BARDI camera, configure its setup, and supply the validated camera guide.

**Camera validation checkpoint, November 14, 2026:** The user reports that the camera settings show an ONVIF option and an IP address. Their PC dual boots Windows and Linux. ONVIF enablement, authentication, discovery, RTSP playback, and JPEG capture have not yet been confirmed. Planning questions are paused while guiding local camera validation. The next suggested test uses ONVIF Device Manager on Windows to discover the actual media stream URI.

**Camera validation update, November 15, 2026:** The user successfully authenticated to ODM as admin, controlled camera rotation, reached TCP port 8554, and played the discovered RTSP URI in VLC using explicit ONVIF credentials and TCP transport. See the owned camera validation checkpoint in section 15. A later local FFmpeg test succeeded, with exit status 0, a visually verified 2880 × 1620 JPEG, and reported duration 2.733 seconds. Repeated capture performance and backend integration remain unverified.

**Integration work to define:** Agree the frontend API, ESP32 image upload and decode response contract, and backend camera capture configuration so each owner can work independently. This is a proposed coordination step, not a completed specification or new assignment.

**Database tooling validation:** If the teammate means Prisma Client Python, its maintainer has deprecated the project and the repository is archived. See the [maintainer's deprecation notice](https://github.com/RobertCraigie/prisma-client-py/issues/1073) and [archived repository](https://github.com/RobertCraigie/prisma-client-py). Clarify whether Prisma is intended for runtime queries, schema and migrations, or another role before finalising this choice. No replacement ORM has been selected.

### Confirmed ESP32 setup and proposed household linking

**Confirmed setup:** For the MVP, the admin edits firmware configuration to supply WiFi credentials and the backend address before building and flashing the ESP32. The app provides source code and a setup guide. Android based WiFi provisioning is deferred. The chosen firmware framework and flashing tools remain open.

**Proposed household linking, not yet final:** The admin registers the ESP32 in the app. The backend creates a device identity linked to that household and issues a device specific credential, which the admin copies into the firmware configuration. Scan uploads can then be associated with the correct household and authenticated independently of the admin's personal login. Keep real credentials out of the distributed source template. Credential format, API contract, and replacement or revocation workflow remain to be defined.

### Confirmed demonstration backend placement

Run the Python backend on a laptop connected to the same WiFi as the ESP32 and selected BARDI CCTV. This is the agreed hackathon setup, not a completed deployment or a validated production architecture. The network must allow device to device communication, and internet access is needed for tracking and push services.

Phone access is a separate decision: receiving a push notification does not establish that the phone can open a delivery page served by a private LAN backend. Mobile data or offsite access would require an agreed reachable route for app data and photos. No tunnel, public endpoint, or alternative deployment has been selected. Database and photo storage placement remain undecided.

### Candidate remote access option: HTTPS tunnel

**Status:** Deferred pending the user's discussion with their teammate. Remote phone access requirements and the use and choice of an HTTPS tunnel remain undecided. Laptop backend placement is still confirmed. No tunnel has been started and no local service has been published.

**Proposed arrangement:** Run the FastAPI backend and a tunnel agent on the same laptop. The agent initiates an outbound connection to a tunnel provider. The Android app uses an internet reachable HTTPS endpoint, and the provider forwards API requests over the tunnel to the laptop. [ngrok's agent documentation](https://ngrok.com/docs/gateway/agent) documents this connection model without opening inbound router ports.

**Local paths:** ESP32 scan traffic and BARDI image capture can stay on the local network. Expose the application's HTTP API and protected image routes, rather than directly exposing RTSP or PostgreSQL.

**When a notification is tapped:** The installed Capacitor app opens its delivery screen, requests the relevant delivery data from the HTTPS API, and fetches the stored photo through an authorised route. The screen is part of the mobile application. The tunnel provides access to its backend data and images.

**Push is a separate path:** The laptop can send a message to a push provider over the internet. The provider delivers it to the phone. Receipt of that alert does not establish that a subsequent API or image request can reach the laptop.

**Authentication proposal:** HTTPS secures transport, and the application's own login and household authorisation protect delivery data. The backend should check the user's session or token and household membership for each delivery and photo request. A public tunnel URL is not an access credential. Tunnel agent credentials stay on the laptop, rather than being embedded in the mobile app. Exact login technology remains open.

**Provider examples under evaluation:** [ngrok's getting started guide](https://ngrok.com/docs/start) documents a development domain for each account and mobile backend testing. [Cloudflare Quick Tunnels](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/) offer temporary URLs without an account or domain, but the hostname changes on restart and the service has no uptime guarantee. The documented email login option requires browser interaction, so it is not a drop in authentication solution for native API calls.

**Recommendation for discussion:** Prefer a stable HTTPS endpoint plus the app's normal login for the demonstration, keeping the camera integration local. A stable hostname avoids changing the app's API address whenever the tunnel restarts. Provider, account, plan, and exact configuration are not selected.

**Operational constraints:** The laptop, backend process, tunnel agent, and internet must remain available. A tunnel does not migrate the backend to a cloud server or provide laptop uptime. Validate the intended venue's outbound access and tunnel behaviour before the demonstration. A phone on mobile data should be used for a full notification tap, delivery data, and photo access test if remote use is selected.

### Mobile platform scope and demonstration message

**Confirmed:** Build and demonstrate Android for this hackathon. iOS is a future extension, not part of MVP acceptance testing. The user wants to mention the cross platform potential of Capacitor in the demonstration.

**Suggested demonstration wording:** For this hackathon, we are demonstrating the Android app. Capacitor lets us reuse our Vue application for a future iOS version, with iOS configuration, push notification setup, and testing still required.

**Evidence and limit:** [Capacitor's introduction](https://capacitorjs.com/docs) documents its Android and iOS runtimes. Its [iOS setup](https://capacitorjs.com/docs/ios) requires a separate native project and Xcode workflow, and its [push plugin documentation](https://capacitorjs.com/docs/apis/push-notifications) includes iOS specific configuration. Reusing the Vue application is an architectural opportunity. Actual iOS effort and compatibility have not been tested, so do not promise immediate or effortless iOS support. No iOS platform build is required for the hackathon.

### Team availability and development approach

**Confirmed:** Both teammates have full time availability on weekends and night time availability on weekdays. Both use Codex and can delegate coding tasks while they are at work. No exact daily hour estimate has been supplied.

**Planning consideration:** Delegated coding can progress during the day. Human review, physical hardware setup, camera and sensor validation, and end to end integration still need time when a teammate is available. Do not count daytime coding delegation as guaranteed full time human availability or assume that generated code has been integrated and verified.

**Planning boundary:** No code changes, firmware flashing, repository setup, or full implementation plan has been started as part of this planning session.

## 17. Barcode input feasibility and recommendation

**Status:** Python backend barcode decoding with ESP32 camera image capture is confirmed for the MVP. A proximity sensor triggers scan attempts, and the ESP32 uses the returned decode result for light and buzzer feedback. Local ESP32 decoding and dedicated scanners are outside the MVP. Exact camera board, decoder library, and firmware details remain undecided.

**User constraint:** Dedicated ESP32 barcode scanner products appear too expensive for the internal hackathon. The user is evaluating a camera module instead. No specific marketplace listing or price has been verified.

### Findings

- Espressif provides a camera driver for ESP32, ESP32 S2, and ESP32 S3 and supports JPEG capture. Its documentation highlights PSRAM requirements and memory pressure for raw colour capture, especially alongside WiFi. See [Espressif camera driver](https://github.com/espressif/esp32-camera).
- Espressif's QR code example demonstrates on device QR recognition. It does not demonstrate recognition of the linear barcode on the team's shipping labels. See [official QR demo](https://github.com/espressif/qrcode-demo).
- Camera capture and barcode decoding can run on different devices. ZXing C++ provides Python bindings that accept images and return barcode data, making backend decoding a candidate for the planned Python backend. See [decoder project](https://github.com/zxing-cpp/zxing-cpp) and [Python binding documentation](https://github.com/zxing-cpp/zxing-cpp/blob/master/wrappers/python/README.md).
- These sources establish building blocks, not tested performance on the team's board, camera, labels, or network.

**Confirmed procurement:** The team needs to buy a camera equipped ESP32. No purchase or exact hardware selection has been made.

### Options under discussion

| Option                                                      | Tradeoff assessment                                                                                                                       | Current recommendation                                                                |
| ----------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| Camera captures a label image and Python backend decodes it | Keeps firmware focused on capture and upload. Needs usable images and network connectivity. Adds image upload and backend decoding        | Selected for the MVP. Validate actual ESP32 images and response latency               |
| Camera captures and decodes entirely on ESP32               | Avoids uploading label images for decoding, but decoder support, memory use, and performance depend on the exact board and barcode format | Earlier alternative retained for reference. Outside the selected MVP                  |
| Dedicated barcode scanner module connected to ESP32         | Offloads barcode decoding to specialised hardware, with additional purchase cost and interface compatibility to check                     | Earlier alternative retained for reference. Outside the current two option comparison |

The tradeoffs and recommendation are technical assessments, not measured results or final decisions.

**Processing clarification:** With backend decoding, the ESP32 uploads a captured image per scan attempt or a limited set of retries. Continuous image streaming is not required. With local decoding, the ESP32 captures and processes frames on the device, then sends the decoded barcode text to the backend. It may inspect frames repeatedly while scanning without transmitting those frames to the server. Automatic scanning without a required button press is now preferred, pending validation. Capture cadence, retry limits, and idle behaviour remain undecided. Both approaches still use the separately planned BARDI photo capture for delivery context.

### Proposed behaviour and validation gate

**Confirmed processing flow:** The ESP32 captures the label image and sends it to the Python backend. A backend decoder extracts the barcode payload and returns the decode result to the ESP32. On success, the ESP32 signals with the light and buzzer, independently of CCTV capture, tracking lookup, or push delivery. Once a valid tracking number is established, the existing shipping lookup and notification flow continues, with a separately associated BARDI delivery photo. The ESP32 image serves close range barcode reading. The BARDI photo serves delivery context.

**User preference:** Start scanning automatically when the courier presents the package label, if feasible. A physical scan button should not be required in the preferred journey. This is a desired experience, not verified hardware functionality.

**Suggested MVP interaction:** The courier holds the barcode in a marked scan area. The device repeatedly attempts to read it and provides a visible or audible success signal once a usable code is accepted. Repeated attempts must be associated with one delivery event so that holding a label in view does not repeatedly capture delivery photos or send push alerts. The user has confirmed a light and a buzzer for scan success feedback. The success condition is now confirmed as successful barcode decoding, independently of CCTV capture, tracking lookup, and push delivery. Duplicate suppression is confirmed for repeated scans of the same household resi within a short period. Light colour, buzzer pattern, and exact deduplication duration will use documented working defaults.

**Automatic scanning options:** With local decoding, repeated frame processing can stay entirely on the ESP32. With backend decoding, the ESP32 can send periodic still images while scanning, with one request in flight at a time. This avoids requiring a video stream, but still generates ongoing image upload traffic while active. Sampling intervals, always active versus presence triggered operation, and network load require validation. The proximity sensor is now a confirmed component for the automatic scan trigger. Dedicated package classification and AI are not assumed requirements.

**Undecided:** Capture cadence, automatic retry and idle behaviour, the accepted barcode and tracking number validation rules, exact duplicate window and rearming, when to capture the BARDI photo relative to decoding, and the exact light and buzzer success patterns and any failure feedback.

**Proposed validation before committing:** Use the actual candidate board and camera to photograph representative real shipping labels at a marked distance with good lighting. Confirm that the complete barcode and its clear margins are visible and sharp, then verify decoding against the printed tracking number. Assess focus, angle, glare, damaged labels, multiple barcodes, latency, and repeated attempts. A proposed demo target is at least 9 correct successful scans in 10 attempts within a few seconds each under the agreed conditions. This target is for discussion, not an accepted requirement or an observed result.

**Important limit:** More backend processing cannot recover barcode detail missing from a blurred or undersized image. Success on a QR example or a synthetic label does not establish success on a real shipping barcode.

**Hardware procurement resolved:** The team needs to buy a camera equipped ESP32. The exact board, sensor, PSRAM, and included programming hardware must be checked before recommending a purchase.

**Current decision:** Use ESP32 camera capture with Python backend barcode decoding for the MVP. Use the proximity sensor for automatic scan triggering and return decode success to the ESP32 for light and buzzer feedback. Dedicated scanners and local ESP32 decoding are outside the MVP. Exact board, decoder library, firmware framework, and connection protocol remain undecided. No application or firmware implementation has started in this planning session.

## 18. Automatic scan trigger and idle image traffic

**Status:** The user has clarified that the intended component is a proximity sensor. A proximity sensor, camera module, light, and buzzer are confirmed components for the ESP32 scanner setup. Automatic scanning is preferred. Exact component models, prices, wiring, sensing distance, and trigger logic remain undecided.

**Confirmed trigger direction:** Use a proximity sensor to detect a package presented near the scan area without requiring physical contact. The earlier phrase contact sensor referred to proximity sensing. A physical contact switch is not the selected direction.

**Goal:** Keep image processing or presence detection local while idle. Upload barcode images only during bounded proximity triggered scan sessions to the selected Python backend. Continuous camera video transport and repeated idle image uploads are not required. Device management traffic, such as a heartbeat, is a separate decision.

### Separate trigger detection from barcode decoding

The trigger only needs to indicate that something has been presented in a defined scan area. A backend decoder can then determine whether the captured image contains a readable barcode. A local trigger does not prove that a package or barcode is present.

| Candidate                     | Proposed local behaviour                                                                                                                                                                   | Tradeoff                                                                                                                                                                    |
| ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Camera scene change detection | Compare a small grayscale view of a fixed scan region with an empty background reference. Arm a scan when a sustained change is detected, then wait for the image to settle before capture | No additional trigger sensor. Must handle shadows, lighting changes, vibration, and stationary packages. Algorithm and memory behaviour require testing on the chosen board |
| Proximity or distance sensor  | Detect an object entering the scan area and start a bounded capture session                                                                                                                | Additional component, mounting, and wiring. Distance does not establish barcode presence. Exact module, free GPIO pins, electrical compatibility, and cost need checking    |
| Local barcode decoding        | Continuously or periodically attempt decoding on ESP32 and send only accepted results                                                                                                      | No barcode image uploads are required, but local decoder feasibility remains unresolved                                                                                     |

### Proposed camera only trigger

1. Fix the camera and mark a scan area, with a clear empty background.
2. Periodically inspect small grayscale frames locally. Example cadence of two checks per second is a starting point for testing, not a verified performance figure.
3. Compare pixel data in the scan region with an empty reference. Require sustained change to avoid triggering on a single noisy frame.
4. After an arrival is detected, allow a short settling period so that a relatively still label can be captured. Frame to frame stability alone must not be treated as proof that the area is empty.
5. Capture a label quality JPEG for decoding. If using backend decoding, upload one image and await its result before considering another.
6. Retry within a bounded attempt count and session deadline. Stop on success, timeout, or object removal. Example maximum of three attempts is a proposal only.
7. After success or exhaustion, wait for the scan area to become empty before rearming. Backend deduplication and event IDs would additionally protect against repeated network submissions.

**Implementation caveat:** Compare decoded pixel or grayscale data, rather than compressed JPEG bytes. The feasibility and overhead of moving between local detection frames and label quality JPEG capture must be checked on the selected camera and board.

**Idle behaviour:** Camera frames may still be captured locally. No barcode images need to leave the device until a trigger is accepted. Local detection does not imply that the device is asleep or uses negligible power.

### Recommendation and validation

**Decision update:** The user has selected proximity sensing as the trigger direction. The camera only trigger above is retained as earlier research, rather than the current preferred approach. No particular proximity sensor model or integration has been selected or tested.

**Validation questions:** Can the camera be fixed toward a controlled scan area? Which proximity sensor and detection distance suit the camera focus and available GPIO pins? What false trigger rate, recognition latency, retry behaviour, and removal detection are acceptable?

### Confirmed scanner hardware and courier feedback

| Component                | Purpose                                                                              | Decision status                                                   |
| ------------------------ | ------------------------------------------------------------------------------------ | ----------------------------------------------------------------- |
| ESP32 with camera module | Capture the package barcode image                                                    | Required. Exact board and camera remain undecided                 |
| Proximity sensor         | Start a scan attempt when the courier presents the package without touching a switch | Confirmed. Exact sensor and detection thresholds remain undecided |
| Indicator light          | Provide visible confirmation that barcode scanning succeeded                         | Confirmed. Exact light, colour, and timing remain undecided       |
| Buzzer                   | Provide audible confirmation that barcode scanning succeeded                         | Confirmed. Exact buzzer and sound pattern remain undecided        |

The light is a courier status indicator. Additional illumination for the barcode camera has not been selected.

**Confirmed success semantics:** The light and buzzer signal that the barcode has been successfully decoded. They do not wait for CCTV capture, shipping API lookup, or recipient push notification delivery. A failed or slow CCTV connection must not block this feedback, since it could confuse the courier. Object proximity or image capture alone is insufficient.

**Confirmed acknowledgement flow:** Decoding runs in the Python backend, which returns the decode result to the ESP32. Only a successful decode result triggers the scan success light and buzzer. CCTV, tracking lookup, and push completion are not prerequisites. Exact response protocol, event acknowledgement details, and transport failure behaviour remain implementation decisions.

**Capture timing consideration:** Since the courier may leave after scan success, validate that the CCTV photo is still captured promptly enough to show useful delivery context. Camera failure must not block household notification. Show Photo unavailable on the delivery page when capture fails. Exact scheduling, timeout, and retry policy remain open.

**Hardware validation:** Check available GPIO pins, voltage and current requirements, and whether the selected feedback components need driver circuitry. Exact wiring, component quantities, and signal patterns will be planned after board selection.

References: [ESP32 camera driver](https://github.com/espressif/esp32-camera), [author's ESP32 frame difference example](https://github.com/s60sc/ESP32-CAM_Motion/blob/master/ESP32-CAM_Motion.ino), and [ST distance sensor example](https://www.st.com/en/imaging-and-photonics-solutions/vl53l0x). These establish component and example availability, not validated end to end behaviour on the proposed hardware.

## 19. Multi courier tracking research and coverage

**Research date:** 2026-11-13

### Current MVP scope proposal

The user originally requested support for all courier services and has now proposed narrowing the hackathon MVP to one courier service. Broad courier support remains a future product goal. The user will choose the courier and physical packages used for testing later. SPX Express is now proposed for testing, pending validation. No API provider has been selected.

**PM assessment:** A one courier MVP is recommended for the November 28 demonstration. It allows the courier code to be configured in advance, removes the need for automatic courier identification in the demo, and narrows label and API validation. It does not remove requirements for barcode decoding, live tracking access, any courier specific verification data, or failure handling.

**Unverified scope:** The exact required courier list and geographical coverage are not yet enumerated. Provider selection, contracted access, actual coverage, and performance remain undecided. Universal support has not been established.

### What Cekresi publicly documents

- [Cekresi's website](https://cekresi.com/) and [FAQ](https://cekresi.com/tanja/) advertise automatic tracking number detection and support for more than 60 couriers.
- This is a finite supported network. It does not establish support for every courier service.
- Cekresi's FAQ states that it no longer offers a public API. Its [API documentation page](https://cekresi.com/api.php) still shows historical request examples with tracking number and courier code, but the same page also states that the REST API is not available publicly. Treat these examples as documentation, not verified usable access.
- Public pages do not disclose the full internal detection algorithm or whether each underlying integration uses partner APIs, other authorised access, or another mechanism. Do not present a guessed implementation as a verified account of Cekresi's backend.
- The website includes a JNE form requesting the final five digits of the recipient phone number. A tracking number alone is therefore not guaranteed to be sufficient for every lookup.

### Comparable integration candidates

| Service    | Documentation finding                                                                                                                                                                                                                      | Remaining validation                                                                                                                             |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| Cekresi    | More than 60 couriers and autodetection advertised on the website. Public API is stated to be unavailable                                                                                                                                  | Cannot assume access for our backend                                                                                                             |
| BinderByte | [Tracking documentation](https://docs.binderbyte.com/api/cek-resi) advertises 28 couriers, requires API key, courier code, and AWB, and provides a courier availability list. JNE has an additional recipient phone verification parameter | API account access, actual required courier coverage, response fields, price, limits, and behaviour on real packages                             |
| Biteship   | [Help centre](https://help.biteship.com/hc/en-us/articles/58286997471513-Testing-Mode-Fee-Policy) describes a public tracking endpoint taking waybill and courier code, distinct from tracking an order created through Biteship           | Current public endpoint availability, documentation consistency, eligible couriers, access, required verification inputs, price, and rate limits |

No service has been selected. No API credentials, account registration, purchases, or live tracking requests have been made.

### Proposed technical direction

**Suggestion:** For the one courier MVP, evaluate an accessible API that supports the chosen courier. A multi courier aggregator is still an option, even if only one courier is enabled. Normalise its tracking result into the app's agreed fields. Provider selection remains open. Broader coverage and automatic courier identification can be revisited later.

**Courier identification remains separate from barcode decoding:** The scanned payload may provide only a tracking number. If the provider requires a courier code, the backend needs an additional identification mechanism. Possible approaches include a provider detection endpoint, number format based candidate selection with verification, or an agreed fallback when ambiguous. For the proposed one courier MVP, use of a preconfigured courier code would avoid needing automatic identification. It would not prove that a scanned shipment belongs to that courier. The exact configuration and unsupported shipment behaviour remain undecided.

A number prefix or length may narrow candidates but must not be treated as universally unique. Blindly querying every courier could add delay and cost. Required detection behaviour and limits must be agreed after provider evaluation.

### Open questions and proposed failure behaviour

- Which provider covers the required courier services and offers usable access within this hackathon?
- Deferred future scope: what does all couriers mean as an explicit coverage list, and which geographical market is required?
- Proposed MVP simplification: preconfigure the chosen courier rather than detect it from each scan. How should wrong courier or unrecognised shipments be handled?
- How will courier specific verification data, such as recipient phone digits or shipment dates, be obtained when required? App notification recipients are not automatically the package addressee.
- Which package fields are reliably available, and what does the app show when fields are absent?
- **Confirmed fallback:** Still send the household admin and members a delivery alert with the scanned resi and any available photo when tracking lookup fails. Show Tracking details unavailable on the delivery page. If camera capture also fails, additionally show Photo unavailable. Lookup failure must not be presented as proof that no package arrived. Timeout and retry policy remain undecided.
- The user will provide the testing courier later. No comprehensive cross courier validation claim is made.

## 20. SPX Express as the candidate test courier

**Status:** SPX Express (Shopee Express Indonesia) is the user's proposed test courier. Neither final courier selection nor an API provider has been approved. No live tracking request has been tested.

### Findings

- [SPX Indonesia](https://spx.co.id/id) provides public website tracking. A documented self service official API for arbitrary resi lookup was not confirmed.
- [SPX terms, section 9](https://spx.co.id/id/terms-of-service.html) describe API access as restricted to SPX authorised users. Public website tracking does not establish public API access.
- [BinderByte documentation](https://docs.binderbyte.com/api/cek-resi) explicitly lists Shopee Express with courier code spx. Its tracking endpoint requires an API key, courier code, and AWB. Its documented extra phone verification parameter applies to JNE, not SPX.
- [17TRACK's SPX Indonesia page](https://www.17track.net/en/carriers/shopee-xpress-id?hl=id-ID) also presents SPX tracking and an API integration route. Exact API carrier code, onboarding, cost, and retrieval timing require validation.

### Recommendation for discussion

SPX is a reasonable candidate if the team can obtain a real label and an accessible tracking API returns useful data. Evaluate BinderByte first as a candidate, using its documented SPX code. This recommendation does not select the provider.

Before commitment, verify account access, current SPX availability, quota and cost, returned fields, and latency using a real SPX resi. Do not assume public API means free access or guaranteed live availability. Do not treat a website's undocumented internal endpoint as a verified supported developer API.

The scanned identifier must be the SPX shipment resi rather than a Shopee order number. Test against the actual printed package label.

### First supplied label and image decoding check

**Observed sample:** The user supplied an SPX package label photo. The large barcode was decoded as **Code 128** with payload **SPXID06784833890B**, matching the visible printed resi.

**Method:** Local analysis of the supplied image using ZXing C++ Python bindings, version 3.1.1. Direct decoding of the original image returned no barcode. Image preprocessing, including 2x resizing of the grayscale image and cropped or rotated variants, produced valid decoder results with the same payload. Some variants returned checksum errors and were rejected. This is an image feasibility check, not application implementation.

**What this establishes:** At least this real SPX label can yield its tracking number through a standard backend barcode decoder. Code 128 support is required for this sample. A QR only reader would not cover it.

**Limits:** The image came from the user's upload, not the proposed ESP32 camera. No result establishes ESP32 capture quality, local ESP32 decoding feasibility, scan speed, or live tracking API availability. The user has confirmed that they can keep the physical label for ESP32 hardware testing. The resi has not been sent to a tracking provider.

**Next validation:** The user will check the BinderByte API on 2026-11-14. Actual API access, SPX response fields, cost, and latency remain unverified until results are reported. The physical SPX label will be retained for capture and decoding tests with the chosen ESP32 camera at the intended distance and lighting.

**Resolved:** An uploaded sample label, decoded resi, and physical label availability for hardware testing are confirmed.

**Deferred:** BinderByte live API evaluation awaits the user's November 14 check. No provider has been selected and no live tracking success is claimed.

**Resolved failure behaviour:** Tracking lookup failure does not block delivery notification. Use the scanned resi and any available photo, and show Tracking details unavailable on the delivery page.

**Open:** API provider, timeouts and retries, and final acceptance of SPX as the test courier. Continue independent product questions while API evaluation is pending.

### Related pages

- [Backend Deployment Discussion](backend-deployment.md)

- [Frontend Screens and User Flows](https://app.notion.com/p/4193556fda928198a935cb459a0f639d)

- [Frontend API and Mock Contract](https://app.notion.com/p/4193556fda92812ba7bef45b4699ec2f)

- [Android Push Notifications and Delivery Navigation](https://app.notion.com/p/4193556fda9281af98bfc3a7b7a32c1f)

- [Frontend Device and Member Setup](https://app.notion.com/p/4193556fda92812f958dfde3f3644d61)

- [Frontend Verification and Demo Checklist](https://app.notion.com/p/4193556fda9281eab368e0076914082c)

- [Frontend Codex Handoff](https://app.notion.com/p/4193556fda92818e9719e95fbac4b667)

- [Repository Scaffold Alignment and Codex Instructions](https://app.notion.com/p/4193556fda9281529832f3dc60f54fb5)
