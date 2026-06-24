import os
import django
import random
import datetime
import hashlib
import json
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from django.core.files.base import ContentFile

# Setup Django Environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'medicart_project.settings')
django.setup()

from store.models import Category, Medicine, PositiveThought, DrugInteraction
from orders.models import BlockchainBlock
from django.contrib.auth import get_user_model

User = get_user_model()

def calculate_hash(index, timestamp, data, previous_hash):
    value = str(index) + str(timestamp) + str(data) + str(previous_hash)
    return hashlib.sha256(value.encode('utf-8')).hexdigest()

def seed_blockchain():
    print("Seeding Blockchain Authenticity Ledger...")
    BlockchainBlock.objects.all().delete()
    
    # Create Genesis Block
    genesis_data = json.dumps({
        "message": "MediCart Blockchain Ledger Initialized",
        "authority": "Global Pharmacy Verification Council"
    })
    genesis_timestamp = datetime.datetime.now()
    genesis_hash = calculate_hash(0, genesis_timestamp, genesis_data, "0")
    
    block_0 = BlockchainBlock.objects.create(
        index=0,
        data=genesis_data,
        previous_hash="0",
        hash=genesis_hash
    )
    block_0.timestamp = genesis_timestamp
    block_0.save()

    # Create drug batch verification blocks
    batches = [
        {"batch": "BATCH-TAB01", "drug": "Paracetamol 500mg", "manufacturer": "GlaxoSmithKline", "status": "FDA Approved", "purity": "99.8%"},
        {"batch": "BATCH-TAB02", "drug": "Dolo 650", "manufacturer": "Micro Labs", "status": "FDA Approved", "purity": "99.4%"},
        {"batch": "BATCH-SYR01", "drug": "Benadryl Syrup", "manufacturer": "Johnson & Johnson", "status": "FDA Approved", "purity": "98.7%"},
        {"batch": "BATCH-OIN01", "drug": "Burnol", "manufacturer": "Morepen", "status": "FDA Approved", "purity": "99.1%"}
    ]
    
    prev_hash = genesis_hash
    for idx, batch in enumerate(batches, start=1):
        batch_data = json.dumps(batch)
        block_time = datetime.datetime.now() - datetime.timedelta(days=10 - idx)
        block_hash = calculate_hash(idx, block_time, batch_data, prev_hash)
        
        block = BlockchainBlock.objects.create(
            index=idx,
            data=batch_data,
            previous_hash=prev_hash,
            hash=block_hash
        )
        block.timestamp = block_time
        block.save()
        prev_hash = block_hash
    print(f"Seeded {len(batches) + 1} blocks in authenticity chain.")

def generate_medicine_label_image(category_name, med_name, brand, generic, ingredient, batch, rx_required):
    """
    Creates an 800x400 composite image.
    Left side (400x400): Loaded base image for the category.
    Right side (400x400): A dynamically rendered medical label containing specific details.
    """
    # 1. Load base category image
    base_dir = os.path.dirname(os.path.abspath(__file__))
    cat_slug = category_name.lower().replace(' ', '_')
    base_img_path = os.path.join(base_dir, 'static', 'images', 'base', f"{cat_slug}_base.png")
    
    # Try to load base image, fallback to a blank canvas if missing
    if os.path.exists(base_img_path):
        try:
            left_img = Image.open(base_img_path).convert('RGB')
        except Exception as e:
            print(f"Error opening base image {base_img_path}: {e}")
            left_img = Image.new('RGB', (400, 400), color='#f0f2f5')
    else:
        left_img = Image.new('RGB', (400, 400), color='#f0f2f5')
        
    left_img = left_img.resize((400, 400), Image.Resampling.LANCZOS)
    
    # 2. Create the label canvas (right side, 400x400)
    right_img = Image.new('RGB', (400, 400), color='#ffffff')
    draw = ImageDraw.Draw(right_img)
    
    # Draw gray card outline inside right panel
    draw.rectangle([10, 10, 390, 390], outline='#e5e5e5', width=2)
    
    # Draw banner color based on category/dosage form
    banner_color = '#0077b6' # default blue
    if category_name == 'Tablet': banner_color = '#7b2cbf'
    elif category_name == 'Syrup': banner_color = '#d90429'
    elif category_name == 'Ointment': banner_color = '#38b000'
    elif category_name == 'First Aid': banner_color = '#ffb703'
    elif category_name == 'Pet Care': banner_color = '#fb8500'
    elif category_name == 'Syringes': banner_color = '#2ec4b6'
    elif category_name == 'Injections': banner_color = '#00f5d4'
    elif category_name == 'Wellness': banner_color = '#9b5de5'
    elif category_name == 'Baby Care': banner_color = '#ff9f1c'
    elif category_name == 'Ayurveda': banner_color = '#606c38'
    
    # Draw Banner
    draw.rectangle([12, 12, 388, 55], fill=banner_color)
    
    # Load fonts safely (Arial is guaranteed on macOS, fall back to default if not found)
    try:
        font_title = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 18)
        font_sub = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 13)
        font_body = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 11)
        font_bold = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 11)
        font_rx = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 12)
    except:
        font_title = font_sub = font_body = font_bold = font_rx = ImageFont.load_default()
        
    # Write banner title
    draw.text((25, 22), "MEDICART PHARMACEUTICALS", fill="#ffffff", font=font_sub)
    
    # Write Medicine Name
    # Simple word wrap for medicine name if too long
    name_lines = []
    words = med_name.split()
    current_line = ""
    for w in words:
        if len(current_line + " " + w) < 22:
            current_line = current_line + " " + w if current_line else w
        else:
            name_lines.append(current_line)
            current_line = w
    if current_line:
        name_lines.append(current_line)
        
    y_pos = 80
    for line in name_lines[:2]:
        draw.text((25, y_pos), line, fill="#1d3557", font=font_title)
        y_pos += 24
        
    # Draw a divider line
    draw.line([25, y_pos + 5, 365, y_pos + 5], fill="#e5e5e5", width=1)
    y_pos += 15
    
    # Draw generic, brand, active ingredients
    draw.text((25, y_pos), f"Generic:", fill="#6c757d", font=font_body)
    draw.text((95, y_pos), generic[:40], fill="#1d3557", font=font_bold)
    y_pos += 20
    
    draw.text((25, y_pos), f"Brand:", fill="#6c757d", font=font_body)
    draw.text((95, y_pos), brand, fill="#1d3557", font=font_bold)
    y_pos += 20
    
    draw.text((25, y_pos), f"Active Ingredient:", fill="#6c757d", font=font_body)
    draw.text((135, y_pos), ingredient, fill="#1d3557", font=font_bold)
    y_pos += 20
    
    draw.text((25, y_pos), f"Dosage Form:", fill="#6c757d", font=font_body)
    draw.text((110, y_pos), category_name, fill="#1d3557", font=font_bold)
    y_pos += 20
    
    draw.text((25, y_pos), f"Batch Code:", fill="#6c757d", font=font_body)
    draw.text((110, y_pos), batch, fill="#1d3557", font=font_bold)
    y_pos += 25
    
    # Draw Rx or OTC Badge
    if rx_required:
        draw.rectangle([25, y_pos, 150, y_pos + 22], fill="#e63946")
        draw.text((35, y_pos + 4), "Rx ONLY (Prescription Required)", fill="#ffffff", font=font_rx)
    else:
        draw.rectangle([25, y_pos, 120, y_pos + 22], fill="#38b000")
        draw.text((35, y_pos + 4), "OTC (Over-The-Counter)", fill="#ffffff", font=font_rx)
        
    y_pos += 35
    
    # Draw warning/storage
    draw.text((25, y_pos), "Storage: Store in a dry place under 30C. Keep away from kids.", fill="#a29bfe" if category_name == 'Tablet' else "#6c757d", font=font_body)
    y_pos += 20
    
    # Draw mock barcode
    start_x = 25
    random.seed(len(med_name)) # deterministic barcode per medicine
    for _ in range(35):
        width = random.choice([1, 2, 3])
        draw.rectangle([start_x, y_pos, start_x + width, y_pos + 20], fill="black")
        start_x += width + random.choice([1, 2])
        
    draw.text((start_x + 10, y_pos + 4), f"VERIFIED: {batch}", fill="#1d3557", font=font_body)
    
    # 3. Assemble composite image
    composite_image = Image.new('RGB', (800, 400), color='#ffffff')
    composite_image.paste(left_img, (0, 0))
    composite_image.paste(right_img, (400, 0))
    
    return composite_image

def populate():
    print("Seeding 100 Medicines across 10 categories with custom-labeled PIL images...")

    # Clear existing data to prevent duplicates
    Medicine.objects.all().delete()
    Category.objects.all().delete()
    DrugInteraction.objects.all().delete()
    PositiveThought.objects.all().delete()

    # 10 Required Categories
    categories = [
        'Tablet', 'Syrup', 'Ointment', 'First Aid', 'Pet Care', 'Syringes', 'Injections', 'Wellness', 'Baby Care', 'Ayurveda'
    ]
    
    cat_objects = {}
    for name in categories:
        slug = name.lower().replace(' ', '-')
        c = Category.objects.create(name=name, slug=slug)
        cat_objects[name] = c

    # Defined 100 Medicines (10 per category)
    medicines_data = {
        'Tablet': [
            {'name': 'Paracetamol 500mg', 'brand': 'Crocin', 'generic': 'Paracetamol 500mg', 'ingredient': 'paracetamol', 'price': 20.00, 'rx': False, 'desc': 'Fever reducer and analgesic.'},
            {'name': 'Dolo 650', 'brand': 'Micro Labs', 'generic': 'Paracetamol 650mg', 'ingredient': 'paracetamol', 'price': 30.00, 'rx': False, 'desc': 'Effective fever treatment.'},
            {'name': 'Crocin Pain Relief', 'brand': 'GlaxoSmithKline', 'generic': 'Paracetamol + Caffeine', 'ingredient': 'paracetamol', 'price': 40.00, 'rx': False, 'desc': 'Fast relief for head and body pain.'},
            {'name': 'Aspirin', 'brand': 'Bayer', 'generic': 'Acetylsalicylic Acid 325mg', 'ingredient': 'aspirin', 'price': 50.00, 'rx': True, 'desc': 'Pain, inflammation, and fever reducer.'},
            {'name': 'Metformin 500mg', 'brand': 'Glycomet', 'generic': 'Metformin Hydrochloride', 'ingredient': 'metformin', 'price': 80.00, 'rx': True, 'desc': 'Antidiabetic medication to manage blood sugar.'},
            {'name': 'Azithromycin 500mg', 'brand': 'Azithral', 'generic': 'Azithromycin Dihydrate', 'ingredient': 'azithromycin', 'price': 120.00, 'rx': True, 'desc': 'Broad-spectrum antibiotic.'},
            {'name': 'Cetirizine 10mg', 'brand': 'Alerid', 'generic': 'Cetirizine Hydrochloride', 'ingredient': 'cetirizine', 'price': 25.00, 'rx': False, 'desc': 'Effective non-drowsy allergy relief.'},
            {'name': 'Vitamin C 500mg', 'brand': 'Limcee', 'generic': 'Ascorbic Acid', 'ingredient': 'vitamin c', 'price': 35.00, 'rx': False, 'desc': 'Daily immunity booster.'},
            {'name': 'Ibuprofen 400mg', 'brand': 'Brufen', 'generic': 'Ibuprofen', 'ingredient': 'ibuprofen', 'price': 30.00, 'rx': False, 'desc': 'Nonsteroidal anti-inflammatory drug (NSAID).'},
            {'name': 'Pantoprazole 40mg', 'brand': 'Pan-40', 'generic': 'Pantoprazole Sodium', 'ingredient': 'pantoprazole', 'price': 90.00, 'rx': True, 'desc': 'Reduces stomach acid to treat GERD.'}
        ],
        'Syrup': [
            {'name': 'Benadryl Syrup', 'brand': 'Johnson & Johnson', 'generic': 'Diphenhydramine + Ammonium Chloride', 'ingredient': 'diphenhydramine', 'price': 120.00, 'rx': False, 'desc': 'Soothes dry cough and throat irritation.'},
            {'name': 'Ascoril Syrup', 'brand': 'Glenmark', 'generic': 'Terbutaline + Bromhexine + Guaiphenesin', 'ingredient': 'bromhexine', 'price': 135.00, 'rx': True, 'desc': 'Clears wet cough and respiratory mucus.'},
            {'name': 'Cofsils Syrup', 'brand': 'Cipla', 'generic': 'Dextromethorphan + Chlorpheniramine', 'ingredient': 'dextromethorphan', 'price': 85.00, 'rx': False, 'desc': 'Effective relief for dry cough.'},
            {'name': 'Ambroxol Syrup', 'brand': 'Ambrolite', 'generic': 'Ambroxol Hydrochloride', 'ingredient': 'ambroxol', 'price': 95.00, 'rx': False, 'desc': 'Mucolytic cough syrup.'},
            {'name': 'Liv 52 Syrup', 'brand': 'Himalaya', 'generic': 'Herbal Liver Tonic', 'ingredient': 'herbal extract', 'price': 150.00, 'rx': False, 'desc': 'Protects and supports liver health.'},
            {'name': 'Zincovit Syrup', 'brand': 'Apex', 'generic': 'Multivitamin + Zinc', 'ingredient': 'multivitamins', 'price': 130.00, 'rx': False, 'desc': 'Nutritional syrup for children and adults.'},
            {'name': 'Iron Syrup', 'brand': 'Dexorange', 'generic': 'Ferric Ammonium Citrate + Folic Acid', 'ingredient': 'iron', 'price': 160.00, 'rx': False, 'desc': 'Supports hemoglobin levels.'},
            {'name': 'Vitamin Syrup', 'brand': 'A to Z', 'generic': 'Multivitamin & Mineral Syrup', 'ingredient': 'multivitamins', 'price': 110.00, 'rx': False, 'desc': 'Supports growth and vitality.'},
            {'name': 'Pediatric Cough Syrup', 'brand': 'Maxtra', 'generic': 'Phenylephrine + Chlorpheniramine', 'ingredient': 'chlorpheniramine', 'price': 90.00, 'rx': True, 'desc': 'Safe cold and cough relief for kids.'},
            {'name': 'Digestive Syrup', 'brand': 'Aristozyme', 'generic': 'Diastase + Pepsin', 'ingredient': 'pepsin', 'price': 105.00, 'rx': False, 'desc': 'Supports digestion and relieves bloating.'}
        ],
        'Ointment': [
            {'name': 'Burnol', 'brand': 'Morepen', 'generic': 'Aminacrine + Cetrimide', 'ingredient': 'cetrimide', 'price': 70.00, 'rx': False, 'desc': 'Antiseptic cream for minor burns.'},
            {'name': 'Soframycin', 'brand': 'Sanofi', 'generic': 'Framycetin Sulfate', 'ingredient': 'framycetin', 'price': 55.00, 'rx': False, 'desc': 'First-aid skin cream for cuts and wounds.'},
            {'name': 'Betnovate', 'brand': 'GlaxoSmithKline', 'generic': 'Betamethasone Valerate', 'ingredient': 'betamethasone', 'price': 45.00, 'rx': True, 'desc': 'Steroid cream for eczema and skin rashes.'},
            {'name': 'Boroline', 'brand': 'GD Pharmaceuticals', 'generic': 'Zinc Oxide + Boric Acid', 'ingredient': 'zinc oxide', 'price': 50.00, 'rx': False, 'desc': 'Antiseptic skin cream for dry skin and cuts.'},
            {'name': 'Clotrimazole Cream', 'brand': 'Canesten', 'generic': 'Clotrimazole 1%', 'ingredient': 'clotrimazole', 'price': 90.00, 'rx': False, 'desc': 'Broad-spectrum antifungal cream.'},
            {'name': 'Neosporin', 'brand': 'Johnson & Johnson', 'generic': 'Neomycin + Polymyxin + Bacitracin', 'ingredient': 'neomycin', 'price': 110.00, 'rx': False, 'desc': 'Triple antibiotic ointment.'},
            {'name': 'Antifungal Cream', 'brand': 'Lulifin', 'generic': 'Luliconazole 1%', 'ingredient': 'luliconazole', 'price': 180.00, 'rx': True, 'desc': 'Powerful cream for fungal skin infections.'},
            {'name': 'Pain Relief Gel', 'brand': 'Volini', 'generic': 'Diclofenac Diethylamine + Menthol', 'ingredient': 'diclofenac', 'price': 125.00, 'rx': False, 'desc': 'Relieves joint and muscle pain quickly.'},
            {'name': 'Antiseptic Cream', 'brand': 'BoroPlus', 'generic': 'Herbal Antiseptic Ointment', 'ingredient': 'zinc oxide', 'price': 40.00, 'rx': False, 'desc': 'Moisturizes and heals skin cuts.'},
            {'name': 'Moisturizing Cream', 'brand': 'Cetaphil', 'generic': 'Intense Hydrating Cream', 'ingredient': 'glycerin', 'price': 450.00, 'rx': False, 'desc': 'Dermatologist recommended for sensitive skin.'}
        ],
        'First Aid': [
            {'name': 'Bandage', 'brand': 'Band-Aid', 'generic': 'Sterile Adhesive Strips', 'ingredient': 'n/a', 'price': 20.00, 'rx': False, 'desc': 'Protects minor cuts and wounds.'},
            {'name': 'Cotton Roll', 'brand': 'Dignity', 'generic': 'Absorbent Cotton Wool', 'ingredient': 'n/a', 'price': 45.00, 'rx': False, 'desc': 'Highly absorbent sterile cotton roll.'},
            {'name': 'Antiseptic Liquid', 'brand': 'Dettol', 'generic': 'Chloroxylenol Antiseptic', 'ingredient': 'chloroxylenol', 'price': 65.00, 'rx': False, 'desc': 'Wound wash and general sanitizing.'},
            {'name': 'Medical Tape', 'brand': '3M Micropore', 'generic': 'Surgical Paper Tape', 'ingredient': 'n/a', 'price': 55.00, 'rx': False, 'desc': 'Hypoallergenic tape for dressing gauze.'},
            {'name': 'Thermometer', 'brand': 'Dr. Trust', 'generic': 'Digital Thermometer', 'ingredient': 'n/a', 'price': 250.00, 'rx': False, 'desc': 'Fast and accurate body temperature reading.'},
            {'name': 'Hot Water Bag', 'brand': 'Equinox', 'generic': 'Rubber Heat Therapy Bottle', 'ingredient': 'n/a', 'price': 350.00, 'rx': False, 'desc': 'Relieves muscular spasms and back pain.'},
            {'name': 'Gauze Pads', 'brand': 'Dettol Sterile', 'generic': 'Sterile Cotton Gauze Swabs', 'ingredient': 'n/a', 'price': 30.00, 'rx': False, 'desc': 'Sterile dressing for wound care.'},
            {'name': 'Ice Pack', 'brand': 'Flamingo', 'generic': 'Gel Ice Compression Pack', 'ingredient': 'n/a', 'price': 180.00, 'rx': False, 'desc': 'Reduces swelling and joint inflammation.'},
            {'name': 'Gloves', 'brand': 'Romsons', 'generic': 'Sterile Latex Examination Gloves', 'ingredient': 'n/a', 'price': 150.00, 'rx': False, 'desc': 'Powdered examination gloves for safety.'},
            {'name': 'Scissors', 'brand': 'Apex Medical', 'generic': 'Stainless Steel Surgical Scissors', 'ingredient': 'n/a', 'price': 80.00, 'rx': False, 'desc': 'Blunt tip bandage cutting scissors.'}
        ],
        'Pet Care': [
            {'name': 'Dog Multivitamin', 'brand': 'PetUp', 'generic': 'Canine Essential Vitamins', 'ingredient': 'multivitamins', 'price': 320.00, 'rx': False, 'desc': 'Supports joint, coat, and immunity.'},
            {'name': 'Cat Deworming Tablet', 'brand': 'Drontal Plus', 'generic': 'Praziquantel + Pyrantel', 'ingredient': 'praziquantel', 'price': 150.00, 'rx': False, 'desc': 'Treats hookworms and tapeworms in cats.'},
            {'name': 'Pet Shampoo', 'brand': 'Himalaya Erina', 'generic': 'Anti-Dandruff & Tick Shampoo', 'ingredient': 'neem', 'price': 200.00, 'rx': False, 'desc': 'Cleans and keeps ticks away.'},
            {'name': 'Pet Skin Cream', 'brand': 'Kiskin', 'generic': 'Clobetasol + Miconazole', 'ingredient': 'miconazole', 'price': 110.00, 'rx': False, 'desc': 'Heals dog fungal skin infections.'},
            {'name': 'Tick Spray', 'brand': 'Fiprofort', 'generic': 'Fipronil Spray', 'ingredient': 'fipronil', 'price': 450.00, 'rx': False, 'desc': 'Kills ticks and fleas on contact.'},
            {'name': 'Pet Calcium Supplement', 'brand': 'SkyCal', 'generic': 'Calcium + Phosphorus for Pets', 'ingredient': 'calcium', 'price': 280.00, 'rx': False, 'desc': 'Supports bone health in puppies.'},
            {'name': 'Pet Ear Drops', 'brand': 'Oticlene', 'generic': 'Chlorhexidine Ear Cleanser', 'ingredient': 'chlorhexidine', 'price': 140.00, 'rx': False, 'desc': 'Prevents ear infections and removes wax.'},
            {'name': 'Pet Food Supplement', 'brand': 'Vetoquinol', 'generic': 'Nutri-Plus High Energy Paste', 'ingredient': 'multivitamins', 'price': 490.00, 'rx': False, 'desc': 'Nutritious paste for recovering pets.'},
            {'name': 'Pet Syrup', 'brand': 'Himalaya Digyton', 'generic': 'Digestive Tonic for Dogs & Cats', 'ingredient': 'herbal extract', 'price': 120.00, 'rx': False, 'desc': 'Relieves flatulence and indigestion.'},
            {'name': 'Pet Wound Spray', 'brand': 'D-Mag', 'generic': 'Gamma Benzene + Propetmpis', 'ingredient': 'herbal extract', 'price': 160.00, 'rx': False, 'desc': 'Heals maggots and septic wounds.'}
        ],
        'Syringes': [
            {'name': '1ml Syringe', 'brand': 'Dispovan', 'generic': '1ml Disposable Syringe with Needle', 'ingredient': 'n/a', 'price': 8.00, 'rx': False, 'desc': 'Surgical 1ml syringe for precise dose.'},
            {'name': '2ml Syringe', 'brand': 'Dispovan', 'generic': '2ml Luer Slip Syringe with Needle', 'ingredient': 'n/a', 'price': 10.00, 'rx': False, 'desc': 'General purpose 2ml disposable syringe.'},
            {'name': '5ml Syringe', 'brand': 'Dispovan', 'generic': '5ml Luer Lock Syringe with Needle', 'ingredient': 'n/a', 'price': 12.00, 'rx': False, 'desc': 'Lock design prevents needle pop-off.'},
            {'name': '10ml Syringe', 'brand': 'Dispovan', 'generic': '10ml Surgical Syringe', 'ingredient': 'n/a', 'price': 18.00, 'rx': False, 'desc': 'Used for larger injections and flushes.'},
            {'name': 'Insulin Syringe', 'brand': 'BD Ultra-Fine', 'generic': '31G U-100 Insulin Syringe 0.5ml', 'ingredient': 'n/a', 'price': 22.00, 'rx': False, 'desc': 'Short, fine needle for pain-free injection.'},
            {'name': 'Disposable Syringe', 'brand': 'Lifelong', 'generic': 'Sterile Dispo Syringe 3ml', 'ingredient': 'n/a', 'price': 9.00, 'rx': False, 'desc': 'Single use sterile syringe.'},
            {'name': 'Safety Syringe', 'brand': 'Romsons Safety', 'generic': 'Retractable Needle Safety Syringe', 'ingredient': 'n/a', 'price': 35.00, 'rx': False, 'desc': 'Needle retracts after use to prevent injury.'},
            {'name': 'Tuberculin Syringe', 'brand': 'BD Tuberculin', 'generic': '1ml TB Syringe 26G', 'ingredient': 'n/a', 'price': 25.00, 'rx': False, 'desc': 'Used for intradermal skin tests.'},
            {'name': 'Luer Lock Syringe', 'brand': 'B.Braun Luer Lock', 'generic': 'Luer Lock Syringe 20ml', 'ingredient': 'n/a', 'price': 40.00, 'rx': False, 'desc': 'Locking mechanism syringe for IV line.'},
            {'name': 'Needle Set', 'brand': 'Dispovan Needles', 'generic': '24G Hypodermic Sterile Needles', 'ingredient': 'n/a', 'price': 30.00, 'rx': False, 'desc': 'Pack of 10 disposable sterile needles.'}
        ],
        'Injections': [
            {'name': 'Insulin Injection', 'brand': 'Lantus', 'generic': 'Insulin Glargine 100 IU/ml', 'ingredient': 'insulin', 'price': 650.00, 'rx': True, 'desc': 'Long-acting basal insulin for diabetes.'},
            {'name': 'Vitamin B12 Injection', 'brand': 'Nervz-G', 'generic': 'Methylcobalamin 1500mcg', 'ingredient': 'vitamin b12', 'price': 80.00, 'rx': True, 'desc': 'Treats neuropathy and B12 deficiencies.'},
            {'name': 'Diclofenac Injection', 'brand': 'Dynapar AQ', 'generic': 'Diclofenac Sodium 75mg/1ml', 'ingredient': 'diclofenac', 'price': 45.00, 'rx': True, 'desc': 'Instant relief for severe joint/muscle pain.'},
            {'name': 'Ceftriaxone Injection', 'brand': 'Monocef 1g', 'generic': 'Ceftriaxone Sodium 1g', 'ingredient': 'ceftriaxone', 'price': 65.00, 'rx': True, 'desc': 'Power cephalosporin antibiotic injection.'},
            {'name': 'Tetanus Injection', 'brand': 'Bett 0.5ml', 'generic': 'Tetanus Toxoid Vaccine', 'ingredient': 'tetanus vaccine', 'price': 40.00, 'rx': False, 'desc': 'Protects against lockjaw infection.'},
            {'name': 'Rabies Vaccine', 'brand': 'Rabipur', 'generic': 'Purified Chick Embryo Cell Vaccine', 'ingredient': 'rabies vaccine', 'price': 350.00, 'rx': True, 'desc': 'Post-exposure immunization against Rabies.'},
            {'name': 'Dexamethasone Injection', 'brand': 'Decadron', 'generic': 'Dexamethasone Sodium Phosphate', 'ingredient': 'dexamethasone', 'price': 35.00, 'rx': True, 'desc': 'Steroid injection to treat inflammation/allergies.'},
            {'name': 'Iron Injection', 'brand': 'Orofer FCM', 'generic': 'Ferric Carboxymaltose Injection', 'ingredient': 'iron', 'price': 2200.00, 'rx': True, 'desc': 'Treats severe iron deficiency anemia.'},
            {'name': 'Calcium Injection', 'brand': 'Calcium Sandoz', 'generic': 'Calcium Gluconate 10%', 'ingredient': 'calcium', 'price': 60.00, 'rx': True, 'desc': 'Treats severe hypocalcemia.'},
            {'name': 'Saline Injection', 'brand': 'N.S. Flush', 'generic': '0.9% Sodium Chloride IV Flush', 'ingredient': 'n/a', 'price': 25.00, 'rx': True, 'desc': 'Sterile saline IV line flusher.'}
        ],
        'Wellness': [
            {'name': 'Multivitamins', 'brand': 'Revital H', 'generic': 'Daily Multivitamins + Ginseng', 'ingredient': 'multivitamins', 'price': 300.00, 'rx': False, 'desc': 'Increases energy levels and mental focus.'},
            {'name': 'Protein Powder', 'brand': 'Ensure', 'generic': 'Nutritional Shake Powder', 'ingredient': 'protein', 'price': 750.00, 'rx': False, 'desc': 'Balanced meal replacement for muscle strength.'},
            {'name': 'Omega 3 Capsules', 'brand': 'TrueBasics', 'generic': 'Fish Oil Triple Strength', 'ingredient': 'omega 3', 'price': 650.00, 'rx': False, 'desc': 'Supports heart, brain, and joint mobility.'},
            {'name': 'Calcium Tablets', 'brand': 'Shelcal 500', 'generic': 'Calcium + Vitamin D3', 'ingredient': 'calcium', 'price': 110.00, 'rx': False, 'desc': 'Supports bone density and calcium levels.'},
            {'name': 'Fish Oil', 'brand': 'Wow Life Science', 'generic': 'Pure Salmon Fish Oil 1000mg', 'ingredient': 'omega 3', 'price': 490.00, 'rx': False, 'desc': 'Rich in EPA and DHA fatty acids.'},
            {'name': 'Energy Drinks', 'brand': 'Red Bull', 'generic': 'Caffeinated Vitalizing Drink', 'ingredient': 'caffeine', 'price': 120.00, 'rx': False, 'desc': 'Quick mental and physical energy boost.'},
            {'name': 'Electrolyte Powder', 'brand': 'Electral', 'generic': 'WHO Oral Rehydration Salts', 'ingredient': 'electrolytes', 'price': 22.00, 'rx': False, 'desc': 'Restores body salts during dehydration.'},
            {'name': 'Probiotics', 'brand': 'GutGlow', 'generic': 'Lactobacillus Acidophilus Capsules', 'ingredient': 'probiotics', 'price': 350.00, 'rx': False, 'desc': 'Supports healthy digestion and gut flora.'},
            {'name': 'Immunity Booster', 'brand': 'Giloy Capsules', 'generic': 'Tinospora Cordifolia Extract', 'ingredient': 'giloy', 'price': 180.00, 'rx': False, 'desc': 'Boosts natural white blood cell defense.'},
            {'name': 'Green Tea Extract', 'brand': 'Organic India', 'generic': 'Antioxidant Green Tea Capsules', 'ingredient': 'green tea', 'price': 220.00, 'rx': False, 'desc': 'Supports metabolism and cellular health.'}
        ],
        'Baby Care': [
            {'name': 'Baby Lotion', 'brand': 'Johnson\'s Baby', 'generic': 'Gentle Baby Moisturizer', 'ingredient': 'glycerin', 'price': 160.00, 'rx': False, 'desc': 'Locks moisture to keep baby skin soft.'},
            {'name': 'Baby Powder', 'brand': 'Himalaya Baby', 'generic': 'Herbal Cooling Powder', 'ingredient': 'herbal extract', 'price': 120.00, 'rx': False, 'desc': 'Prevents diaper rash and absorbs wetness.'},
            {'name': 'Baby Shampoo', 'brand': 'Sebamed', 'generic': 'No Tears Baby Shampoo', 'ingredient': 'glycerin', 'price': 320.00, 'rx': False, 'desc': 'Ph 5.5 clinically tested baby hair care.'},
            {'name': 'Baby Soap', 'brand': 'Seba Soap', 'generic': 'Ultra Mild Baby Cleansing Bar', 'ingredient': 'glycerin', 'price': 110.00, 'rx': False, 'desc': 'Keeps delicate baby skin moist.'},
            {'name': 'Baby Diapers', 'brand': 'Pampers Active', 'generic': 'High Absorbent Diaper Pants M-size', 'ingredient': 'n/a', 'price': 699.00, 'rx': False, 'desc': 'Locks wetness up to 12 hours.'},
            {'name': 'Baby Wipes', 'brand': 'Mother Sparsh', 'generic': '99% Pure Water Unscented Wipes', 'ingredient': 'n/a', 'price': 199.00, 'rx': False, 'desc': 'Gentle cleaning for face and hands.'},
            {'name': 'Baby Oil', 'brand': 'Figaro Baby', 'generic': 'Pure Olive Oil for Massage', 'ingredient': 'olive oil', 'price': 280.00, 'rx': False, 'desc': 'Nourishes bones and muscles.'},
            {'name': 'Feeding Bottle', 'brand': 'Philips Avent', 'generic': 'Anti-Colic Feeding Bottle 260ml', 'ingredient': 'n/a', 'price': 450.00, 'rx': False, 'desc': 'Venting design prevents colic and gas.'},
            {'name': 'Baby Cream', 'brand': 'Cetaphil Baby', 'generic': 'Organic Calendula Diaper Cream', 'ingredient': 'calendula', 'price': 380.00, 'rx': False, 'desc': 'Instantly heals diaper rash inflammation.'},
            {'name': 'Baby Thermometer', 'brand': 'Chicco Digital', 'generic': 'Soft Tip Baby Thermometer', 'ingredient': 'n/a', 'price': 399.00, 'rx': False, 'desc': 'Comfortable measurement for infants.'}
        ],
        'Ayurveda': [
            {'name': 'Ashwagandha', 'brand': 'Pat整体', 'generic': 'Withania Somnifera Extract 500mg', 'ingredient': 'ashwagandha', 'price': 180.00, 'rx': False, 'desc': 'Powerful adaptogen for anxiety and fatigue.'},
            {'name': 'Triphala Powder', 'brand': 'Dabur', 'generic': 'Amla + Haritaki + Bibhitaki Powder', 'ingredient': 'triphala', 'price': 90.00, 'rx': False, 'desc': 'Promotes bowel health and colon cleanse.'},
            {'name': 'Tulsi Drops', 'brand': 'Sri Sri Tattva', 'generic': 'Pancha Tulsi Liquid Extract', 'ingredient': 'tulsi', 'price': 120.00, 'rx': False, 'desc': 'Liquid immunity booster drops for cold.'},
            {'name': 'Chyawanprash', 'brand': 'Dabur Special', 'generic': 'Amla & Herbal Extract Elixir', 'ingredient': 'amla', 'price': 340.00, 'rx': False, 'desc': 'Traditional winter family health booster.'},
            {'name': 'Neem Capsules', 'brand': 'Himalaya Neem', 'generic': 'Azadirachta Indica Leaf Extract', 'ingredient': 'neem', 'price': 160.00, 'rx': False, 'desc': 'Purifies blood and controls acne.'},
            {'name': 'Giloy Juice', 'brand': 'Baidyanath', 'generic': 'Tinospora Cordifolia Juice', 'ingredient': 'giloy', 'price': 220.00, 'rx': False, 'desc': 'Purges toxins and builds chronic fever resistance.'},
            {'name': 'Brahmi Tablets', 'brand': 'Himalaya Brahmi', 'generic': 'Bacopa Monnieri Extract', 'ingredient': 'brahmi', 'price': 175.00, 'rx': False, 'desc': 'Improves focus, cognitive health, and memory.'},
            {'name': 'Amla Juice', 'brand': 'Kapiva', 'generic': 'Cold Pressed Amla Juice', 'ingredient': 'amla', 'price': 240.00, 'rx': False, 'desc': 'Rich source of Vitamin C and digestives.'},
            {'name': 'Herbal Tea', 'brand': 'Organic India', 'generic': 'Tulsi Ginger Caffeine-Free Tea', 'ingredient': 'tulsi', 'price': 190.00, 'rx': False, 'desc': 'De-stresses and protects against cold.'},
            {'name': 'Digestive Powder', 'brand': 'Pachanol', 'generic': 'Hing + Cumin Digestive Churna', 'ingredient': 'hing', 'price': 75.00, 'rx': False, 'desc': 'Relieves acidity, gas, and stomach ache.'}
        ]
    }

    # Helper indices for batch codes and locations
    batch_idx = 100
    for cat_name, items in medicines_data.items():
        cat = cat_objects[cat_name]
        for idx, item in enumerate(items, start=1):
            batch_idx += 1
            batch_code = f"BATCH-{cat_name[:3].upper()}{batch_idx}"
            row = chr(65 + (batch_idx % 6)) # Rows A to F
            shelf = (batch_idx % 4) + 1
            location = f"Row {row} / Shelf {shelf}"
            
            med = Medicine.objects.create(
                category=cat,
                name=item['name'],
                brand_name=item['brand'],
                generic_name=item['generic'],
                active_ingredient=item['ingredient'].lower(),
                price=item['price'],
                original_price=item['price'],
                discount_percent=random.choice([0, 5, 10, 15, 20, 25]),
                is_featured=random.choice([True, False, False, False]),
                rating=round(random.uniform(3.9, 4.9), 1),
                review_count=random.randint(12, 190),
                medicine_type=cat_name.lower(),
                stock=random.randint(20, 180),
                expiry_date=datetime.date.today() + datetime.timedelta(days=random.randint(300, 750)),
                manufactured_date=datetime.date.today() - datetime.timedelta(days=random.randint(30, 90)),
                batch_number=batch_code,
                warehouse_location=location,
                demand_factor=round(random.uniform(0.8, 1.4), 2),
                description=item['desc'],
                is_prescription_required=item['rx']
            )
            
            # Generate Label and Save
            composite_img = generate_medicine_label_image(
                category_name=cat_name,
                med_name=item['name'],
                brand=item['brand'],
                generic=item['generic'],
                ingredient=item['ingredient'],
                batch=batch_code,
                rx_required=item['rx']
            )
            
            # Save Image to Medicine Field
            buffer = BytesIO()
            composite_img.save(buffer, format='JPEG', quality=90)
            med.image.save(f"{med.name.replace(' ', '_').replace('/', '_')}.jpg", ContentFile(buffer.getvalue()), save=True)
            print(f"[{cat_name}] Created: {med.name} with unique image ({batch_code})")

    # Seeding Drug Interactions
    interactions = [
        {'a': 'aspirin', 'b': 'ibuprofen', 'severity': 'Severe', 'effect': 'Increases risk of stomach ulcers and bleeding, reducing heart protective effects of aspirin.'},
        {'a': 'ciprofloxacin', 'b': 'calcium', 'severity': 'Moderate', 'effect': 'Calcium bindings decrease ciprofloxacin absorption and reduce antibiotic strength.'},
        {'a': 'paracetamol', 'b': 'alcohol', 'severity': 'Severe', 'effect': 'Combining paracetamol with heavy alcohol consumption raises severe liver toxicity hazards.'},
        {'a': 'diphenhydramine', 'b': 'chlorpheniramine', 'severity': 'Moderate', 'effect': 'Co-taking increases sedative side effects like extreme drowsiness and dry mouth.'},
        {'a': 'metformin', 'b': 'contrast dye', 'severity': 'Severe', 'effect': 'Increased danger of lactic acidosis during radiology scans.'},
        {'a': 'pantoprazole', 'b': 'iron', 'severity': 'Moderate', 'effect': 'Acid suppression decreases iron absorption.'}
    ]

    for inter in interactions:
        DrugInteraction.objects.create(
            ingredient_a=inter['a'],
            ingredient_b=inter['b'],
            severity=inter['severity'],
            effect=inter['effect']
        )
        print(f"Added Drug Interaction: {inter['a']} + {inter['b']}")

    # Seeding Positive Thoughts
    thoughts = [
        "A healthy outside starts from the inside. Eat clean and stay positive!",
        "Your health is your greatest wealth. Invest in taking care of yourself today.",
        "Small, positive daily habits lead to long-term wellness. Keep going!",
        "Laughter is the best medicine, but for everything else, MediCart is here.",
        "Take care of your body. It's the only place you have to live in."
    ]
    for text in thoughts:
        PositiveThought.objects.create(text=text, is_active=True)
    
    print("Database seeding completed successfully.")

if __name__ == '__main__':
    populate()
    seed_blockchain()
