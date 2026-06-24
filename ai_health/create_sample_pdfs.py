import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

def create_pdf(filename, title, content_list):
    """
    Creates a clean medical PDF document with professional styles.
    """
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    doc = SimpleDocTemplate(filename, pagesize=letter, rightMargin=54, leftMargin=54, topMargin=54, bottomMargin=54)
    story = []
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=colors.HexColor('#1d3557'),
        spaceAfter=15
    )
    
    h1_style = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=18,
        textColor=colors.HexColor('#457b9d'),
        spaceBefore=15,
        spaceAfter=8
    )
    
    body_style = ParagraphStyle(
        'BodyText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#2b2d42'),
        spaceAfter=8
    )
    
    bullet_style = ParagraphStyle(
        'BulletText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#2b2d42'),
        leftIndent=20,
        firstLineIndent=-10,
        spaceAfter=5
    )

    # Document Header
    story.append(Paragraph(title, title_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph("<b>MediCart Clinical Reference Library</b> | Verified Guidelines", bullet_style))
    story.append(Spacer(1, 15))
    
    # Process elements
    for element_type, text in content_list:
        if element_type == 'h1':
            story.append(Paragraph(text, h1_style))
            story.append(Spacer(1, 5))
        elif element_type == 'p':
            story.append(Paragraph(text, body_style))
            story.append(Spacer(1, 5))
        elif element_type == 'bullet':
            story.append(Paragraph(f"&bull; {text}", bullet_style))
            story.append(Spacer(1, 3))
            
    doc.build(story)
    print(f"Generated PDF: {filename}")

def build_all_pdfs():
    docs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'medical_docs')
    
    # 1. Clinical Dosages Guide
    clinical_dosages = [
        ('h1', '1. Analgesics & Antipyretics'),
        ('p', '<b>Paracetamol / Acetaminophen (Dolo 650, Crocin, Calpol)</b>: Standard adult dose is 500mg to 650mg every 4 to 6 hours as needed. Do not exceed 4000mg (4g) within a 24-hour window to prevent acute liver toxicity. Side effects are rare but include skin rash or liver enzyme elevations when overdosed. Avoid combining with alcohol due to heightened hepatotoxicity hazards.'),
        ('p', '<b>Ibuprofen (Brufen 400mg)</b>: Nonsteroidal anti-inflammatory drug (NSAID). Standard adult dosage is 400mg every 6 to 8 hours, preferably taken after meals to avoid gastrointestinal irritation. Maximum daily dose is 1200mg. Commonly causes stomach pain, heartburn, or nausea. Contraindicated in patients with active peptic ulcers, chronic kidney disease, or severe heart failure.'),
        ('h1', '2. Antibiotics'),
        ('p', '<b>Azithromycin (Azithral 500mg)</b>: Broad-spectrum macrolide antibiotic. Typical course is 500mg once daily for 3 to 5 days. Must be taken 1 hour before or 2 hours after meals for optimal absorption. Common side effects: mild diarrhea, nausea, stomach cramps, or temporary hearing changes at high doses. Ensure full compliance to prevent antibiotic resistance.'),
        ('h1', '3. Gastrointestinal Drugs'),
        ('p', '<b>Pantoprazole (Pan-40)</b>: Proton Pump Inhibitor (PPI) that reduces gastric acid production. Recommended dosage is 40mg once daily, taken 30 to 45 minutes before breakfast. Useful for GERD, acid reflux, and stomach ulcers. Long term usage may lead to vitamin B12 or magnesium deficiency.'),
        ('h1', '4. Antidiabetics'),
        ('p', '<b>Metformin 500mg (Glycomet)</b>: Standard initial dose is 500mg once or twice daily with meals to reduce gastrointestinal discomfort. Helps control blood glucose in Type 2 Diabetes. Major risk includes lactic acidosis (rare but severe), presenting as muscle pain, abdominal distress, and drowsiness.')
    ]
    create_pdf(os.path.join(docs_dir, 'clinical_dosages.pdf'), 'Clinical Medicine Dosage & Usage Guide', clinical_dosages)

    # 2. Pregnancy & Pediatrics Safety Guidelines
    pregnancy_pediatrics = [
        ('h1', '1. FDA Pregnancy Risk Categories'),
        ('bullet', '<b>Category A</b>: Controlled human studies show no risk to the fetus in any trimester. (e.g. Levothyroxine, Folic Acid).'),
        ('bullet', '<b>Category B</b>: Animal studies show no fetal risk, but no controlled studies in pregnant women exist, OR animal studies show risk but human studies do not. (e.g. Paracetamol, Metformin, Amoxicillin).'),
        ('bullet', '<b>Category C</b>: Animal studies show adverse effects on fetus, but no human trials are available. Use only if potential benefit outweighs risk. (e.g. Ibuprofen in 1st/2nd trimester, Aspirin, Amlodipine).'),
        ('bullet', '<b>Category D</b>: Positive evidence of human fetal risk based on adverse reaction data, but benefits may warrant use in life-threatening situations. (e.g. Ibuprofen in 3rd trimester - causes premature closure of ductus arteriosus).'),
        ('bullet', '<b>Category X</b>: Studies in animals or humans show definite fetal abnormalities. Contraindicated in pregnancy. (e.g. Atorvastatin, Thalidomide).'),
        ('h1', '2. Child & Pediatric Dosage Calculations'),
        ('p', 'Pediatric doses must be calculated based on body weight (mg/kg) rather than using standard adult dosages. For example, child paracetamol dose is 10-15 mg/kg per dose. Always use a calibrated dosing syringe or spoon for liquid syrups; home teaspoons are highly inaccurate. Keep all medicines locked away out of reach of children.'),
        ('h1', '3. Elderly Care and Geriatric Considerations'),
        ('p', 'Geriatric patients (65+ years) frequently suffer from reduced renal and hepatic clearance. Medication doses must be titrated slowly ("start low and go slow"). Avoid polypharmacy to prevent side effects. Be highly cautious with NSAIDs (Ibuprofen) due to increased risk of acute kidney injury and gastrointestinal bleeding in older patients.')
    ]
    create_pdf(os.path.join(docs_dir, 'pregnancy_and_pediatrics.pdf'), 'Pregnancy & Pediatric Care Guidelines', pregnancy_pediatrics)

    # 3. First Aid Protocols
    first_aid = [
        ('h1', '1. First Aid for Minor Burns'),
        ('bullet', 'Cool the burn immediately by holding the area under cool, running tap water for 10 to 15 minutes. Do NOT use ice, butter, or oil, as this causes tissue damage.'),
        ('bullet', 'Apply a thin layer of <b>Burnol Antiseptic Cream</b> to soothe the skin and prevent bacterial growth.'),
        ('bullet', 'Cover the burn loosely with a sterile non-stick bandage or gauze pads. Do not pop blisters.'),
        ('h1', '2. Managing Open Wounds & Bleeding'),
        ('bullet', 'Apply direct pressure on the wound using a sterile gauze pad or clean cloth until bleeding stops.'),
        ('bullet', 'Clean the wound under running tap water or clean with diluted <b>Dettol Antiseptic Liquid</b>.'),
        ('bullet', 'Apply an antibiotic ointment like <b>Soframycin</b> or <b>Neosporin</b> to maintain moisture and prevent infection.'),
        ('bullet', 'Secure a clean bandage or medical tape over the wound dressing.'),
        ('h1', '3. Insect Bites & Sprains'),
        ('bullet', 'Bites: Wash the area with soap and water, apply Calamine lotion or Clotrimazole cream to soothe itching.'),
        ('bullet', 'Sprains: Use the R.I.C.E protocol: Rest the limb, Ice the injury for 20 mins using an Ice Pack, Compress using an elastic crepe bandage, and Elevate the limb above heart level.')
    ]
    create_pdf(os.path.join(docs_dir, 'first_aid_protocols.pdf'), 'Standard First Aid Emergency Protocols', first_aid)

    # 4. Ayurvedic & Herbal Medicine Reference
    ayurveda = [
        ('h1', '1. Ashwagandha (Withania Somnifera)'),
        ('p', 'An adaptogenic herb that helps the body manage stress. It lowers cortisol levels, improves cognitive function, enhances sleep quality, and supports overall vitality. Standard adult dose is 250mg to 500mg of extract once or twice daily, taken with warm milk or water.'),
        ('h1', '2. Triphala Powder'),
        ('p', 'A traditional blend of three fruits: Amla (Emblica officinalis), Haritaki (Terminalia chebula), and Bibhitaki (Terminalia bellirica). Primarily used for digestive support, colon cleansing, and relieving constipation. Dose is 1/2 to 1 teaspoon of powder with warm water before bedtime.'),
        ('h1', '3. Tulsi (Holy Basil) Drops'),
        ('p', 'Possesses immunomodulatory and anti-inflammatory properties. Extremely useful for cold, sore throat, and respiratory infections. Add 3 to 5 drops of liquid Tulsi extract to warm water or tea twice daily.'),
        ('h1', '4. Neem & Giloy Juice'),
        ('bullet', '<b>Neem Capsules</b>: Purifies blood, supports liver health, and controls inflammatory skin disorders like acne.'),
        ('bullet', '<b>Giloy Juice</b>: Powerful antipyretic and immunomodulator that boosts platelet count during chronic viral fevers.')
    ]
    create_pdf(os.path.join(docs_dir, 'ayurvedic_reference.pdf'), 'Traditional Ayurvedic & Herbal Medicine Guide', ayurveda)

    # 5. Drug Interactions & Safety Charts
    interactions = [
        ('h1', '1. Severe Drug Interactions (Contraindicated)'),
        ('bullet', '<b>Aspirin + Ibuprofen</b>: Concurrent usage significantly increases the risk of gastrointestinal ulcers and internal bleeding. Ibuprofen also blocks the anti-platelet cardio-protective benefits of low-dose aspirin.'),
        ('bullet', '<b>Paracetamol + Alcohol</b>: Regular alcohol intake induces CYP2E1 liver enzymes, leading to rapid accumulation of hepatotoxic NAPQI metabolites from paracetamol, triggering acute liver failure.'),
        ('bullet', '<b>Metformin + Contrast Dye</b>: Patients undergoing CT scans or contrast imaging must temporarily suspend metformin for 48 hours to avoid severe lactic acidosis.'),
        ('h1', '2. Moderate Drug Interactions'),
        ('bullet', '<b>Ciprofloxacin + Calcium</b>: Calcium carbonates (found in dairy, wellness supplements) bind to ciprofloxacin in the gut, reducing antibiotic absorption and clinical efficacy by up to 40%. Separate administration by at least 2 hours.'),
        ('bullet', '<b>Pantoprazole + Iron</b>: Reduced stomach acid due to PPIs decreases the body\'s absorption of oral iron supplements, requiring higher doses or alternative IV options.')
    ]
    create_pdf(os.path.join(docs_dir, 'drug_interactions_reference.pdf'), 'Drug-to-Drug Interactions & Safety Reference', interactions)

if __name__ == '__main__':
    build_all_pdfs()
