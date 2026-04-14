

## Hebron Guide — Product Document

**Overview**
Hebron Guide is a civic utility app for Hebron residents, built around four integrated modules: ticket management, government document guidance, real-time road status, and local business availability. Each module operates independently but shares underlying infrastructure — GPS, crowd-sourcing, and AI validation — to provide a cohesive, trustworthy experience.

---

### Module 1 — Tickets

Citizens can look up any outstanding violations issued to them — road rule infractions, illegal parking, or waste disposal fines — by entering their **national ID number** or **vehicle plate number**. Each ticket record displays the violation type, exact location, date and time of issuance, and any attached photo evidence captured by enforcement officers.

**Payment** is handled directly within the app, supporting Visa cards as well as locally integrated Palestinian payment platforms, eliminating the need to visit government offices.

---

### Module 2 — Government Documents

This module acts as a comprehensive bureaucratic guide for residents navigating official processes. It addresses two pain points: not knowing *what* documents are needed, and not knowing *how* to fill them correctly, and where to get those documents.

Features include:
- A scalable library of application templates from government bodies, municipalities, and private institutions.
- Process-specific checklists (e.g., "to install solar panels, you need: building ownership deed, technical plan, municipality permit application...").
- Filling guides that highlight common errors and explain exactly what each field requires.
- An **OCR-powered digital filling** tool that lets users scan existing documents and fill or submit forms electronically — reducing paperwork errors and office trips.

---

### Module 3 — Road Status

A live, GPS-integrated road map powered by the **Google Maps API** and fueled by community reports. Residents submit real-time reports about road conditions, congestion, checkpoint activity, and closures directly from their location.

**Trust & verification** is enforced through a point-based system:
- Every submitted report that is verified earns the reporter **1 point**.
- A report is considered verified once **25 matching reports** are filed from users whose GPS confirms they are physically at or near the reported location.
- An **AI model** cross-checks report consistency across submissions to filter false or duplicate entries.

Additional coverage includes: military/police **checkpoint status**, **open gas stations**, and **electric vehicle charging point** availability.

---

### Module 4 — Shops & Pharmacies

A crowd-sourced directory showing which shops and pharmacies in the user's immediate area are **currently open**. Status is updated by the community in real-time, with GPS verification ensuring reporters are physically present before marking a business open or closed. Users can filter by category (pharmacy, grocery, bakery, etc.) and proximity.

---

### Extra Feature — Live Utility Prices

A live pricing dashboard displaying current rates for electricity (per kWh), water (per cubic meter / liter), and other essential utilities — sourced directly from the **Hebron Electric Institution** and relevant water authorities. Residents get a quick, reliable reference without needing to navigate multiple institutional apps.
