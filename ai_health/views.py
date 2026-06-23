import json
import base64
import requests
import re
from django.db import models
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from store.models import Medicine, DrugInteraction
from .rag_engine import retrieve_context

# Use a valid public key or fallback safely
API_KEY_FALLBACK = "AIzaSyA0mgHwj8Vl6wJKD2NIGSaBo4TMAumrQYA"

def get_gemini_url(model="gemini-1.5-flash"):
    return f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={API_KEY_FALLBACK}"

def symptom_checker(request):
    result = None
    if request.method == 'POST':
        age = request.POST.get('age')
        gender = request.POST.get('gender')
        symptoms_input = request.POST.get('symptoms', '')
        
        # 1. RAG retrieval step: retrieve matching inventory & interaction logs
        rag_context = retrieve_context(symptoms_input)
        
        # 2. Construct prompt incorporating retrieved context
        prompt = f"""
        You are 'MediBot RAG Engine', a professional clinical assistant.
        Analyze symptoms for a {age}-year-old {gender}.
        Symptoms: {symptoms_input}
        
        Below is the context retrieved from our actual pharmacy inventory database:
        {rag_context}
        
        Return a JSON object with the following structure:
        {{
            "conditions": ["List of 2-3 possible conditions"],
            "advice": ["List of 3-4 professional health recommendations"],
            "remedies": ["List of 3-4 home remedies"],
            "medicines": [
                {{"name": "Suggested Medicine from Inventory or OTC", "reason": "Brief reason based on context"}}
            ]
        }}
        Ensure the output is valid JSON and only the JSON object. Do not include markdown wraps.
        IMPORTANT: Prioritize matching retrieved medicines from context. If none match, list safe OTC remedies.
        """
        
        headers = {'Content-Type': 'application/json'}
        data = {
            "contents": [{
                "parts": [{"text": prompt}]
            }]
        }
        
        try:
            response = requests.post(get_gemini_url(), headers=headers, json=data, timeout=30)
            if response.status_code == 200:
                raw_response = response.json()
                content = raw_response['candidates'][0]['content']['parts'][0]['text']
                
                # Extract clean JSON
                if '```json' in content:
                    content = content.split('```json')[1].split('```')[0].strip()
                elif '```' in content:
                    content = content.split('```')[1].split('```')[0].strip()
                
                ai_data = json.loads(content)
                
                result = {
                    'conditions': ai_data.get('conditions', []),
                    'advice': ai_data.get('advice', []),
                    'remedies': ai_data.get('remedies', []),
                    'medicines': ai_data.get('medicines', []),
                    'disclaimer': "This RAG-powered tool provides general health suggestions based on stock inventory. It is not a substitute for clinical advice."
                }
            else:
                # Local offline fallback if API returns non-200
                result = local_symptom_fallback(symptoms_input, age, gender)
        except Exception as e:
            # Local offline fallback on exception
            result = local_symptom_fallback(symptoms_input, age, gender)
        
    return render(request, 'ai_health/checker.html', {'result': result})

def local_symptom_fallback(symptoms_input, age, gender):
    symptoms_lower = symptoms_input.lower()
    conditions = []
    advice = []
    remedies = []
    suggested_medicines = []
    
    # 1. Pain / Fever / Headache
    if any(word in symptoms_lower for word in ['fever', 'headache', 'body pain', 'temp', 'migraine', 'ache', 'sore']):
        conditions.append("Mild Pyrexia (Fever) & Tension Headache")
        advice.extend([
            "Monitor body temperature using a thermometer regularly.",
            "Rest in a quiet, dark room to relieve head pressure.",
            "If temperature exceeds 102 F or lasts > 3 days, consult a physician."
        ])
        remedies.extend([
            "Apply a cold damp compress to the forehead.",
            "Drink warm herbal infusion tea (chamomile or ginger).",
            "Keep well-hydrated with water and electrolyte solution."
        ])
        # Find matching medicines in database
        meds = Medicine.objects.filter(models.Q(name__icontains="calpol") | models.Q(name__icontains="crocin") | models.Q(name__icontains="ibuprofen") | models.Q(name__icontains="aspirin"))
        for m in meds[:3]:
            suggested_medicines.append({
                "name": m.name,
                "reason": f"Contains active ingredient '{m.active_ingredient}' which is a clinical analgesic/antipyretic."
            })
            
    # 2. Cough / Cold / Throat
    if any(word in symptoms_lower for word in ['cough', 'cold', 'sneeze', 'throat', 'congestion', 'mucus', 'flu', 'runny nose']):
        conditions.append("Upper Respiratory Tract Infection (Common Cold)")
        advice.extend([
            "Keep throat hydrated by sipping warm water throughout the day.",
            "Inhale steam with eucalyptus oil twice daily.",
            "Avoid exposure to cold drinks, air conditioning drafts, and smoke."
        ])
        remedies.extend([
            "Mix honey, ginger juice, and black pepper, and consume 1 teaspoon.",
            "Gargle with warm saline water at least three times a day.",
            "Drink hot lemon-water with honey to soothe throat irritation."
        ])
        meds = Medicine.objects.filter(models.Q(name__icontains="benadryl") | models.Q(name__icontains="ascoril"))
        for m in meds[:2]:
            suggested_medicines.append({
                "name": m.name,
                "reason": f"Useful for dry or wet cough and congestion. Relieves airway irritation."
            })
            
    # 3. Allergies / Itch
    if any(word in symptoms_lower for word in ['allergy', 'allergic', 'itch', 'hives', 'rash', 'redness', 'eczema', 'sneeze']):
        if not conditions:  # Avoid duplicate sneeze triggers
            conditions.append("Allergic Rhinitis or Contact Dermatitis")
        advice.extend([
            "Identify and avoid exposure to potential allergen triggers (pollen, dust, pet hair).",
            "Avoid scratching irritated skin or scratching hives."
        ])
        remedies.extend([
            "Apply pure aloe vera gel or calamine lotion to the itchy areas.",
            "Take oatmeal bath or apply a cool damp compress."
        ])
        meds = Medicine.objects.filter(name__icontains="avil")
        for m in meds[:2]:
            suggested_medicines.append({
                "name": m.name,
                "reason": f"An antihistamine (Pheniramine) that blocks allergic receptors to relieve itching and runny nose."
            })
            
    # 4. Default wellness / general fatigue
    if not conditions:
        conditions.append("General Fatigue / Nutritional Deficiencies")
        advice.extend([
            "Maintain a balanced daily diet rich in leafy greens and protein.",
            "Attempt at least 7-8 hours of sound sleep daily.",
            "Engage in 30 minutes of low-impact physical exercise daily."
        ])
        remedies.extend([
            "Start the day with warm water and soaked almonds.",
            "Practice deep breathing or light yoga for stress relief."
        ])
        meds = Medicine.objects.filter(models.Q(name__icontains="zincovit") | models.Q(name__icontains="ashwagandha") | models.Q(name__icontains="lotion"))
        for m in meds[:2]:
            suggested_medicines.append({
                "name": m.name,
                "reason": f"Enriches vitamins or provides general adaptogenic strength support."
            })
            
    return {
        'conditions': list(set(conditions)),
        'advice': list(set(advice))[:4],
        'remedies': list(set(remedies))[:4],
        'medicines': suggested_medicines,
        'disclaimer': "Notice: Running in Local Offline Fallback Mode. Information is retrieved from local clinical knowledge rules and pharmacy stock."
    }

def markdown_to_html(text):
    if not text:
        return ""
    # Convert bold **text** to <strong>text</strong>
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
    # Convert italic *text* to <em>text</em>
    text = re.sub(r'\*(.*?)\*', r'<em>\1</em>', text)
    
    lines = text.split('\n')
    processed_lines = []
    in_list = False
    
    for line in lines:
        line_strip = line.strip()
        
        # Headers: ### or ## or #
        if line_strip.startswith('### '):
            if in_list:
                processed_lines.append('</ul>')
                in_list = False
            processed_lines.append(f'<h5 class="fw-bold mt-3 text-primary">{line_strip[4:]}</h5>')
        elif line_strip.startswith('## '):
            if in_list:
                processed_lines.append('</ul>')
                in_list = False
            processed_lines.append(f'<h4 class="fw-bold mt-3 text-primary">{line_strip[3:]}</h4>')
        elif line_strip.startswith('# '):
            if in_list:
                processed_lines.append('</ul>')
                in_list = False
            processed_lines.append(f'<h3 class="fw-bold mt-3 text-primary">{line_strip[2:]}</h3>')
            
        # Bullet list: - or *
        elif line_strip.startswith('- ') or line_strip.startswith('* '):
            if not in_list:
                processed_lines.append('<ul class="list-group list-group-flush mb-3">')
                in_list = True
            content = line_strip[2:]
            processed_lines.append(f'<li class="list-group-item bg-transparent py-1 border-0"><i class="fas fa-chevron-right text-primary me-2 small"></i>{content}</li>')
        else:
            if in_list and line_strip == "":
                processed_lines.append('</ul>')
                in_list = False
            
            if line_strip:
                processed_lines.append(f'<p class="mb-2">{line_strip}</p>')
            else:
                processed_lines.append('')
                
    if in_list:
        processed_lines.append('</ul>')
        
    return '\n'.join(processed_lines)

def local_chat_fallback(query):
    query_lower = query.lower()
    
    # 1. Drug interaction check (evaluated first so it is not intercepted by generic medicine check)
    if any(word in query_lower for word in ['interact', 'conflict', 'mix', 'safe to take', 'side effect', 'contraindication', 'warning']):
        return """
### MediBot Local RAG Assistant (Offline Mode)
I detected a query about drug safety/interactions.

*Key conflicts tracked in our database*:
- **Aspirin + Ibuprofen**: Severe risk of stomach bleeding and ulcers.
- **Ciprofloxacin + Calcium**: Calcium reduces antibiotic absorption.
- **Paracetamol + Alcohol**: Severe risk of liver toxicity.

You can visit our **Interactions Graph** tab from the navigation bar to interactively search and visualize drug-to-drug conflicts.
*Disclaimer*: Always verify combination safety with a certified physician.
"""
    # 2. Symptoms check
    elif any(word in query_lower for word in ['symptom', 'fever', 'cough', 'headache', 'cold', 'pain', 'ache', 'sore']):
        return """
### MediBot Local RAG Assistant (Offline Mode)
I detected symptoms related to pain, cough, or fever. 

Based on our local inventory, I suggest:
- **Calpol 650 / Crocin**: Contains **Paracetamol**, useful for relieving fever and headaches.
- **Benadryl / Ascoril LS**: Useful for cough and chest congestion.

*Remedies*: Drink warm water, gargle with salt water, and get plenty of rest.
*Disclaimer*: I am an AI RAG fallback assistant. Please consult a doctor for severe symptoms.
"""
    # 3. Medicine check
    elif any(word in query_lower for word in ['medicine', 'drug', 'tablet', 'pill', 'syrup', 'stock', 'store', 'shop']):
        return """
### MediBot Local RAG Assistant (Offline Mode)
You inquired about medicines.

We currently stock:
- **Calpol 650** (Fever/Pain)
- **Aspirin Cardio** (Heart Health - *Prescription Required*)
- **Avil 25** (Allergies)
- **Benadryl Cough Syrup** (Cough)
- **Ashwagandha Capsule** (Wellness & Stress)

You can search for these names in our shop search bar to view prices, stocks, and details.
*Disclaimer*: I am an AI RAG fallback assistant. Consult a clinical pharmacist before taking drugs.
"""
    
    # Default fallback
    return """
### MediBot Local RAG Assistant (Offline Mode)
Hello! I am currently running in **Local Offline Fallback Mode** because the external AI generative engine is resting.

I can still guide you regarding:
- Symptom advice (mention fever, cold, headache, etc.)
- Medicine stock information
- Drug interaction warnings (e.g. Aspirin + Ibuprofen)

*Disclaimer*: I am an AI assistant and not a medical doctor. Please consult a physician for health concerns.
"""

def health_assistant(request):
    response_text = None
    user_message = None
    
    if request.method == 'POST':
        user_message = request.POST.get('message', '')
        
        # RAG retrieval for the user query
        rag_context = retrieve_context(user_message)
        
        prompt = f"""
        You are 'MediBot', a professional AI Health Assistant for MediCart Pharmacy operating on local RAG.
        Empathize, maintain accuracy, and limit suggestions to safe practices.
        
        Use the following local database context to answer the query:
        {rag_context}
        
        User Query: {user_message}
        
        Always include a disclaimer that you are an AI assistant and not a medical doctor.
        Keep responses concise, structural, and format using markdown.
        """
        
        try:
            headers = {'Content-Type': 'application/json'}
            data = {"contents": [{"parts": [{"text": prompt}]}]}
            response = requests.post(get_gemini_url(), headers=headers, json=data, timeout=30)
            if response.status_code == 200:
                response_text = response.json()['candidates'][0]['content']['parts'][0]['text']
            else:
                response_text = local_chat_fallback(user_message)
        except Exception as e:
            response_text = local_chat_fallback(user_message)
            
        # Convert markdown text to HTML format
        response_text = markdown_to_html(response_text)
            
    return render(request, 'ai_health/assistant.html', {
        'response': response_text,
        'user_message': user_message
    })

@login_required
def prescription_ocr(request):
    extracted_medicines = []
    matched_db_medicines = []
    
    if request.method == 'POST' and request.FILES.get('prescription'):
        presc_file = request.FILES['prescription']
        
        # 1. Base64 encode image for Gemini API vision
        try:
            image_data = base64.b64encode(presc_file.read()).decode('utf-8')
            
            prompt = """
            Analyze this prescription image. Perform OCR on the handwriting or print.
            Extract all names of prescribed drugs or medicines.
            Return a JSON object with a single key 'medicines' which is a list of strings of drug names.
            Return ONLY valid JSON. Example: {"medicines": ["Aspirin", "Paracetamol"]}
            """
            
            payload = {
                "contents": [{
                    "parts": [
                        {"text": prompt},
                        {
                            "inlineData": {
                                "mimeType": presc_file.content_type,
                                "data": image_data
                            }
                        }
                    ]
                }]
            }
            
            headers = {'Content-Type': 'application/json'}
            url = get_gemini_url("gemini-1.5-flash") # Vision model support
            
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            if response.status_code == 200:
                raw_text = response.json()['candidates'][0]['content']['parts'][0]['text']
                if '```json' in raw_text:
                    raw_text = raw_text.split('```json')[1].split('```')[0].strip()
                elif '```' in raw_text:
                    raw_text = raw_text.split('```')[1].split('```')[0].strip()
                    
                data = json.loads(raw_text)
                extracted_medicines = data.get('medicines', [])
                
                # Match extracted names with database items (fuzzy check)
                for ext_med in extracted_medicines:
                    ext_med_clean = ext_med.strip().lower()
                    # Look for exact or partial name matching
                    db_match = Medicine.objects.filter(
                        models.Q(name__icontains=ext_med_clean) |
                        models.Q(generic_name__icontains=ext_med_clean) |
                        models.Q(active_ingredient__icontains=ext_med_clean)
                    ).first()
                    
                    matched_db_medicines.append({
                        'extracted_name': ext_med,
                        'matched': db_match is not None,
                        'medicine_id': db_match.id if db_match else None,
                        'medicine_name': db_match.name if db_match else "No match found in shop",
                        'price': db_match.price if db_match else None,
                        'stock': db_match.stock if db_match else 0
                    })
            else:
                return render(request, 'ai_health/ocr_result.html', {'error': 'OCR Service failed to analyze image.'})
        except Exception as e:
            return render(request, 'ai_health/ocr_result.html', {'error': f'Failed processing image: {str(e)}'})
            
    return render(request, 'ai_health/ocr_result.html', {
        'extracted': matched_db_medicines
    })

def drug_interaction_api(request):
    """
    Returns drug interactions as a network dataset (nodes and edges) in JSON format
    for drawing interactive graph networks on frontend canvas.
    """
    interactions = DrugInteraction.objects.all()
    nodes = set()
    edges = []
    
    for inter in interactions:
        nodes.add(inter.ingredient_a.lower())
        nodes.add(inter.ingredient_b.lower())
        edges.append({
            'source': inter.ingredient_a.lower(),
            'target': inter.ingredient_b.lower(),
            'severity': inter.severity,
            'effect': inter.effect
        })
        
    return JsonResponse({
        'nodes': [{'id': n, 'label': n.capitalize()} for n in list(nodes)],
        'edges': edges
    })

def check_interactions_ajax(request):
    """
    Accepts a list of medicine IDs, checks active ingredients for conflicts
    and returns lists of identified warnings.
    """
    med_ids = request.GET.getlist('med_ids[]')
    medicines = Medicine.objects.filter(id__in=med_ids)
    ingredients = [med.active_ingredient.lower() for med in medicines if med.active_ingredient]
    
    warnings = []
    found_ingredients = set()
    
    # Check pairwise combinations
    for i in range(len(ingredients)):
        for j in range(i + 1, len(ingredients)):
            ing_a = ingredients[i]
            ing_b = ingredients[j]
            
            # Query bidirectional
            conflict = DrugInteraction.objects.filter(
                (models.Q(ingredient_a=ing_a) & models.Q(ingredient_b=ing_b)) |
                (models.Q(ingredient_a=ing_b) & models.Q(ingredient_b=ing_a))
            ).first()
            
            if conflict:
                warnings.append({
                    'ingredient_a': conflict.ingredient_a.capitalize(),
                    'ingredient_b': conflict.ingredient_b.capitalize(),
                    'severity': conflict.severity,
                    'effect': conflict.effect
                })
                
    return JsonResponse({'warnings': warnings})
