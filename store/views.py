import requests
import json
import difflib
import datetime
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from .models import Medicine, Category, PositiveThought, SubscriptionOrder, DrugInteraction

def apply_dynamic_pricing(medicine):
    """
    Adjusts the price dynamically based on stock and demand_factor.
    If stock is less than 15, increase price by 8%. If demand_factor > 1.2, increase by 10%.
    """
    price = float(medicine.original_price)
    
    # 1. Low stock premium (Scarcity pricing)
    if medicine.stock > 0 and medicine.stock < 15:
        price *= 1.08
    # 2. Demand factor premium (Surge pricing)
    if medicine.demand_factor > 1.2:
        price *= 1.10
        
    return round(price, 2)

def home(request):
    featured_medicines = Medicine.objects.all()[:4]
    
    # Apply dynamic pricing to featured
    for med in featured_medicines:
        med.price = apply_dynamic_pricing(med)
        
    categories = Category.objects.all()
    
    # AI Daily Health Tip
    API_KEY = "AIzaSyA0mgHwj8Vl6wJKD2NIGSaBo4TMAumrQYA"
    URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={API_KEY}"
    
    thought_text = "Stay hydrated and keep smiling!" # Default
    try:
        prompt = "Provide a one-sentence inspiring health tip or positive medical thought for a pharmacy website. Keep it under 15 words."
        response = requests.post(URL, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=5)
        if response.status_code == 200:
            thought_text = response.json()['candidates'][0]['content']['parts'][0]['text'].strip()
    except:
        # Fallback to database if AI fails
        thought = PositiveThought.objects.filter(is_active=True).order_by('?').first()
        if thought:
            thought_text = thought.text

    # Cart recovery reminder check:
    show_cart_reminder = False
    if request.user.is_authenticated:
        # Check if user has items in cart
        from orders.models import Cart
        cart, created = Cart.objects.get_or_create(user=request.user)
        if cart.items.exists():
            show_cart_reminder = True

    return render(request, 'store/home.html', {
        'featured_medicines': featured_medicines,
        'categories': categories,
        'thought_text': thought_text,
        'cart_reminder': show_cart_reminder
    })

def medicine_list(request):
    medicines = Medicine.objects.all()
    query = request.GET.get('q')
    category_id = request.GET.get('category')
    
    # Smart search with typo correction (difflib close match check)
    did_you_mean = None
    if query:
        query_strip = query.strip()
        # Direct filters
        filtered_meds = medicines.filter(
            Q(name__icontains=query_strip) | 
            Q(brand_name__icontains=query_strip) |
            Q(generic_name__icontains=query_strip) |
            Q(active_ingredient__icontains=query_strip)
        )
        
        # If direct filter returns nothing, run typo-correction check
        if not filtered_meds.exists():
            all_names = list(medicines.values_list('name', flat=True))
            matches = difflib.get_close_matches(query_strip, all_names, n=1, cutoff=0.4)
            if matches:
                did_you_mean = matches[0]
                # Filter by closest match
                filtered_meds = medicines.filter(name__icontains=did_you_mean)
            else:
                filtered_meds = Medicine.objects.none()
        
        medicines = filtered_meds
        
    if category_id:
        medicines = medicines.filter(category_id=category_id)
        
    # Apply dynamic pricing calculations for listing
    for med in medicines:
        med.price = apply_dynamic_pricing(med)
        
    categories = Category.objects.all()
    return render(request, 'store/medicine_list.html', {
        'medicines': medicines,
        'categories': categories,
        'query': query,
        'did_you_mean': did_you_mean
    })

def medicine_detail(request, pk):
    medicine = get_object_or_404(Medicine, pk=pk)
    # Apply dynamic pricing
    original_p = medicine.price
    medicine.price = apply_dynamic_pricing(medicine)
    price_surged = float(medicine.price) > float(medicine.original_price)
    
    # 1. Alternative substitutions (cheaper generic brands in stock)
    generic_substitutes = Medicine.objects.filter(
        generic_name__iexact=medicine.generic_name,
        price__lt=medicine.price
    ).exclude(id=medicine.id).order_by('price')
    
    # 2. Similar medicine suggestions (same category)
    similar_medicines = Medicine.objects.filter(category=medicine.category).exclude(id=medicine.id)[:4]
    
    # 3. Frequently bought together (collaborative mock recommendations)
    # Get items in the same subcategory or package suggestions
    package_suggestions = []
    if medicine.category.name == 'Tablet' or medicine.category.name == 'Syrup':
        # Suggest wellness supplements
        package_suggestions = Medicine.objects.filter(category__name='Wellness')[:2]

    # Wishlist state
    is_in_wishlist = False
    if request.user.is_authenticated:
        is_in_wishlist = medicine.wishlist_users.filter(id=request.user.id).exists()

    return render(request, 'store/medicine_detail.html', {
        'medicine': medicine,
        'price_surged': price_surged,
        'generic_substitutes': generic_substitutes,
        'similar_medicines': similar_medicines,
        'package_suggestions': package_suggestions,
        'is_in_wishlist': is_in_wishlist
    })

def emergency_services(request):
    return render(request, 'store/emergency.html')

def about_us(request):
    return render(request, 'store/about.html')

def compare_medicines(request):
    med1 = None
    med2 = None
    if request.method == 'POST' or request.GET.get('id1'):
        id1 = request.POST.get('med1_id') or request.GET.get('id1')
        id2 = request.POST.get('med2_id') or request.GET.get('id2')
        if id1:
            med1 = get_object_or_404(Medicine, id=id1)
            med1.price = apply_dynamic_pricing(med1)
        if id2:
            med2 = get_object_or_404(Medicine, id=id2)
            med2.price = apply_dynamic_pricing(med2)
            
    all_medicines = Medicine.objects.all().order_by('name')
    return render(request, 'store/compare.html', {
        'med1': med1,
        'med2': med2,
        'all_medicines': all_medicines
    })

@login_required
def wishlist_view(request):
    medicines = request.user.wishlist_medicines.all()
    for med in medicines:
        med.price = apply_dynamic_pricing(med)
    return render(request, 'store/wishlist.html', {'medicines': medicines})

@login_required
def wishlist_toggle(request, pk):
    medicine = get_object_or_404(Medicine, pk=pk)
    if medicine.wishlist_users.filter(id=request.user.id).exists():
        medicine.wishlist_users.remove(request.user)
        messages.success(request, f"{medicine.name} removed from your wishlist.")
    else:
        medicine.wishlist_users.add(request.user)
        messages.success(request, f"{medicine.name} saved to your wishlist.")
    
    # Redirect back to referring page or wishlist
    next_url = request.META.get('HTTP_REFERER', 'wishlist_view')
    return redirect(next_url)

def drug_interactions_network(request):
    return render(request, 'store/interactions.html')

@login_required
def subscribe_medicine(request, pk):
    medicine = get_object_or_404(Medicine, pk=pk)
    if request.method == 'POST':
        qty = int(request.POST.get('quantity', 1))
        freq = int(request.POST.get('frequency', 30))
        
        # Calculate next delivery date
        next_date = datetime.date.today() + datetime.timedelta(days=freq)
        
        SubscriptionOrder.objects.create(
            user=request.user,
            medicine=medicine,
            quantity=qty,
            frequency_days=freq,
            next_delivery_date=next_date
        )
        messages.success(request, f"Successfully subscribed to recurring order of {medicine.name} every {freq} days!")
        return redirect('subscriptions_list')
        
    return render(request, 'store/subscribe.html', {'medicine': medicine})

@login_required
def subscriptions_list(request):
    subscriptions = SubscriptionOrder.objects.filter(user=request.user)
    return render(request, 'store/subscriptions_list.html', {'subscriptions': subscriptions})
