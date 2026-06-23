import re
from store.models import Medicine, Category, DrugInteraction

def retrieve_context(query):
    """
    RAG retriever that finds matching medicines, active ingredients, categories,
    and potential drug interactions from the database based on keywords in the query.
    """
    query_lower = query.lower()
    keywords = re.findall(r'\b\w{3,}\b', query_lower)  # Words of length >= 3
    
    # 1. Search for matching medicines
    matched_medicines = set()
    for word in keywords:
        # Match name, brand, generic, ingredients, or description
        meds = Medicine.objects.filter(
            models.Q(name__icontains=word) |
            models.Q(brand_name__icontains=word) |
            models.Q(generic_name__icontains=word) |
            models.Q(active_ingredient__icontains=word) |
            models.Q(description__icontains=word)
        )
        for med in meds:
            matched_medicines.add(med)
            
    # 2. Search for drug interactions between ingredients in the query
    detected_interactions = []
    # Extract active ingredients from database to see if they are in query
    all_interactions = DrugInteraction.objects.all()
    for inter in all_interactions:
        # Check if both ingredients are mentioned in the query
        if inter.ingredient_a.lower() in query_lower and inter.ingredient_b.lower() in query_lower:
            detected_interactions.append(inter)
            
    # 3. Format retrieved data as text context
    context_parts = []
    
    if matched_medicines:
        context_parts.append("Retrieved Medicines in Stock:")
        for med in list(matched_medicines)[:6]:  # Cap at 6 matches for context window
            rx_status = "Prescription REQUIRED" if med.is_prescription_required else "Over-the-Counter (OTC)"
            context_parts.append(
                f"- Name: {med.name} (Brand: {med.brand_name}, Generic: {med.generic_name})\n"
                f"  Active Ingredient: {med.active_ingredient}\n"
                f"  Price: INR {med.price} | Stock: {med.stock} units | Expiry: {med.expiry_date}\n"
                f"  Class: {rx_status} | Location: {med.warehouse_location}\n"
                f"  Description: {med.description}"
            )
            
    if detected_interactions:
        context_parts.append("\nDetected Drug Interactions:")
        for inter in detected_interactions:
            context_parts.append(
                f"- conflict: {inter.ingredient_a.upper()} + {inter.ingredient_b.upper()}\n"
                f"  Severity: {inter.severity}\n"
                f"  Effect: {inter.effect}"
            )
            
    # If nothing matched, retrieve a generic list of top categories
    if not context_parts:
        categories = Category.objects.all()
        context_parts.append("Store Categories available:")
        for cat in categories:
            context_parts.append(f"- {cat.name}")
            
    return "\n".join(context_parts)

# Ensure models is available in the module context
from django.db import models
