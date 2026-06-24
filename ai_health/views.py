import json
import base64
import re
from django.db import models
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from store.models import Medicine, DrugInteraction
from pypdf import PdfReader
from .rag_service import search_similar_documents, query_local_ollama

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

def local_symptom_fallback(symptoms_input, age, gender):
    symptoms_lower = symptoms_input.lower()
    conditions = []
    advice = []
    remedies = []
    suggested_medicines = []
    
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
        meds = Medicine.objects.filter(models.Q(name__icontains="calpol") | models.Q(name__icontains="crocin") | models.Q(name__icontains="dolo") | models.Q(name__icontains="ibuprofen"))
        for m in meds[:3]:
            suggested_medicines.append({
                "name": m.name,
                "reason": f"Contains active ingredient '{m.active_ingredient}' which acts as an analgesic/antipyretic."
            })
            
    if any(word in symptoms_lower for word in ['cough', 'cold', 'sneeze', 'throat', 'congestion', 'mucus', 'flu', 'runny nose']):
        conditions.append("Upper Respiratory Tract Infection (Common Cold)")
        advice.extend([
            "Keep throat hydrated by sipping warm water throughout the day.",
            "Inhale steam with eucalyptus oil twice daily.",
            "Avoid exposure to cold drafts and carbonated cold drinks."
        ])
        remedies.extend([
            "Mix honey, ginger juice, and black pepper, and consume 1 teaspoon.",
            "Gargle with warm saline water 3 times a day."
        ])
        meds = Medicine.objects.filter(models.Q(name__icontains="benadryl") | models.Q(name__icontains="ascoril") | models.Q(name__icontains="cofsils"))
        for m in meds[:3]:
            suggested_medicines.append({
                "name": m.name,
                "reason": "Indicated for cough, airway congestion, and chest soothing."
            })
            
    if not conditions:
        conditions.append("General Health Fatigue or Exhaustion")
        advice.extend([
            "Ensure a balanced meal intake with plenty of green vegetables.",
            "Attempt to get 8 hours of quality sleep.",
            "Consult a medical professional if feelings of fatigue persist."
        ])
        remedies.extend([
            "Practice deep breathing or light stretching.",
            "Stay hydrated and avoid heavy, greasy meals."
        ])
        meds = Medicine.objects.filter(models.Q(name__icontains="multivitamin") | models.Q(name__icontains="ashwagandha") | models.Q(name__icontains="zincovit"))
        for m in meds[:3]:
            suggested_medicines.append({
                "name": m.name,
                "reason": "Provides adaptogenic strength, vitamins, and minerals to bolster immune recovery."
            })
            
    return {
        'conditions': list(set(conditions)),
        'advice': list(set(advice))[:4],
        'remedies': list(set(remedies))[:4],
        'medicines': suggested_medicines,
        'disclaimer': "Notice: Running in Local Offline Fallback Mode. Information is retrieved from local clinical knowledge rules and pharmacy stock."
    }

def local_chat_fallback(query):
    query_lower = query.lower()
    
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
    
    return """
### MediBot Local RAG Assistant (Offline Mode)
Hello! I am currently running in **Local Offline Fallback Mode** because the external AI generative engine is resting.

I can still guide you regarding:
- Symptom advice (mention fever, cold, headache, etc.)
- Medicine stock information
- Drug interaction warnings (e.g. Aspirin + Ibuprofen)

*Disclaimer*: I am an AI assistant and not a medical doctor. Please consult a physician for health concerns.
"""

def symptom_checker(request):
    result = None
    if request.method == 'POST':
        age = request.POST.get('age')
        gender = request.POST.get('gender')
        symptoms_input = request.POST.get('symptoms', '')
        
        # RAG Search
        docs = search_similar_documents(symptoms_input, limit=4)
        rag_context = "\n\n".join([doc.page_content for doc in docs])
        
        system_prompt = (
            "You are 'MediBot RAG Doctor', a professional clinical assistant. "
            "Analyze symptoms and match with appropriate inventory. "
            "You must return ONLY a valid JSON object matching this structure. "
            "Do not wrap in markdown blocks, just return raw JSON text:\n"
            "{\n"
            "  \"conditions\": [\"Condition Name\"],\n"
            "  \"advice\": [\"Health recommendation\"],\n"
            "  \"remedies\": [\"Home remedy\"],\n"
            "  \"medicines\": [\n"
            "    {\"name\": \"Medicine Name\", \"reason\": \"Why this helps based on context\"}\n"
            "  ]\n"
            "}"
        )
        
        prompt = (
            f"Analyze symptoms for a {age}-year-old {gender}.\n"
            f"Symptoms: {symptoms_input}\n\n"
            f"Local DB Context:\n{rag_context}\n\n"
            f"Return the JSON response now."
        )
        
        response_text = query_local_ollama(prompt, system_prompt)
        
        try:
            # Clean response text if wrapped in code blocks
            clean_text = response_text.strip()
            if '```json' in clean_text:
                clean_text = clean_text.split('```json')[1].split('```')[0].strip()
            elif '```' in clean_text:
                clean_text = clean_text.split('```')[1].split('```')[0].strip()
                
            ai_data = json.loads(clean_text)
            result = {
                'conditions': ai_data.get('conditions', []),
                'advice': ai_data.get('advice', []),
                'remedies': ai_data.get('remedies', []),
                'medicines': ai_data.get('medicines', []),
                'disclaimer': "Disclaimer: This local RAG-powered analysis is for informational purposes only. It is not a substitute for clinical advice."
            }
        except Exception as e:
            print(f"Ollama JSON parse error: {e}. Output was: {response_text}")
            result = local_symptom_fallback(symptoms_input, age, gender)
            
    return render(request, 'ai_health/checker.html', {'result': result})

def health_assistant(request):
    response_text = None
    user_message = None
    
    # Initialize history list in session
    if 'assistant_history' not in request.session:
        request.session['assistant_history'] = []
        
    if request.method == 'POST':
        user_message = request.POST.get('message', '')
        
        # RAG Search
        docs = search_similar_documents(user_message, limit=4)
        rag_context = "\n\n".join([doc.page_content for doc in docs])
        
        system_prompt = (
            "You are 'MediBot', an empathetic, professional AI Health Assistant for MediCart Pharmacy. "
            "You operate locally using a vector database of clinical guides and medicine inventory. "
            "Provide helpful, structured advice. Always include a disclaimer at the end stating that "
            "you are an AI and not a substitute for a real doctor. Format your reply with bold headings and lists."
        )
        
        # Prepare context with message history
        history_str = ""
        for h in request.session['assistant_history'][-6:]: # last 3 turns
            history_str += f"User: {h['user']}\nAssistant: {h['bot']}\n"
            
        prompt = (
            f"Local Context:\n{rag_context}\n\n"
            f"Chat History:\n{history_str}\n"
            f"User: {user_message}\n"
            f"Assistant:"
        )
        
        response_text = query_local_ollama(prompt, system_prompt)
        
        # Save to session history
        history_list = request.session['assistant_history']
        history_list.append({"user": user_message, "bot": response_text})
        request.session['assistant_history'] = history_list
        request.session.modified = True
        
        # Convert to HTML
        response_text = markdown_to_html(response_text)
        
    return render(request, 'ai_health/assistant.html', {
        'response': response_text,
        'user_message': user_message,
        'chat_history': request.session['assistant_history']
    })

def doctor_chat(request):
    """
    Dedicated local clinical AI Doctor page.
    Supports speech-to-text, typing indicators, suggested questions, and medical report parsing.
    """
    response_text = None
    user_message = None
    extracted_text = None
    
    if 'doctor_history' not in request.session:
        request.session['doctor_history'] = []
        
    if request.method == 'POST':
        user_message = request.POST.get('message', '')
        report_file = request.FILES.get('report')
        
        # Handle Medical Report/Prescription File Upload (PDF or mock Image text)
        if report_file:
            if report_file.name.endswith('.pdf'):
                try:
                    pdf = PdfReader(report_file)
                    text_parts = [page.extract_text() for page in pdf.pages if page.extract_text()]
                    extracted_text = "\n".join(text_parts)
                    user_message = f"Please explain this uploaded medical document/report:\n\n{extracted_text}"
                except Exception as e:
                    user_message = f"Error reading uploaded PDF report: {e}"
            else:
                # Mock OCR text extractor for images (e.g. blood test report metadata or name)
                extracted_text = f"Simulated OCR extract from {report_file.name}: Blood Glucose level 145 mg/dL, cholesterol 210 mg/dL, trace proteins."
                user_message = f"Please analyze this clinical report image: {extracted_text}"
        
        if user_message:
            # Vector database lookup
            docs = search_similar_documents(user_message, limit=5)
            rag_context = "\n\n".join([doc.page_content for doc in docs])
            
            system_prompt = (
                "You are 'Dr. Llama', a professional, knowledgeable clinical AI consultant. "
                "You review symptoms, explain diagnostic lab reports, and outline medication schedules. "
                "Be thorough, structured, and empathetic. Always highlight that the analysis is "
                "for educational purposes and does not replace consulting a certified physician."
            )
            
            history_str = ""
            for h in request.session['doctor_history'][-6:]:
                history_str += f"Patient: {h['user']}\nDr. Llama: {h['bot']}\n"
                
            prompt = (
                f"Medical Context:\n{rag_context}\n\n"
                f"Consultation History:\n{history_str}\n"
                f"Patient: {user_message}\n"
                f"Dr. Llama:"
            )
            
            response_text = query_local_ollama(prompt, system_prompt)
            
            # Save history
            history_list = request.session['doctor_history']
            history_list.append({"user": user_message[:100] + ("..." if len(user_message) > 100 else ""), "bot": response_text})
            request.session['doctor_history'] = history_list
            request.session.modified = True
            
            # Render Markdown
            response_text = markdown_to_html(response_text)
            
    return render(request, 'ai_health/doctor_chat.html', {
        'response': response_text,
        'user_message': user_message,
        'chat_history': request.session['doctor_history']
    })

@login_required
def prescription_ocr(request):
    extracted_medicines = []
    matched_db_medicines = []
    error_msg = None
    
    if request.method == 'POST' and request.FILES.get('prescription'):
        presc_file = request.FILES['prescription']
        extracted_text = ""
        
        try:
            if presc_file.name.endswith('.pdf'):
                # Extract PDF text directly
                pdf = PdfReader(presc_file)
                extracted_text = "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])
            else:
                # Fallback mock OCR keywords based on file name or simple text matching
                name_clean = presc_file.name.lower()
                matched_words = []
                # Simple check of name keywords
                for word in ['dolo', 'paracetamol', 'aspirin', 'benadryl', 'avil', 'ashwagandha', 'metformin', 'burnol', 'soframycin']:
                    if word in name_clean:
                        matched_words.append(word.capitalize())
                if not matched_words:
                    matched_words = ['Paracetamol 500mg', 'Dolo 650'] # default mockup
                extracted_text = f"Prescription reads: Take {', '.join(matched_words)} twice daily after meals."
            
            # Use Llama3 to extract medicine names from text
            system_prompt = (
                "You are an OCR clinical text processor. Extract all names of medicines or drugs. "
                "Return ONLY a JSON list of drug names with the key 'medicines'."
                "Do not include markdown tags. Example: {\"medicines\": [\"Aspirin\", \"Dolo\"]}"
            )
            
            prompt = f"Text to parse:\n{extracted_text}\n\nReturn JSON list of medicines."
            response_text = query_local_ollama(prompt, system_prompt)
            
            clean_text = response_text.strip()
            if '```json' in clean_text:
                clean_text = clean_text.split('```json')[1].split('```')[0].strip()
            elif '```' in clean_text:
                clean_text = clean_text.split('```')[1].split('```')[0].strip()
                
            data = json.loads(clean_text)
            extracted_medicines = data.get('medicines', [])
            
            # Match extracted names with database items
            for ext_med in extracted_medicines:
                ext_med_clean = ext_med.strip().lower()
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
        except Exception as e:
            error_msg = f"Failed processing prescription document: {str(e)}"
            
    return render(request, 'ai_health/ocr_result.html', {
        'extracted': matched_db_medicines,
        'error': error_msg
    })

def drug_interaction_api(request):
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
    med_ids = request.GET.getlist('med_ids[]')
    medicines = Medicine.objects.filter(id__in=med_ids)
    ingredients = [med.active_ingredient.lower() for med in medicines if med.active_ingredient]
    
    warnings = []
    for i in range(len(ingredients)):
        for j in range(i + 1, len(ingredients)):
            ing_a = ingredients[i]
            ing_b = ingredients[j]
            
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
