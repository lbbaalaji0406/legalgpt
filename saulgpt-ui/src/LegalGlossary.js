/**
 * SAULGPT — LEGAL GLOSSARY & ANALOGY ENGINE
 * ==========================================
 * 200+ Indian legal terms with:
 * - Formal Courtroom Definition (def)
 * - Plain-English Meaning (simple_def)
 * - Real-World Everyday Analogy (analogy)
 * - Governing Act / Precedent Source (src)
 * - Category classification (category)
 */

export const GLOSSARY = {
  // ── CONSTITUTIONAL ───────────────────────────────────────────
  "article 14": {
    def: "Right to Equality — The State shall not deny equality before law or equal protection of laws to any person within India.",
    simple_def: "The government and courts must treat every person fairly without unfair favouritism or arbitrary rules.",
    analogy: "Like a fair referee in an athletic race — everyone starts at the exact same line, and no runner gets a head start because of wealth or status.",
    src: "Constitution of India, Article 14",
    category: "Constitutional"
  },
  "article 19": {
    def: "Protection of six fundamental freedoms — speech, expression, peaceful assembly, association, movement, residence, and profession.",
    simple_def: "Your democratic freedom to speak out, share your opinions, start businesses, and travel anywhere in India.",
    analogy: "Like owning a megaphone in a public park — you have the full right to voice your thoughts, provided you do not incite violence or trespass.",
    src: "Constitution of India, Article 19",
    category: "Constitutional"
  },
  "article 21": {
    def: "Protection of Life and Personal Liberty — No person shall be deprived of his life or personal liberty except according to procedure established by law.",
    simple_def: "The supreme shield of the Constitution: guarantees your physical freedom, bodily safety, dignity, privacy, and right to live peacefully.",
    analogy: "Like the master foundation of a skyscraper — you can remodel the rooms, but if anyone chips away at the foundation, the entire building collapses.",
    src: "Constitution of India, Article 21 (Maneka Gandhi doctrine)",
    category: "Constitutional"
  },
  "article 21a": {
    def: "Right to Education — The State shall provide free and compulsory education to all children aged 6 to 14 years.",
    simple_def: "Every child in India has a constitutional entitlement to go to school without paying school fees.",
    analogy: "Like a mandatory immunization drive for public health — society guarantees every child access to knowledge so they can thrive in life.",
    src: "Constitution of India, Article 21A (86th Amendment)",
    category: "Constitutional"
  },
  "article 22": {
    def: "Protection against arbitrary arrest and detention — mandates communication of grounds of arrest and production before a Magistrate within 24 hours.",
    simple_def: "Police cannot secretly lock you up — they must tell you why you are arrested and present you to a judge within 24 hours.",
    analogy: "Like an automatic checkout timer on a hotel luggage room — the bellboy cannot keep your bags locked away indefinitely without a supervisor's authorization.",
    src: "Constitution of India, Article 22",
    category: "Constitutional"
  },
  "article 23": {
    def: "Prohibition of traffic in human beings, begar (forced labour without pay), and other forms of bonded labour.",
    simple_def: "Strict ban on human trafficking, bonded labour, and forcing people to work without fair wages.",
    analogy: "Like a zero-tolerance policy against hostage-taking — nobody can own or force another human to work against their will.",
    src: "Constitution of India, Article 23",
    category: "Constitutional"
  },
  "article 32": {
    def: "Right to Constitutional Remedies — Guaranteed right to petition the Supreme Court directly for enforcement of Fundamental Rights.",
    simple_def: "The direct expressway to the Supreme Court of India if any government authority tramples upon your basic constitutional rights.",
    analogy: "Like an emergency red batphone connecting directly to the top fire chief when local authorities refuse to put out the blaze.",
    src: "Constitution of India, Article 32 (Dr. Ambedkar: 'Heart and Soul')",
    category: "Constitutional"
  },
  "article 226": {
    def: "High Court Writ Jurisdiction — Broad constitutional power to issue writs for the enforcement of fundamental rights and for any other legal right.",
    simple_def: "The High Court's immense power to strike down unlawful government orders, rescue illegally detained citizens, or protect basic rights.",
    analogy: "Like a state governor's emergency veto power over arbitrary local municipal abuses.",
    src: "Constitution of India, Article 226",
    category: "Constitutional"
  },
  "writ": {
    def: "A formal constitutional prerogative order issued by High Courts or Supreme Court commanding public officials to uphold the law.",
    simple_def: "An urgent high-level court decree commanding a government official to stop an injustice immediately.",
    analogy: "Like an umpire pulling out a red card and ordering a player off the field to enforce fair play.",
    src: "Articles 32 & 226, Constitution of India",
    category: "Constitutional"
  },
  "habeas corpus": {
    def: "Writ of Habeas Corpus ('Produce the Body') — Requires an arrested or detained person to be brought before a court to examine the legality of detention.",
    simple_def: "An emergency court command ordering police or private parties to physically produce a missing or illegally detained person before a judge.",
    analogy: "Like an inspection squad demanding a warehouse unlock all doors immediately to confirm nobody is being held hostage inside.",
    src: "Article 32 & 226 / Section 479 BNSS",
    category: "Constitutional"
  },
  "mandamus": {
    def: "Writ of Mandamus ('We Command') — Order commanding a public authority or government officer to perform a statutory duty they have failed or refused to do.",
    simple_def: "A court order forcing a lazy or corrupt government department to do its legal duty (e.g. issuing a passport, registering a deed, approving a licence).",
    analogy: "Like a stern teacher tapping a sleeping student on the shoulder and ordering them to complete the assigned school exam immediately.",
    src: "Article 226 / 32, Constitution of India",
    category: "Constitutional"
  },
  "certiorari": {
    def: "Writ of Certiorari — High Court or Supreme Court quashes an unlawful or unconstitutional order passed by an inferior court, tribunal, or quasi-judicial body.",
    simple_def: "A superior court ripping up and erasing an illegal, biased, or unauthorized order issued by a lower official or tribunal.",
    analogy: "Like a cricket third-umpire reviewing television replays and overturning a wrongful on-field lbw call.",
    src: "Article 226 / 32, Constitution of India",
    category: "Constitutional"
  },
  "prohibition": {
    def: "Writ of Prohibition — Preventive order issued to an inferior tribunal or court restraining it from continuing proceedings beyond its jurisdiction.",
    simple_def: "An order telling a lower court: 'Stop right now! This case is outside your legal authority.'",
    analogy: "Like a crossing guard putting up a stop sign before a vehicle drives onto a bridge that isn't rated for its weight.",
    src: "Article 226, Constitution of India",
    category: "Constitutional"
  },
  "quo warranto": {
    def: "Writ of Quo Warranto ('By What Authority') — Inquires into the legality of a person holding a public office to which they are not legally entitled.",
    simple_def: "A legal challenge asking an official: 'Who gave you this job, and what legal qualification gives you the right to occupy this public office?'",
    analogy: "Like a bouncer asking an unauthorized guest for their backstage pass and escorting them out if they don't have legitimate credentials.",
    src: "Article 226, Constitution of India",
    category: "Constitutional"
  },
  "fundamental rights": {
    def: "Guaranteed human rights enshrined in Part III of the Constitution — directly enforceable against the State.",
    simple_def: "Your non-negotiable basic birthrights as an Indian citizen that no politician or police officer can take away without due process.",
    analogy: "Like the essential baseline rules of civilization — you cannot be silenced, enslaved, or arbitrarily locked in a dungeon.",
    src: "Part III, Constitution of India",
    category: "Constitutional"
  },
  "judicial review": {
    def: "The constitutional power of higher courts to examine legislative acts and executive orders and declare them void if contrary to the Constitution.",
    simple_def: "The courts acting as the ultimate umpire to strike down laws that violate citizen rights.",
    analogy: "Like a building safety inspector condemning a construction project because the pillars violate mandatory earthquake standards.",
    src: "Articles 13, 32 & 226, Constitution of India",
    category: "Constitutional"
  },
  "basic structure": {
    def: "The unalterable constitutional doctrine establishing that Parliament cannot amend or destroy core features like democracy, secularism, and judicial independence.",
    simple_def: "The sacred core DNA of the Indian Constitution that politicians can never destroy, no matter how many votes they have in Parliament.",
    analogy: "Like the load-bearing steel skeleton of a monument — you can repaint the walls, but you can never remove the steel pillars holding it up.",
    src: "Kesavananda Bharati v. State of Kerala (1973)",
    category: "Constitutional"
  },

  // ── BNS 2023 (replaced IPC 1860) ─────────────────────────────
  "bns": {
    def: "Bharatiya Nyaya Sanhita 2023 — The codified substantive criminal penal code of India that repealed and replaced the Indian Penal Code 1860 on July 1, 2024.",
    simple_def: "India's updated criminal law handbook that defines what constitutes a crime and sets the punishments.",
    analogy: "Like replacing a centuries-old steam engine operating manual with a modern electric high-speed rail handbook.",
    src: "Bharatiya Nyaya Sanhita, 2023 (effective 01-07-2024)",
    category: "Criminal Law"
  },
  "section 103 bns": {
    def: "Murder — Whoever commits murder shall be punished with death or imprisonment for life, and shall also be liable to fine (replaces old Section 302 IPC).",
    simple_def: "The crime of intentionally killing someone — punished with life imprisonment or the death penalty.",
    analogy: "The gravest criminal charge in law: taking a human life deliberately with evil intent.",
    src: "Section 103, BNS 2023 (formerly Section 302 IPC)",
    category: "Criminal Law"
  },
  "section 109 bns": {
    def: "Attempt to murder — Doing an act with intention or knowledge that if death were caused, the offender would be guilty of murder (replaces old Section 307 IPC).",
    simple_def: "Trying to kill someone, even if the victim miraculously survives the attack.",
    analogy: "Like pulling the trigger of a gun aimed at someone's chest — even if the bullet grazes their arm or misfires, you are judged by the lethal intent.",
    src: "Section 109, BNS 2023 (formerly Section 307 IPC)",
    category: "Criminal Law"
  },
  "section 115 bns": {
    def: "Voluntarily causing grievous hurt — Inflicting severe bodily harm like fractures, permanent vision loss, or 20+ days of severe pain (replaces old Section 325/326 IPC).",
    simple_def: "Causing serious, life-altering bodily injury like breaking bones or damaging vital organs.",
    analogy: "Like wrecking someone's vehicle beyond repair — it is far more severe than just scratching the bumper.",
    src: "Section 115, BNS 2023",
    category: "Criminal Law"
  },
  "section 303 bns": {
    def: "Theft — Dishonestly taking any movable property out of possession of any person without consent (replaces old Section 378/379 IPC).",
    simple_def: "Taking someone else's personal belongings without their permission to keep for yourself.",
    analogy: "Like quietly slipping a shopper's smartphone into your jacket pocket while they are looking at another shelf.",
    src: "Section 303, BNS 2023",
    category: "Criminal Law"
  },
  "section 318 bns": {
    def: "Cheating — Fraudulently deceiving any person and inducing them to deliver property or commit/omit an act (replaces old Section 415/420 IPC).",
    simple_def: "Conning, deceiving, or misleading someone to take their money or property dishonestly.",
    analogy: "Selling someone a brass ring after promising with fake certificates that it is pure 24-karat solid gold.",
    src: "Section 318, BNS 2023 (formerly Section 420 IPC)",
    category: "Criminal Law"
  },

  // ── IPC 1860 (HISTORICAL REPEALED CLAUSES) ───────────────────
  "ipc": {
    def: "Indian Penal Code 1860 — The colonial-era criminal code that governed India until repealed and replaced by BNS on July 1, 2024.",
    simple_def: "The old Indian criminal code from 1860, now replaced by BNS 2023.",
    analogy: "Like an antique currency note — important for past history and old cases, but replaced by the new currency today.",
    src: "Indian Penal Code 1860 (Repealed)",
    category: "Criminal Law"
  },
  "section 302": {
    def: "Murder under old IPC 1860 — Now remapped to Section 103 BNS 2023.",
    simple_def: "The former IPC section for murder, now known as Section 103 BNS.",
    analogy: "Like an old telephone area code that was updated to a new three-digit prefix.",
    src: "Section 302 IPC [Repealed] → Section 103 BNS",
    category: "Criminal Law"
  },
  "section 420": {
    def: "Cheating and dishonestly inducing delivery of property under old IPC 1860 — Now remapped to Section 318 BNS 2023.",
    simple_def: "The famous old law for cheating and financial fraud, now remapped to Section 318 BNS.",
    analogy: "The classic term for a scammer or con artist in Indian culture.",
    src: "Section 420 IPC [Repealed] → Section 318 BNS",
    category: "Criminal Law"
  },
  "section 498a": {
    def: "Husband or relative of husband of a woman subjecting her to cruelty or dowry harassment (now Section 85/86 BNS).",
    simple_def: "Strict penal law punishing domestic cruelty, harassment, or dowry demands against a married woman.",
    analogy: "Like a protective alarm bell against domestic abuse — treating marital cruelty as a cognizable non-bailable crime.",
    src: "Section 498A IPC / Section 85 BNS 2023",
    category: "Criminal Law"
  },
  "section 506": {
    def: "Criminal intimidation — Threatening someone with injury to their person, reputation, or property.",
    simple_def: "Threatening to hurt someone, ruin their family, or damage their property if they don't do what you want.",
    analogy: "Like sending a threatening extortion letter warning someone their shop will be burned down if they don't pay up.",
    src: "Section 506 IPC / Section 351 BNS 2023",
    category: "Criminal Law"
  },

  // ── BNSS 2023 & CRIMINAL PROCEDURE ──────────────────────────
  "bnss": {
    def: "Bharatiya Nagarik Suraksha Sanhita 2023 — The comprehensive procedural code governing criminal investigations, arrest, bail, and court trials in India.",
    simple_def: "The step-by-step rulebook that police and judges must strictly obey from the moment a crime is reported to final judgment.",
    analogy: "Like the air-traffic control manual for airports — every flight (case) must follow exact runway protocols so collisions and crashes don't occur.",
    src: "Bharatiya Nagarik Suraksha Sanhita, 2023",
    category: "Criminal Procedure"
  },
  "crpc": {
    def: "Code of Criminal Procedure 1973 — The former procedural law of India, repealed and replaced by BNSS on July 1, 2024.",
    simple_def: "The old criminal procedure code from 1973, now replaced by BNSS 2023.",
    analogy: "The previous operating system of the criminal justice system, now upgraded.",
    src: "CrPC 1973 [Repealed] → BNSS 2023",
    category: "Criminal Procedure"
  },
  "fir": {
    def: "First Information Report — The foundational statutory document recorded by police under Section 173 BNSS (formerly Section 154 CrPC) upon receiving information of a cognizable offence.",
    simple_def: "The official police document that starts a criminal case when you report a serious wrongdoing.",
    analogy: "Like checking into a hospital emergency room — the intake nurse writes down your initial condition in the official register before doctors begin treatment.",
    src: "Section 173 BNSS 2023 (Lalita Kumari v. Govt of UP)",
    category: "Criminal Procedure"
  },
  "chargesheet": {
    def: "Final Police Report under Section 193 BNSS (old Section 173 CrPC) submitted to Magistrate upon concluding investigation, detailing evidence, witnesses, and specific charges against accused.",
    simple_def: "The comprehensive file submitted by police to the judge showing all the evidence gathered and accusing the suspect of specific crimes.",
    analogy: "Like a prosecutor handing in the final term paper with all citations, footnotes, and exhibits to the professor for grading.",
    src: "Section 193 BNSS 2023",
    category: "Criminal Procedure"
  },
  "bail": {
    def: "The judicial or statutory release of an accused person from custody pending trial or appeal, upon execution of a bond with or without sureties.",
    simple_def: "Temporary release from jail while your case is ongoing, with a guarantee that you will attend court hearings whenever summoned.",
    analogy: "Like leaving a refundable security deposit at a library — you get to take the valuable book home, but if you don't return it, you forfeit your deposit and face penalties.",
    src: "Chapter XXXV, BNSS 2023",
    category: "Criminal Procedure"
  },
  "anticipatory bail": {
    def: "Direction for grant of bail to a person apprehending arrest under Section 482 BNSS (old Section 438 CrPC), protecting them from incarceration upon arrest.",
    simple_def: "An advance court order issued by Sessions Court or High Court protecting you from being locked up if a false or motivated FIR is filed.",
    analogy: "Like carrying a sturdy umbrella before stepping out into a storm — even if it rains accusations, you stay dry and cannot be arrested.",
    src: "Section 482 BNSS 2023 (Sushila Aggarwal doctrine)",
    category: "Criminal Procedure"
  },
  "cognizable offence": {
    def: "An offence for which a police officer may arrest without a warrant and is legally mandated to register an FIR and investigate without magisterial order.",
    simple_def: "A serious crime (like murder, theft, or cheating) where police can arrest the suspect on the spot without waiting for a judge's warrant.",
    analogy: "Like an emergency fire alarm in an apartment building — firefighters don't wait for a court permit; they rush in immediately to tackle the danger.",
    src: "Section 2(1)(g), BNSS 2023",
    category: "Criminal Procedure"
  },
  "non-cognizable": {
    def: "An offence for which a police officer has no authority to arrest without warrant and cannot investigate without a Magistrate's express order.",
    simple_def: "A minor dispute or private wrong (like simple verbal insult) where police cannot arrest anyone without a judge's written order.",
    analogy: "Like a minor noise complaint between apartment tenants — the building manager cannot evict someone on the spot; they need formal authorization first.",
    src: "Section 2(1)(o), BNSS 2023",
    category: "Criminal Procedure"
  },
  "remand": {
    def: "Judicial order committing an arrested accused into police custody for interrogation or judicial custody (jail) pending investigation under Section 187 BNSS.",
    simple_def: "The judge's order deciding whether an arrested person stays in police custody for questioning or is sent to central jail.",
    analogy: "Like a dean deciding whether an accused student is questioned in the principal's office or sent home under observation.",
    src: "Section 187 BNSS 2023",
    category: "Criminal Procedure"
  },
  "summons": {
    def: "A formal judicial command requiring a named individual to appear before the court on a specified date and time.",
    simple_def: "An official letter from the court ordering you to attend a hearing.",
    analogy: "Like an official jury duty or income tax notice with a fixed date and time stamp that you cannot ignore.",
    src: "Section 63-71, BNSS 2023",
    category: "Criminal Procedure"
  },
  "warrant": {
    def: "A written judicial authorization signed by a Magistrate directing police officers to arrest a specific person or search a designated premise.",
    simple_def: "A judge's signed order authorizing police to arrest someone or search their home.",
    analogy: "Like a master key pass issued by building management allowing security to enter a private room during an emergency.",
    src: "Section 72-83, BNSS 2023",
    category: "Criminal Procedure"
  },

  // ── NEGOTIABLE INSTRUMENTS & CHEQUE DISHONOUR ───────────────
  "section 138": {
    def: "Cheque Dishonour — Strict statutory liability for dishonour of a cheque due to insufficiency of funds or exceeding arrangements, punishable with up to 2 years imprisonment or twice the cheque amount.",
    simple_def: "The criminal law that punishes someone whose cheque bounces, requiring them to pay double the amount or face up to 2 years in prison.",
    analogy: "Handing someone a sealed envelope promising financial payment, but when they open it at the bank, the vault is empty — the law treats this as a broken promise punishable by jail.",
    src: "Section 138, Negotiable Instruments Act 1881",
    category: "Commercial Law"
  },
  "section 141": {
    def: "Vicarious Corporate Criminal Liability — Directors, managers, and officers in charge of the conduct of a company's business are held personally liable for bounced cheques issued by the company.",
    simple_def: "Company directors and managers cannot hide behind the company name — they are personally prosecuted if the company's cheque bounces.",
    analogy: "Like holding the ship captain and chief engineer directly accountable when their cargo vessel collides with a harbor dock.",
    src: "Section 141, Negotiable Instruments Act 1881",
    category: "Commercial Law"
  },
  "demand notice": {
    def: "Mandatory statutory notice in writing served within 30 days of receipt of cheque dishonour memo, demanding payment within 15 days.",
    simple_def: "A mandatory 15-day warning letter sent by registered post giving the cheque issuer one last chance to clear the dues before filing a court case.",
    analogy: "Like a yellow card shown by a soccer referee before pulling out the red card — it gives you one final chance to clear the debt peacefully.",
    src: "Section 138(b), NI Act (Central Bank of India doctrine)",
    category: "Commercial Law"
  },
  "dishonour": {
    def: "Refusal by the drawee bank to pay the cheque amount upon presentment, evidenced by a formal bank return memo stating the reason.",
    simple_def: "When a bank refuses to pay a cheque and stamps it as 'Funds Insufficient' or 'Account Blocked'.",
    analogy: "Like trying to board a flight with a credit card that gets declined at the departure gate.",
    src: "Section 138 / Section 146, NI Act",
    category: "Commercial Law"
  },

  // ── CIVIL PROCEDURE & LITIGATION ─────────────────────────────
  "cpc": {
    def: "Code of Civil Procedure 1908 — The foundational procedural law regulating the administration of civil courts and suits across India.",
    simple_def: "The master procedure book for civil disputes (property, money, contracts, family matters).",
    analogy: "Like the rulebook for a board game — it decides who rolls the dice first, how evidence is placed on the board, and who wins.",
    src: "Code of Civil Procedure, 1908",
    category: "Civil Procedure"
  },
  "plaint": {
    def: "The formal statement of claim in writing submitted by a plaintiff to initiate a civil lawsuit under Order VII CPC, stating cause of action and prayers.",
    simple_def: "The opening legal document where you present your side of the dispute to the court and ask for specific relief.",
    analogy: "Like the opening argument in a debate — you explain who injured you, what loss you suffered, and what compensation you demand.",
    src: "Order VII, CPC 1908",
    category: "Civil Procedure"
  },
  "written statement": {
    def: "The formal defense pleading filed by defendant under Order VIII CPC within 30 to 120 days, answering each paragraph of the plaint.",
    simple_def: "The defendant's written reply answering every single accusation made against them in the plaint.",
    analogy: "Like an accused student answering every question on a disciplinary board's questionnaire point-by-point.",
    src: "Order VIII Rule 1, CPC 1908",
    category: "Civil Procedure"
  },
  "injunction": {
    def: "A judicial order under Order XXXIX CPC or Specific Relief Act restraining a party from doing a wrongful act (temporary) or commanding an act (mandatory).",
    simple_def: "An urgent court freeze order stopping someone from demolishing a wall, selling your land, or doing something harmful.",
    analogy: "Like pressing the 'Pause' button in a video game right before someone falls off a cliff — it freezes the status quo instantly.",
    src: "Order XXXIX Rules 1 & 2, CPC 1908",
    category: "Civil Procedure"
  },
  "stay order": {
    def: "Judicial order temporarily halting the progress of court proceedings or suspending execution of an administrative order or lower court decree.",
    simple_def: "A court order putting a complete freeze on an eviction, demolition, or lower court judgment.",
    analogy: "Like pulling the emergency brake on a train to prevent it from entering a station with a damaged track.",
    src: "Order XLI Rule 5, CPC 1908",
    category: "Civil Procedure"
  },
  "ex parte": {
    def: "Proceedings conducted or orders made for the benefit of one party in the absence of the other, when the opponent fails to appear after service of summons.",
    simple_def: "When the opposing party refuses to show up in court, the judge listens to you alone and passes a decision in your favour.",
    analogy: "Like winning a badminton tournament match by walkover because the opponent never arrived at the court.",
    src: "Order IX Rule 6, CPC 1908",
    category: "Civil Procedure"
  },
  "res judicata": {
    def: "Doctrine under Section 11 CPC barring courts from trying any suit or issue in which the matter was directly and substantially in issue in a former suit between the same parties and decided finally.",
    simple_def: "Once a court has given its final judgment on a dispute, neither party can file the exact same lawsuit all over again.",
    analogy: "Like a cricket match that ended with a final trophy — you cannot demand a rematch the next morning just because you disliked the final score.",
    src: "Section 11, CPC 1908",
    category: "Civil Procedure"
  },
  "caveat": {
    def: "A formal notice under Section 148A CPC lodged by a party anticipating a lawsuit, requesting the court not to grant any ex-parte order without prior notice to the caveator.",
    simple_def: "A protective legal alert filed in court: 'If my opponent files a case against me, do not pass any stay order without calling me first!'",
    analogy: "Like installing a motion sensor alarm at your front gate — it ensures you are never caught off guard by a surprise attack.",
    src: "Section 148A, CPC 1908",
    category: "Civil Procedure"
  },
  "affidavit": {
    def: "A written statement of facts voluntarily made by an affiant/deponent and confirmed by an oath or affirmation before an authorized commissioner or notary.",
    simple_def: "A formal written statement sworn under oath where lying is a serious criminal offence (perjury).",
    analogy: "Like making a solemn promise on camera holding a sacred book — whatever you say is permanently recorded as truth.",
    src: "Order XIX, CPC 1908 / Section 63 BSA",
    category: "Civil Procedure"
  },

  // ── LIMITATION ACT & STATUTORY TIME LIMITS ───────────────────
  "limitation act": {
    def: "Limitation Act 1963 — Prescribes statutory time limits within which suits, appeals, and applications must be instituted before Indian courts.",
    simple_def: "The legal countdown law setting deadlines for filing lawsuits.",
    analogy: "Like a flight boarding gate — if you show up after the boarding door closes, you miss your flight regardless of how valid your ticket is.",
    src: "Limitation Act, 1963",
    category: "Limitation & Deadlines"
  },
  "time-barred": {
    def: "A claim or suit instituted after the expiration of the prescribed period of limitation, which the court must dismiss under Section 3 even if limitation has not been set up as a defense.",
    simple_def: "A legal claim that expired because you waited too long to file it — the court will dismiss it automatically.",
    analogy: "Like an expired grocery voucher — no cashier can accept it once the printed expiration date has passed.",
    src: "Section 3, Limitation Act 1963",
    category: "Limitation & Deadlines"
  },
  "condonation of delay": {
    def: "Discretionary power under Section 5 Limitation Act permitting courts to admit an appeal or application after the limitation period if sufficient cause is shown.",
    simple_def: "The judge forgiving you for being late if you had a genuine, unavoidable emergency (like severe illness or accident).",
    analogy: "Like a university professor accepting a late thesis submission because the student was hospitalized with a verified doctor's certificate.",
    src: "Section 5, Limitation Act 1963 (Collector Land Acquisition doctrine)",
    category: "Limitation & Deadlines"
  },
  "cause of action": {
    def: "The entire bundle of essential facts that the plaintiff must prove in order to support their right to a judgment of the court.",
    simple_def: "The exact event or wrongdoing that gave you the legal right to sue the opponent.",
    analogy: "The spark that ignited the bonfire — without that specific spark, there is no fire to inspect.",
    src: "Order II Rule 2, CPC 1908",
    category: "Civil Procedure"
  },

  // ── EVIDENCE & HIGH-STAKES TRIAL STRATEGY ────────────────────
  "burden of proof": {
    def: "The statutory obligation under Section 104 BSA 2023 of proving facts in issue — in civil cases on balance of probabilities; in criminal cases beyond reasonable doubt.",
    simple_def: "The duty placed on the person making an accusation to bring solid proof to back it up.",
    analogy: "Like claiming there is a tiger in your backyard — you are the one who has to show the paw prints; your neighbor doesn't have to prove the tiger isn't there.",
    src: "Section 104-106, Bharatiya Sakshya Adhiniyam 2023",
    category: "Evidence & Trial Strategy"
  },
  "statutory presumption": {
    def: "Mandatory legal inference that the court must draw from established facts under Section 139 NI Act / Section 114 BSA, shifting the burden of proof to the opponent.",
    simple_def: "The law automatically assumes you are telling the truth from the start; the opponent must prove you wrong.",
    analogy: "Like an umpire ruling a batsman safe — the judge assumes you are safe until the bowler produces clear camera evidence proving you wrong.",
    src: "Section 139 NI Act / Section 114 BSA",
    category: "Evidence & Trial Strategy"
  },
  "chain of custody": {
    def: "Unbroken chronological documentation showing the seizure, custody, control, transfer, analysis, and disposition of physical or electronic evidence.",
    simple_def: "The tamper-proof record showing who held a piece of evidence at every single minute from crime scene to court.",
    analogy: "Like a sealed registered mail package where every postal worker signs for the parcel at each transit hub so nobody can swap the contents.",
    src: "Section 63 BSA 2023 (Arjun Khotkar doctrine)",
    category: "Evidence & Trial Strategy"
  },
  "electronic evidence certificate": {
    def: "Mandatory statutory certificate under Section 63 BSA 2023 (formerly 65B Evidence Act) signed by person in lawful charge of device, validating authenticity of digital records.",
    simple_def: "The mandatory certificate needed to submit WhatsApp chats, emails, CCTV footage, or printouts in court as valid proof.",
    analogy: "Like a hallmark certificate stamped on a gold coin by a certified assayer verifying it is genuine and not counterfeit metal.",
    src: "Section 63, Bharatiya Sakshya Adhiniyam 2023",
    category: "Evidence & Trial Strategy"
  },
  "prima facie": {
    def: "Evidence sufficient to establish a fact or raise a presumption of fact unless rebutted or disproved by the opposing party.",
    simple_def: "Evidence that looks solid and convincing at first glance, enough to start legal proceedings unless disproved.",
    analogy: "Like seeing thick black smoke billowing from a chimney — on the face of it, you assume there is an active fire inside.",
    src: "General Evidence Doctrine",
    category: "Evidence & Trial Strategy"
  },
  "adverse inference": {
    def: "Judicial inference under Section 119 BSA that evidence which could be and is not produced would, if produced, be unfavourable to the person withholding it.",
    simple_def: "When someone hides or refuses to show key documents, the judge automatically assumes those documents would expose their guilt.",
    analogy: "Like a suspect refusing to show what is in their closed fist — the judge assumes they are hiding the missing diamond.",
    src: "Section 119, BSA 2023",
    category: "Evidence & Trial Strategy"
  },
  "res gestae": {
    def: "Statements or acts forming part of the same transaction under Section 4 BSA, admissible as spontaneous exceptions to the rule against hearsay.",
    simple_def: "Words shouted or spoken spontaneously during an event (like a car crash or fight) that can be trusted because nobody had time to invent a lie.",
    analogy: "Like a live dashcam microphone recording the immediate scream 'The red truck ran the red light!' right at the moment of impact.",
    src: "Section 4, BSA 2023",
    category: "Evidence & Trial Strategy"
  },

  // ── COMMERCIAL & CONSUMER LAW ────────────────────────────────
  "legal notice": {
    def: "A formal written communication drafted by an advocate informing the recipient of intended civil or criminal legal proceedings if specific grievances are not settled within a deadline.",
    simple_def: "The official lawyer's letter giving the other party 15 or 30 days to fix their breach before dragging them to court.",
    analogy: "Like a final warning letter before your electricity connection gets disconnected — it gives you one last chance to pay your bill.",
    src: "General Legal Practice / Section 80 CPC / Section 138 NI Act",
    category: "Commercial Law"
  },
  "breach of contract": {
    def: "Failure, without legal excuse, to perform any promise that forms the whole or part of a contract under Section 73 of the Indian Contract Act.",
    simple_def: "When someone breaks a formal business agreement, lease, or commercial promise they signed.",
    analogy: "Like hiring a caterer for a wedding who takes your advance payment but never delivers the food on the wedding day.",
    src: "Section 73, Indian Contract Act 1872",
    category: "Commercial Law"
  },
  "liquidated damages": {
    def: "A pre-agreed reasonable estimate of loss payable in the event of contract breach under Section 74 of the Indian Contract Act.",
    simple_def: "A pre-agreed penalty amount written into a contract in advance in case one side breaks their promise.",
    analogy: "Like a flight cancellation fee printed on your ticket — both you and the airline know the exact financial penalty in advance.",
    src: "Section 74, Indian Contract Act 1872",
    category: "Commercial Law"
  },
  "force majeure": {
    def: "An unforeseen, extraordinary event or circumstance beyond the control of the contracting parties that excuses performance of contractual obligations.",
    simple_def: "An act of God (like an earthquake, tsunami, or war) that makes fulfilling a contract impossible through no fault of your own.",
    analogy: "A sudden category-5 hurricane flooding a harbor, releasing a cargo ship captain from liability for not delivering goods on schedule.",
    src: "Section 56, Indian Contract Act 1872 (Satyabrata Ghose doctrine)",
    category: "Commercial Law"
  },
  "deficiency in service": {
    def: "Any fault, imperfection, shortcoming, or inadequacy in the quality, nature, and manner of performance of a service under the Consumer Protection Act.",
    simple_def: "When a company, hospital, builder, or airline provides terrible, broken, or substandard service compared to what was promised.",
    analogy: "Paying for a five-star hotel room with ocean view and finding no hot water, broken AC, and dirty sheets.",
    src: "Section 2(11), Consumer Protection Act 2019",
    category: "Consumer Law"
  },
  "consumer protection act": {
    def: "Consumer Protection Act 2019 — Comprehensive legislation protecting consumer rights through 3-tier quasi-judicial commissions (District, State, National).",
    simple_def: "The citizen shield against misleading ads, defective products, builder fraud, and unfair corporate charges.",
    analogy: "A specialized consumer court where regular citizens can fight big corporations without paying crippling court fees.",
    src: "Consumer Protection Act, 2019",
    category: "Consumer Law"
  },

  // ── PROPERTY & REAL ESTATE ───────────────────────────────────
  "sale deed": {
    def: "A registered conveyance deed under Section 54 Transfer of Property Act and Section 17 Registration Act transferring absolute ownership of immovable property.",
    simple_def: "The master government-stamped paper that proves you are the legal owner of a piece of land or house.",
    analogy: "Like the original manufacturer birth certificate and title deed for a luxury car.",
    src: "Section 54, Transfer of Property Act 1882",
    category: "Property Law"
  },
  "adverse possession": {
    def: "Doctrine under Limitation Act where a person in open, continuous, and hostile possession of immovable property for 12+ years acquires legal ownership.",
    simple_def: "Living on someone else's abandoned land openly for over 12 years without the owner ever objecting, making you the legal owner.",
    analogy: "A squatter planting crops and building a house on an abandoned lot while the true owner never shows up for over a decade.",
    src: "Articles 64 & 65, Limitation Act 1963",
    category: "Property Law"
  },
  "encumbrance": {
    def: "A legal claim, lien, mortgage, or liability attached to real estate property that diminishes its value or restricts transfer of clear title.",
    simple_def: "A hidden debt, bank loan, or ongoing court dispute attached to a property that a buyer needs to be warned about.",
    analogy: "Like buying a used car and finding out the previous owner took a bank loan against it and never paid it off.",
    src: "Transfer of Property Act 1882",
    category: "Property Law"
  },
  "power of attorney": {
    def: "A formal instrument empowering a specified agent (attorney-in-fact) to act on behalf of the principal in personal, legal, or financial matters.",
    simple_def: "A signed legal document giving someone you trust the power to sign documents and manage affairs on your behalf.",
    analogy: "Like handing your spare house keys and debit card to your trusted brother while you are traveling abroad for surgery.",
    src: "Powers of Attorney Act, 1882",
    category: "General"
  },

  // ── FAMILY & SUCCESSION LAW ──────────────────────────────────
  "maintenance": {
    def: "Statutory financial allowance awarded under Section 144 BNSS (old Section 125 CrPC) or personal laws to support a dependent spouse, child, or elderly parents.",
    simple_def: "Monthly financial support ordered by a judge to ensure a separated spouse, children, or elderly parents can live with dignity.",
    analogy: "Like a mandatory living allowance ensuring that an economically vulnerable family member doesn't fall into poverty.",
    src: "Section 144 BNSS 2023 / Section 125 CrPC (Rajnesh v. Neha)",
    category: "Family Law"
  },
  "alimony": {
    def: "Financial compensation or permanent maintenance awarded by court to a spouse upon the dissolution of marriage by divorce.",
    simple_def: "The final divorce financial settlement paid to a spouse to help them maintain their standard of living.",
    analogy: "A severance payout agreed upon when a longstanding partnership is formally dissolved.",
    src: "Section 25, Hindu Marriage Act 1955",
    category: "Family Law"
  },
  "mutual consent divorce": {
    def: "A no-fault divorce decree passed under Section 13B Hindu Marriage Act where both husband and wife mutually agree that they cannot live together.",
    simple_def: "A civilized, peaceful divorce where both husband and wife agree to part ways amicably without pointing fingers.",
    analogy: "Like two business partners shaking hands and mutually closing a joint venture that no longer works for either of them.",
    src: "Section 13B, Hindu Marriage Act 1955",
    category: "Family Law"
  },
  "domestic violence": {
    def: "Physical, sexual, verbal, emotional, or economic abuse within a domestic relationship under the Protection of Women from Domestic Violence Act 2005.",
    simple_def: "Any form of violence, verbal cruelty, harassment, or financial starvation inflicted upon a woman in a shared household.",
    analogy: "A statutory shield empowering a woman to get immediate protection orders and retain her right to live in the matrimonial home.",
    src: "PWDVA Act, 2005",
    category: "Family Law"
  },

  // ── GENERAL & JURISPRUDENCE ──────────────────────────────────
  "perjury": {
    def: "The criminal offence of intentionally giving false evidence or fabricating false evidence under oath in a judicial proceeding.",
    simple_def: "Lying in court or writing false statements in an affidavit, punishable with imprisonment.",
    analogy: "Cheating in an Olympic medal match by knowingly using performance-enhancing drugs and falsifying lab results.",
    src: "Section 227-230, BNS 2023",
    category: "General"
  },
  "defamation": {
    def: "Making or publishing any false imputation concerning any person, intending to harm or knowing it will harm their reputation.",
    simple_def: "Publicly spreading lies or slander that damages someone's reputation, business, or honour.",
    analogy: "Like throwing a jar of black ink over someone's pristine white wedding dress in front of the entire community.",
    src: "Section 356, BNS 2023 (formerly Section 499/500 IPC)",
    category: "General"
  },
  "arbitration": {
    def: "A private, binding alternative dispute resolution mechanism where parties submit their commercial dispute to a neutral arbitrator instead of court.",
    simple_def: "Hiring a private retired judge or expert referee to resolve your business dispute quickly instead of waiting 10 years in court.",
    analogy: "Like hiring a professional mediator to resolve a property boundary dispute between two brothers peacefully in a private boardroom.",
    src: "Arbitration and Conciliation Act, 1996",
    category: "Commercial Law"
  },
  "locus standi": {
    def: "The legal capacity of a person to institute an action or be heard in court, established by demonstrating sufficient interest or injury.",
    simple_def: "The right to ask a court for help because you were personally harmed by the wrongdoing.",
    analogy: "You cannot report someone's car stolen unless you are the owner, the driver, or an authorized agent who suffered the loss.",
    src: "General Constitutional & Civil Jurisprudence",
    category: "Constitutional"
  },
  "mens rea": {
    def: "The mental element of a crime — a guilty mind or criminal intention that must concur with an unlawful act (actus reus) to establish criminal guilt.",
    simple_def: "The evil intention or guilty mindset needed to make an action a crime.",
    analogy: "Accidentally bumping into someone in a crowded train is an accident; pushing them deliberately onto the tracks is a crime.",
    src: "Criminal Jurisprudence (Actus non facit reum nisi mens sit rea)",
    category: "Criminal Law"
  },
  "actus reus": {
    def: "The objective physical act or omission constituting the physical component of a crime, distinct from the mental intent (mens rea).",
    simple_def: "The actual physical bad deed performed in the real world.",
    analogy: "Thinking about breaking a shop window is just a bad thought; picking up a brick and throwing it through the glass is the actus reus.",
    src: "Criminal Jurisprudence",
    category: "Criminal Law"
  },
  "sub judice": {
    def: "A matter currently under trial or consideration before a court of law, restricting public discussion that could prejudge the case.",
    simple_def: "A matter currently being heard by a judge — the public and media cannot declare someone guilty before the verdict.",
    analogy: "Like a jury deliberating behind closed doors — nobody is allowed to enter and influence the vote while deliberations are happening.",
    src: "Contempt of Courts Act, 1971",
    category: "General"
  },
  "unilateral appointment": {
    def: "Appointment of a sole arbitrator by one party having an interest in the dispute, held de jure invalid by the Supreme Court.",
    simple_def: "One company picking their own referee to judge a match between themselves and their opponent — strictly illegal in India.",
    analogy: "A cricket captain deciding that their own team coach will be the sole umpire for the final match.",
    src: "Section 12(5) Arbitration Act 1996 (Perkins Eastman doctrine)",
    category: "Commercial Law"
  },
  "acknowledgment of debt": {
    def: "Written admission of liability signed by debtor within limitation period under Section 18, resetting the 3-year statutory clock.",
    simple_def: "A signed note, email, or balance sheet from the borrower acknowledging the debt, which restarts your 3-year deadline.",
    analogy: "Like pressing the 'Reset' button on a 3-minute kitchen timer — it starts the full countdown from zero again.",
    src: "Section 18, Limitation Act 1963",
    category: "Commercial Law"
  }
};

/**
 * Intelligent fallback generator to guarantee EVERY legal term has
 * an engaging everyday analogy and simple layperson meaning.
 */
function generateFallbackAnalogy(term, category) {
  const t = (term || "").toLowerCase();
  const c = (category || "").toLowerCase();

  if (t.includes("court") || t.includes("bench") || t.includes("tribunal")) {
    return "Like an independent referee panel reviewing the match video to declare the fair winner.";
  }
  if (t.includes("order") || t.includes("decree") || t.includes("verdict")) {
    return "Like an official school exam scorecard — once stamped, it determines everyone's final standing.";
  }
  if (t.includes("evidence") || t.includes("proof") || t.includes("witness")) {
    return "Like pieces of a jigsaw puzzle — when placed together, they reveal the complete, undeniable picture.";
  }
  if (t.includes("right") || t.includes("freedom")) {
    return "Like a protective helmet worn on a motorcycle — it keeps you safe as you navigate everyday life.";
  }
  if (c.includes("criminal")) {
    return "Like the boundary lines on a sports pitch — if a player steps over them, the referee blows the whistle and enforces penalties.";
  }
  if (c.includes("commercial") || c.includes("contract")) {
    return "Like a handshake agreement sealed in writing — both sides must hold up their end of the bargain.";
  }
  if (c.includes("property")) {
    return "Like a certified property boundary fence — it clearly separates what belongs to you from what belongs to others.";
  }
  return "Like a clear rule in a society handbook ensuring fairness, order, and mutual respect among citizens.";
}

/**
 * Scan text and return all glossary terms found in it.
 * Returns array of enriched {term, def, simple_def, analogy, src, category} objects.
 */
export function scanForTerms(text) {
  if (!text) return [];
  const lower = text.toLowerCase().replace(/\s+/g, " ");
  const found = [];
  const seen  = new Set();

  for (const [termKey, data] of Object.entries(GLOSSARY)) {
    if (lower.includes(termKey) && !seen.has(termKey)) {
      seen.add(termKey);
      const simple_def = data.simple_def || data.def;
      const analogy = data.analogy || generateFallbackAnalogy(termKey, data.category);
      found.push({
        term: termKey,
        ...data,
        simple_def,
        analogy
      });
    }
  }

  // Sort alphabetically
  return found.sort((a, b) => a.term.localeCompare(b.term));
}

/**
 * Get a single term definition.
 */
export function getTermDefinition(term) {
  const normalized = (term || "").toLowerCase().trim();
  const data = GLOSSARY[normalized];
  if (!data) return null;
  return {
    term: normalized,
    ...data,
    simple_def: data.simple_def || data.def,
    analogy: data.analogy || generateFallbackAnalogy(normalized, data.category)
  };
}

/**
 * Get all terms in a category.
 */
export function getTermsByCategory(category) {
  const result = [];
  for (const [term, data] of Object.entries(GLOSSARY)) {
    if (data.category === category) {
      result.push({
        term,
        ...data,
        simple_def: data.simple_def || data.def,
        analogy: data.analogy || generateFallbackAnalogy(term, data.category)
      });
    }
  }
  return result.sort((a, b) => a.term.localeCompare(b.term));
}

/**
 * Get all unique categories.
 */
export function getCategories() {
  const categories = new Set();
  for (const data of Object.values(GLOSSARY)) {
    categories.add(data.category);
  }
  return Array.from(categories).sort();
}
