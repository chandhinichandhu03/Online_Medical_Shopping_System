import os
import django
import random
import datetime
import hashlib
import json
import requests
from io import BytesIO
from django.core.files import File

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
        {"batch": "BATCH-001", "drug": "Calpol 650", "manufacturer": "GlaxoSmithKline", "status": "FDA Approved", "purity": "99.8%"},
        {"batch": "BATCH-002", "drug": "Avil 25", "manufacturer": "Sanofi", "status": "FDA Approved", "purity": "99.4%"},
        {"batch": "BATCH-003", "drug": "Aspirin 81", "manufacturer": "Bayer", "status": "FDA Approved", "purity": "99.9%"},
        {"batch": "BATCH-004", "drug": "Benadryl Cough Syrup", "manufacturer": "Johnson & Johnson", "status": "FDA Approved", "purity": "98.7%"}
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

def download_image(url):
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return BytesIO(response.content)
    except Exception as e:
        print(f"Error downloading image {url}: {e}")
    return None

def populate():
    print("Seeding database categories and medicines with real images...")

    # Clear existing data to prevent duplicates during testing
    Medicine.objects.all().delete()
    Category.objects.all().delete()
    DrugInteraction.objects.all().delete()
    PositiveThought.objects.all().delete()

    # Seeding Categories
    categories = [
        'Tablet', 'Syrup', 'Ointment', 'First Aid', 'Pet Care', 'Syringes', 'Injections', 'Wellness', 'Baby Care', 'Ayurveda'
    ]
    
    cat_objects = {}
    for name in categories:
        slug = name.lower().replace(' ', '-')
        c = Category.objects.create(name=name, slug=slug)
        cat_objects[name] = c

    # Extended Medicines Data with Active Ingredients and Generic Substitutes and stable Unsplash images
    medicines_data = [
        # Ayurveda
        {
            'name': 'Ashwagandha Capsule', 'category': 'Ayurveda', 'brand': 'Himalaya', 'price': 160.00, 
            'generic': 'Withania Somnifera Powder', 'ingredient': 'ashwagandha', 'stock': 45, 
            'days_to_expiry': 400, 'desc': 'Herbal supplement for stress relief, anxiety reduction, and immunity.', 'rx': False,
            'warehouse': 'Row A / Shelf 1', 'batch': 'BATCH-AYU01',
            'image_url': 'https://images.unsplash.com/photo-1540420773420-3366772f4999?auto=format&fit=crop&w=300'
        },
        {
            'name': 'Chyawanprash Special', 'category': 'Ayurveda', 'brand': 'Dabur', 'price': 340.00, 
            'generic': 'Amla & Herbal Elixir', 'ingredient': 'amla', 'stock': 80, 
            'days_to_expiry': 300, 'desc': 'Traditional immunity booster enriched with vitamin C and antioxidant herbs.', 'rx': False,
            'warehouse': 'Row A / Shelf 2', 'batch': 'BATCH-AYU02',
            'image_url': 'https://images.unsplash.com/photo-1512290923902-8a9f81dc236c?auto=format&fit=crop&q=80&w=300'
        },
        
        # Tablets
        {
            'name': 'Calpol 650', 'category': 'Tablet', 'brand': 'GlaxoSmithKline', 'price': 32.00, 
            'generic': 'Paracetamol 650mg', 'ingredient': 'paracetamol', 'stock': 120, 
            'days_to_expiry': 450, 'desc': 'Common antipyretic and analgesic tablet for fever and mild to moderate pain relief.', 'rx': False,
            'warehouse': 'Row B / Shelf 1', 'batch': 'BATCH-001',
            'image_url': 'https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?auto=format&fit=crop&q=80&w=300'
        },
        {
            'name': 'Crocin Pain Relief', 'category': 'Tablet', 'brand': 'GlaxoSmithKline', 'price': 40.00, 
            'generic': 'Paracetamol 650mg', 'ingredient': 'paracetamol', 'stock': 15, 
            'days_to_expiry': 12, 
            'desc': 'Fast acting tablet containing paracetamol and caffeine for severe headache and joint pain.', 'rx': False,
            'warehouse': 'Row B / Shelf 1', 'batch': 'BATCH-TAB02',
            'image_url': 'https://images.unsplash.com/photo-1550572017-edd951b55104?auto=format&fit=crop&q=80&w=300'
        },
        {
            'name': 'Aspirin Cardio', 'category': 'Tablet', 'brand': 'Bayer', 'price': 90.00, 
            'generic': 'Aspirin 81mg', 'ingredient': 'aspirin', 'stock': 200, 
            'days_to_expiry': 600, 'desc': 'Low dose aspirin for cardiovascular protection and anti-platelet therapy.', 'rx': True,
            'warehouse': 'Row B / Shelf 2', 'batch': 'BATCH-003',
            'image_url': 'https://images.unsplash.com/photo-1584017911766-d451b3d0e843?auto=format&fit=crop&w=300'
        },
        {
            'name': 'Ecotrin 325', 'category': 'Tablet', 'brand': 'Bayer', 'price': 75.00, 
            'generic': 'Aspirin 325mg', 'ingredient': 'aspirin', 'stock': 65, 
            'days_to_expiry': 350, 'desc': 'Enteric-coated aspirin tablet for anti-inflammatory and pain relief uses.', 'rx': True,
            'warehouse': 'Row B / Shelf 2', 'batch': 'BATCH-TAB04',
            'image_url': 'https://images.unsplash.com/photo-1628771065518-0d82f1938462?auto=format&fit=crop&q=80&w=300'
        },
        {
            'name': 'Ibuprofen 400', 'category': 'Tablet', 'brand': 'Abbott', 'price': 25.00, 
            'generic': 'Ibuprofen 400mg', 'ingredient': 'ibuprofen', 'stock': 150, 
            'days_to_expiry': 500, 'desc': 'Non-steroidal anti-inflammatory drug (NSAID) for muscle pain, dental pain, and arthritis.', 'rx': False,
            'warehouse': 'Row B / Shelf 3', 'batch': 'BATCH-TAB05',
            'image_url': 'https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?auto=format&fit=crop&q=80&w=300'
        },
        {
            'name': 'Avil 25', 'category': 'Tablet', 'brand': 'Sanofi', 'price': 18.00, 
            'generic': 'Pheniramine Maleate 25mg', 'ingredient': 'pheniramine', 'stock': 90, 
            'days_to_expiry': 280, 'desc': 'Antihistamine tablet for allergic rhinitis, hives, eczema, and skin reactions.', 'rx': False,
            'warehouse': 'Row B / Shelf 4', 'batch': 'BATCH-002',
            'image_url': 'https://images.unsplash.com/photo-1471864190281-a93a3070b6de?auto=format&fit=crop&q=80&w=300'
        },
        {
            'name': 'Cifran 500', 'category': 'Tablet', 'brand': 'Ranbaxy', 'price': 85.00, 
            'generic': 'Ciprofloxacin 500mg', 'ingredient': 'ciprofloxacin', 'stock': 50, 
            'days_to_expiry': 365, 'desc': 'Broad-spectrum fluoroquinolone antibiotic for treating severe bacterial infections.', 'rx': True,
            'warehouse': 'Row B / Shelf 5', 'batch': 'BATCH-TAB07',
            'image_url': 'https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?auto=format&fit=crop&q=80&w=300'
        },
        
        # Syrups
        {
            'name': 'Benadryl Cough Syrup', 'category': 'Syrup', 'brand': 'Johnson & Johnson', 'price': 120.00, 
            'generic': 'Diphenhydramine Syrup', 'ingredient': 'diphenhydramine', 'stock': 70, 
            'days_to_expiry': 180, 'desc': 'Relieves cough, throat irritation, runny nose, and sneezing symptoms.', 'rx': False,
            'warehouse': 'Row C / Shelf 1', 'batch': 'BATCH-004',
            'image_url': 'https://images.unsplash.com/photo-1512290923902-8a9f81dc236c?auto=format&fit=crop&w=300'
        },
        {
            'name': 'Ascoril LS', 'category': 'Syrup', 'brand': 'Glenmark', 'price': 140.00, 
            'generic': 'Ambroxol + Levosalbutamol + Guaiphenesin', 'ingredient': 'ambroxol', 'stock': 8, 
            'days_to_expiry': 120, 'desc': 'Mucolytic expectorant cough syrup designed to clear chest congestion and ease breathing.', 'rx': True,
            'warehouse': 'Row C / Shelf 2', 'batch': 'BATCH-SYR02',
            'image_url': 'https://images.unsplash.com/photo-1512290923902-8a9f81dc236c?auto=format&fit=crop&w=300'
        },

        # Wellness
        {
            'name': 'Zincovit Tablets', 'category': 'Wellness', 'brand': 'Apex', 'price': 110.00, 
            'generic': 'Multivitamins & Zinc', 'ingredient': 'multivitamins', 'stock': 130, 
            'days_to_expiry': 270, 'desc': 'Daily nutritional supplement packed with vital vitamins, minerals, and zinc.', 'rx': False,
            'warehouse': 'Row D / Shelf 1', 'batch': 'BATCH-WEL01',
            'image_url': 'https://images.unsplash.com/photo-1628771065518-0d82f1938462?auto=format&fit=crop&q=80&w=300'
        },
        
        # Baby Care
        {
            'name': 'Himalaya Baby Lotion', 'category': 'Baby Care', 'brand': 'Himalaya', 'price': 180.00, 
            'generic': 'Olive Oil & Country Mallow Lotion', 'ingredient': 'herbal extract', 'stock': 35, 
            'days_to_expiry': 480, 'desc': 'Gentle, hypoallergenic daily moisturizer formulated specifically for tender baby skin.', 'rx': False,
            'warehouse': 'Row E / Shelf 1', 'batch': 'BATCH-BAB01',
            'image_url': 'https://images.unsplash.com/photo-1608571423902-eed4a5ad8108?auto=format&fit=crop&q=80&w=300'
        },
        
        # First Aid
        {
            'name': 'Dettol Liquid 250ml', 'category': 'First Aid', 'brand': 'Reckitt Benckiser', 'price': 65.00, 
            'generic': 'Chloroxylenol Antiseptic', 'ingredient': 'chloroxylenol', 'stock': 110, 
            'days_to_expiry': 700, 'desc': 'Antiseptic disinfectant liquid for first aid wound cleaning and environmental sanitation.', 'rx': False,
            'warehouse': 'Row F / Shelf 1', 'batch': 'BATCH-AID01',
            'image_url': 'https://images.unsplash.com/photo-1603052875302-d376b7c0638a?auto=format&fit=crop&q=80&w=300'
        }
    ]

    for item in medicines_data:
        cat = cat_objects[item['category']]
        med = Medicine.objects.create(
            category=cat,
            name=item['name'],
            brand_name=item['brand'],
            generic_name=item['generic'],
            active_ingredient=item['ingredient'],
            price=item['price'],
            original_price=item['price'],
            stock=item['stock'],
            expiry_date=datetime.date.today() + datetime.timedelta(days=item['days_to_expiry']),
            manufactured_date=datetime.date.today() - datetime.timedelta(days=100),
            batch_number=item['batch'],
            warehouse_location=item['warehouse'],
            demand_factor=1.0,
            description=item['desc'],
            is_prescription_required=item['rx']
        )
        
        # Download and Save Image
        img_url = item.get('image_url')
        if img_url:
            img_content = download_image(img_url)
            if img_content:
                med.image.save(f"{med.name.replace(' ', '_')}.jpg", File(img_content), save=True)
                print(f"Added Medicine with Image: {item['name']}")
            else:
                print(f"Added Medicine (No Image Downloaded): {item['name']}")
        else:
            print(f"Added Medicine (No Image URL): {item['name']}")

    # Seeding Drug Interactions
    interactions = [
        {
            'a': 'aspirin', 'b': 'ibuprofen', 'severity': 'Severe', 
            'effect': 'Concomitant use increases risk of gastrointestinal ulceration, bleeding, and reduced anti-platelet cardiotonic efficacy of aspirin.'
        },
        {
            'a': 'ciprofloxacin', 'b': 'calcium', 'severity': 'Moderate', 
            'effect': 'Calcium carbonate or calcium rich drinks bind to ciprofloxacin in the gut, reducing antibiotic absorption and efficacy by up to 40%.'
        },
        {
            'a': 'paracetamol', 'b': 'alcohol', 'severity': 'Severe', 
            'effect': 'Chronic or heavy alcohol intake combined with paracetamol increases the risk of severe hepatotoxicity (liver failure).'
        },
        {
            'a': 'diphenhydramine', 'b': 'pheniramine', 'severity': 'Moderate', 
            'effect': 'Combining two antihistamines increases central nervous system depression, leading to severe drowsiness, dry mouth, and blurred vision.'
        }
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
    
    print("Database seeding completed.")

if __name__ == '__main__':
    populate()
    seed_blockchain()
