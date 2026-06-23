import json
import hashlib
import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.db.models import Sum, Count
from store.models import Medicine
from .models import Cart, CartItem, Order, OrderItem, OrderAuditLog, BlockchainBlock
from .forms import CheckoutForm

def log_order_status(order, status_from, status_to, user=None):
    OrderAuditLog.objects.create(
        order=order,
        status_from=status_from,
        status_to=status_to,
        updated_by=user
    )

def add_block_to_chain(data_dict):
    """
    Simulates appending a verification block to the blockchain authenticity chain.
    """
    last_block = BlockchainBlock.objects.order_by('-index').first()
    idx = 0
    prev_hash = "0"
    if last_block:
        idx = last_block.index + 1
        prev_hash = last_block.hash
        
    data_str = json.dumps(data_dict)
    timestamp = datetime.datetime.now()
    
    # Calculate SHA256 hash
    value = str(idx) + str(timestamp) + data_str + prev_hash
    block_hash = hashlib.sha256(value.encode('utf-8')).hexdigest()
    
    BlockchainBlock.objects.create(
        index=idx,
        data=data_str,
        previous_hash=prev_hash,
        hash=block_hash
    )

@login_required
def add_to_cart(request, pk):
    medicine = get_object_or_404(Medicine, pk=pk)
    cart, created = Cart.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 1))
        
        # Apply dynamic pricing to verify stock limits
        if quantity > medicine.stock:
            messages.error(request, f"Only {medicine.stock} items left in stock.")
            return redirect('medicine_detail', pk=pk)
        
        cart_item, created = CartItem.objects.get_or_create(cart=cart, medicine=medicine)
        if not created:
            cart_item.quantity += quantity
        else:
            cart_item.quantity = quantity
            
        cart_item.save()
        messages.success(request, f"{medicine.name} added to cart.")
        
    return redirect('cart_view')

@login_required
def cart_view(request):
    cart, created = Cart.objects.get_or_create(user=request.user)
    # Apply dynamic pricing to cart items
    from store.views import apply_dynamic_pricing
    for item in cart.items.all():
        item.medicine.price = apply_dynamic_pricing(item.medicine)
    return render(request, 'orders/cart.html', {'cart': cart})

@login_required
def remove_from_cart(request, pk):
    cart_item = get_object_or_404(CartItem, pk=pk, cart__user=request.user)
    cart_item.delete()
    messages.success(request, "Item removed from cart.")
    return redirect('cart_view')

@login_required
def checkout(request):
    cart, created = Cart.objects.get_or_create(user=request.user)
    if not cart.items.exists():
        messages.warning(request, "Your cart is empty.")
        return redirect('medicine_list')

    # Apply dynamic pricing
    from store.views import apply_dynamic_pricing
    for item in cart.items.all():
        item.medicine.price = apply_dynamic_pricing(item.medicine)

    if request.method == 'POST':
        form = CheckoutForm(request.POST, request.FILES)
        if form.is_valid():
            # Check if any item needs prescription
            needs_prescription = False
            for item in cart.items.all():
                if item.medicine.is_prescription_required:
                    needs_prescription = True
                    break
            
            if needs_prescription and not request.FILES.get('prescription_image'):
                 messages.error(request, "A prescription is required for one or more items in your cart. Please upload it.")
                 return render(request, 'orders/checkout.html', {'form': form, 'cart': cart})

            order = form.save(commit=False)
            order.user = request.user
            order.total_amount = cart.total_price
            order.status = 'Pending'
            order.save()
            
            # Create Order Items and decrease stock
            for item in cart.items.all():
                OrderItem.objects.create(
                    order=order,
                    medicine=item.medicine,
                    quantity=item.quantity,
                    price=item.medicine.price
                )
                # Decrease stock
                item.medicine.stock -= item.quantity
                item.medicine.save()
            
            # Log audit status
            log_order_status(order, "Created", "Pending", request.user)
            
            # Clear Cart
            cart.items.all().delete()
            messages.success(request, "Order placed successfully! Thank you for choosing MediCart.")
            return render(request, 'orders/order_success.html', {'order': order, 'total_amount': order.total_amount})
        else:
             messages.error(request, f"Please correct the errors below: {form.errors}")
    else:
        form = CheckoutForm() 
        
    return render(request, 'orders/checkout.html', {'form': form, 'cart': cart})

@login_required
def order_history(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'orders/order_history.html', {'orders': orders})

@staff_member_required
def admin_dashboard(request):
    # Basic Stats
    total_orders = Order.objects.count()
    total_sales = Order.objects.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    pending_orders = Order.objects.filter(status='Pending').count()
    
    # Recent orders
    recent_orders = Order.objects.order_by('-created_at')[:5]
    
    # Chart Data: Orders not cancelled
    valid_orders = Order.objects.filter().exclude(status='Cancelled')
    status_counts = valid_orders.values('status').annotate(count=Count('status'))
    labels = [item['status'] for item in status_counts]
    data = [item['count'] for item in status_counts]
    
    # ML Low stock items prediction details
    low_stock_medicines = Medicine.objects.filter(stock__lt=15)
    for med in low_stock_medicines:
        # Simple velocity calculation: simulate 2.5 units sold daily
        med.predicted_days_remaining = int(med.stock / 2.5) if med.stock > 0 else 0
        med.reorder_suggested = med.stock < 10
        
    # Expiry warnings: within 30 days
    expiry_threshold = datetime.date.today() + datetime.timedelta(days=30)
    near_expiry_medicines = Medicine.objects.filter(expiry_date__lte=expiry_threshold)

    # Customer segments counts
    customer_segments = {
        'Chronic Patient': User.objects.filter(medical_history__isnull=False).count(),
        'General Wellness': Medicine.objects.filter(category__name='Wellness').count(),
        'Baby Care': Medicine.objects.filter(category__name='Baby Care').count(),
        'Ayurveda': Medicine.objects.filter(category__name='Ayurveda').count(),
    }

    # Fraud detection reports: order with >10 Rx medicines or unusual amounts
    anomalous_orders = Order.objects.annotate(item_count=Count('items')).filter(
        models.Q(total_amount__gt=2000) | models.Q(item_count__gt=8)
    )

    return render(request, 'orders/admin_dashboard.html', {
        'total_orders': total_orders,
        'total_sales': total_sales,
        'pending_orders': pending_orders,
        'recent_orders': recent_orders,
        'chart_labels': json.dumps(labels),
        'chart_data': json.dumps(data),
        'low_stock_medicines': low_stock_medicines,
        'near_expiry_medicines': near_expiry_medicines,
        'customer_segments': json.dumps(list(customer_segments.keys())),
        'customer_segment_values': json.dumps(list(customer_segments.values())),
        'anomalous_orders': anomalous_orders
    })

# ================= Advanced Logistics & Orders views =================

@staff_member_required
def pharmacist_queue(request):
    """
    Renders the pharmacist queue displaying orders requiring prescriptions verification.
    """
    pending_validations = Order.objects.filter(
        prescription_image__isnull=False,
        status='Pending'
    ).order_by('-created_at')
    
    return render(request, 'orders/pharmacist_queue.html', {
        'orders': pending_validations
    })

@staff_member_required
def pharmacist_validate(request, pk, action):
    """
    Approve or reject prescription files, logging the activity in audit files
    and blockchain batch records.
    """
    order = get_object_or_404(Order, pk=pk)
    old_status = order.status
    
    if action == 'approve':
        order.status = 'Approved'
        order.save()
        messages.success(request, f"Order #{order.id} prescription has been APPROVED.")
        log_order_status(order, old_status, "Approved", request.user)
        
        # Write approval log to blockchain verification block!
        blockchain_data = {
            "event": "Prescription Approved",
            "order_id": order.id,
            "pharmacist": request.user.username,
            "timestamp": datetime.datetime.now().isoformat(),
            "items": [item.medicine.name for item in order.items.all()],
            "status": "Authentic Validation Secured"
        }
        add_block_to_chain(blockchain_data)
        
    elif action == 'reject':
        order.status = 'Cancelled'
        order.save()
        messages.warning(request, f"Order #{order.id} prescription has been REJECTED. Order Cancelled.")
        log_order_status(order, old_status, "Cancelled (Prescription Rejected)", request.user)
        
        # Also return stock
        for item in order.items.all():
            item.medicine.stock += item.quantity
            item.medicine.save()
            
    return redirect('pharmacist_queue')

def blockchain_ledger(request):
    """
    View to display the security block verification nodes.
    """
    blocks = BlockchainBlock.objects.all().order_by('index')
    
    # Parse JSON block data fields
    parsed_blocks = []
    for b in blocks:
        try:
            parsed_data = json.loads(b.data)
        except:
            parsed_data = {"raw": b.data}
        parsed_blocks.append({
            'index': b.index,
            'timestamp': b.timestamp,
            'data': parsed_data,
            'previous_hash': b.previous_hash,
            'hash': b.hash
        })
        
    return render(request, 'orders/blockchain.html', {
        'blocks': parsed_blocks
    })

@login_required
def order_tracking(request, pk):
    """
    Delivery Route tracking showing Dijkstra routing visualization mapping warehouses.
    """
    order = get_object_or_404(Order, pk=pk, user=request.user)
    return render(request, 'orders/delivery_route.html', {
        'order': order
    })

# Make model helper imports
from django.db import models
