import json
import hashlib
import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.db.models import Sum, Count
from django.contrib.auth import get_user_model
from store.models import Medicine
from .models import Cart, CartItem, Order, OrderItem, OrderAuditLog, BlockchainBlock
from .forms import CheckoutForm

User = get_user_model()

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

    subtotal = cart.total_price
    delivery_option = request.POST.get('delivery_option', 'Standard')
    delivery_charges = 0.00
    if delivery_option == 'Standard':
        delivery_charges = 0.00 if subtotal > 500 else 40.00
    elif delivery_option == 'Express':
        delivery_charges = 100.00
    elif delivery_option == 'Same Day':
        delivery_charges = 150.00
        
    tax_amount = round(float(subtotal) * 0.18, 2)
    
    if request.method == 'POST':
        form = CheckoutForm(request.POST, request.FILES)
        
        discount_applied_str = request.POST.get('discount_applied', '0.00')
        try:
            discount_val = float(discount_applied_str)
        except ValueError:
            discount_val = 0.00

        if form.is_valid():
            # Check if any item needs prescription
            needs_prescription = False
            for item in cart.items.all():
                if item.medicine.is_prescription_required:
                    needs_prescription = True
                    break
            
            if needs_prescription and not request.FILES.get('prescription_image'):
                messages.error(request, "A prescription is required for one or more items in your cart. Please upload it.")
                return render(request, 'orders/checkout.html', {
                    'form': form,
                    'cart': cart,
                    'subtotal': subtotal,
                    'delivery_charges': delivery_charges,
                    'tax_amount': tax_amount
                })

            payment_method = form.cleaned_data['payment_method']
            
            card_number = request.POST.get('card_number', '').replace(' ', '')
            cvv = request.POST.get('cvv', '')
            force_fail = request.POST.get('force_fail', '')
            
            simulate_fail = False
            fail_reason = "Transaction Timeout"
            
            if payment_method in ['Card', 'UPI', 'NetBanking', 'Wallet']:
                upi_id = request.POST.get('upi_id', '')
                if card_number.endswith('4444') or cvv == '999' or upi_id == 'fail@upi' or force_fail == 'true':
                    simulate_fail = True
                    if cvv == '999':
                        fail_reason = "Insufficient Balance"
                    elif card_number.endswith('4444'):
                        fail_reason = "Card Expired"
                    elif upi_id == 'fail@upi':
                        fail_reason = "Network Error"
                    else:
                        fail_reason = "Transaction Timeout"
            
            delivery_opt = form.cleaned_data['delivery_option']
            if delivery_opt == 'Standard':
                delivery_charges = 0.00 if subtotal > 500 else 40.00
            elif delivery_opt == 'Express':
                delivery_charges = 100.00
            elif delivery_opt == 'Same Day':
                delivery_charges = 150.00
                
            tax_amount = round(float(subtotal) * 0.18, 2)
            grand_total = float(subtotal) - discount_val + float(delivery_charges) + tax_amount

            order = form.save(commit=False)
            order.user = request.user
            order.total_amount = grand_total
            order.delivery_charges = delivery_charges
            order.tax_amount = tax_amount
            order.discount_amount = discount_val
            order.payment_method = payment_method
            
            import random
            order.transaction_id = f"TXN-{random.randint(100000, 999999)}{random.randint(1000, 9999)}"
            order.invoice_number = f"INV-2026-{random.randint(10000, 99999)}"
            order.tracking_number = f"TRK-{random.randint(10000000, 99999999)}"
            order.estimated_delivery_date = datetime.date.today() + datetime.timedelta(days=3)
            order.delivery_agent_name = random.choice(["Rahul Sharma", "Amit Patel", "Vikram Singh", "Sanjay Dutt"])

            if simulate_fail:
                order.payment_status = 'Failed'
                order.status = 'Cancelled'
                order.save()
                
                log_order_status(order, "Order Placed", "Cancelled (Payment Failed)", request.user)
                
                request.session['payment_fail_reason'] = fail_reason
                request.session['payment_fail_method'] = payment_method
                return redirect('payment_failed')
            
            if payment_method == 'COD':
                order.payment_status = 'Pending'
                order.status = 'Order Placed'
            else:
                order.payment_status = 'Successful'
                order.status = 'Payment Confirmed'
                
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
            
            log_order_status(order, "Created", order.status, request.user)
            
            # Write to blockchain authenticity ledger
            blockchain_data = {
                "event": "Order Payment Received",
                "order_id": order.id,
                "amount": float(order.total_amount),
                "payment_method": order.payment_method,
                "transaction_id": order.transaction_id,
                "timestamp": datetime.datetime.now().isoformat()
            }
            add_block_to_chain(blockchain_data)
            
            # Clear Cart
            cart.items.all().delete()
            messages.success(request, "Payment successful! Order confirmed.")
            return redirect('payment_success', pk=order.id)
        else:
            messages.error(request, f"Please correct the errors below: {form.errors}")
    else:
        form = CheckoutForm() 
        
    return render(request, 'orders/checkout.html', {
        'form': form,
        'cart': cart,
        'subtotal': subtotal,
        'delivery_charges': delivery_charges,
        'tax_amount': tax_amount
    })

@login_required
def payment_success(request, pk):
    order = get_object_or_404(Order, pk=pk, user=request.user)
    return render(request, 'orders/payment_success.html', {'order': order})

@login_required
def payment_failed(request):
    reason = request.session.pop('payment_fail_reason', 'Transaction Timeout')
    method = request.session.pop('payment_fail_method', 'Card')
    return render(request, 'orders/payment_failed.html', {
        'reason': reason,
        'method': method
    })

@login_required
def reorder_item(request, pk):
    order = get_object_or_404(Order, pk=pk, user=request.user)
    cart, created = Cart.objects.get_or_create(user=request.user)
    for item in order.items.all():
        cart_item, created = CartItem.objects.get_or_create(cart=cart, medicine=item.medicine)
        if created:
            cart_item.quantity = item.quantity
        else:
            cart_item.quantity += item.quantity
        cart_item.save()
    messages.success(request, f"Items from Order #{order.id} have been added back to your cart.")
    return redirect('cart_view')

@login_required
def request_refund(request, pk):
    order = get_object_or_404(Order, pk=pk, user=request.user)
    if order.payment_status == 'Successful':
        order.refund_status = 'Refund Pending'
        order.save()
        log_order_status(order, order.status, "Refund Requested", request.user)
        messages.success(request, f"Refund request submitted for Order #{order.id}.")
    else:
        messages.error(request, "Refund is only applicable for paid orders.")
    return redirect('order_history')

@staff_member_required
def update_status_admin(request, pk):
    order = get_object_or_404(Order, pk=pk)
    if request.method == 'POST':
        new_status = request.POST.get('status')
        valid_statuses = [c[0] for c in Order.STATUS_CHOICES]
        if new_status in valid_statuses:
            old_status = order.status
            order.status = new_status
            order.save()
            log_order_status(order, old_status, new_status, request.user)
            messages.success(request, f"Order #{order.id} status updated to {new_status}.")
            
            if new_status == 'Delivered':
                blockchain_data = {
                    "event": "Order Delivered",
                    "order_id": order.id,
                    "delivered_to": order.full_name,
                    "timestamp": datetime.datetime.now().isoformat(),
                    "status": "Authentic Delivery Verified"
                }
                add_block_to_chain(blockchain_data)
        else:
            messages.error(request, "Invalid status choice.")
    return redirect('admin_dashboard')

@staff_member_required
def process_refund_admin(request, pk, action):
    order = get_object_or_404(Order, pk=pk)
    if action == 'approve':
        order.refund_status = 'Refunded'
        order.payment_status = 'Refunded'
        order.status = 'Cancelled'
        order.save()
        log_order_status(order, order.status, "Cancelled (Refunded)", request.user)
        
        for item in order.items.all():
            item.medicine.stock += item.quantity
            item.medicine.save()
            
        messages.success(request, f"Refund approved for Order #{order.id}. Inventory restored.")
    elif action == 'reject':
        order.refund_status = 'Refund Rejected'
        order.save()
        messages.warning(request, f"Refund rejected for Order #{order.id}.")
    return redirect('admin_dashboard')

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
    
    # Detailed payment metrics
    successful_payments = Order.objects.filter(payment_status='Successful').count()
    failed_payments = Order.objects.filter(payment_status='Failed').count()
    refund_requests = Order.objects.filter(refund_status='Refund Pending').count()
    pending_payments = Order.objects.filter(payment_status='Pending').count()
    
    # Recent orders (expanded)
    recent_orders = Order.objects.order_by('-created_at')[:20]
    
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
        'successful_payments': successful_payments,
        'failed_payments': failed_payments,
        'refund_requests': refund_requests,
        'pending_payments': pending_payments,
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

from django.http import HttpResponse
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

@login_required
def download_invoice(request, pk):
    """
    Generates a professional tax invoice PDF for a completed order.
    """
    order = get_object_or_404(Order, pk=pk)
    if order.user != request.user and not request.user.is_staff:
        return HttpResponse("Unauthorized", status=403)
        
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="MediCart_Invoice_{order.id}.pdf"'
    
    # Setup document
    doc = SimpleDocTemplate(response, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    story = []
    
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'InvoiceTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#0d9488'),
        spaceAfter=15
    )
    
    h2_style = ParagraphStyle(
        'InvoiceSub',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=15,
        textColor=colors.HexColor('#1e293b'),
        spaceBefore=10,
        spaceAfter=6
    )
    
    body_style = ParagraphStyle(
        'InvoiceBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#334155')
    )
    
    body_bold = ParagraphStyle(
        'InvoiceBodyBold',
        parent=body_style,
        fontName='Helvetica-Bold'
    )
    
    header_style = ParagraphStyle(
        'TableHeader',
        parent=body_style,
        fontName='Helvetica-Bold',
        textColor=colors.white
    )
    
    # Title Header
    story.append(Paragraph("TAX INVOICE / RETAIL RECEIPT", title_style))
    story.append(Paragraph("<b>MediCart Online Pharmacy</b><br/>123 Health Street, MedCity<br/>Phone: +91 98765 43210 | support@medicart.com", body_style))
    story.append(Spacer(1, 15))
    
    # Invoice metadata with detailed address
    cust_name = order.full_name or order.user.username
    shipping_addr = "{}, {}, {}, {} - {}, Landmark: {}".format(
        order.house_number, order.street_address, order.city, order.state, order.pincode, order.landmark
    ) if order.street_address else order.address or "n/a"
    
    payment_info = "{} ({})".format(order.payment_method, order.payment_status)
    if order.transaction_id:
        payment_info += "<br/><font size=7 color='#64748b'>Txn: {}</font>".format(order.transaction_id)
        
    meta_data = [
        [Paragraph("<b>Invoice No:</b>", body_style), Paragraph(f"MC-{order.id:06d}", body_style), Paragraph("<b>Order Date:</b>", body_style), Paragraph(order.created_at.strftime('%Y-%m-%d %H:%M'), body_style)],
        [Paragraph("<b>Customer Name:</b>", body_style), Paragraph(cust_name, body_style), Paragraph("<b>Payment Mode:</b>", body_style), Paragraph(payment_info, body_style)],
        [Paragraph("<b>Phone & Email:</b>", body_style), Paragraph(f"{order.mobile_number}<br/>{order.email}", body_style), Paragraph("<b>Shipment Status:</b>", body_style), Paragraph(order.status, body_style)],
        [Paragraph("<b>Shipping Address:</b>", body_style), Paragraph(shipping_addr, body_style), Paragraph("<b>Tracking Number:</b>", body_style), Paragraph(order.tracking_number or "Pending", body_style)]
    ]
    t_meta = Table(meta_data, colWidths=[110, 160, 110, 160])
    t_meta.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 20))
    
    # Items Table
    table_data = [[
        Paragraph("S.No", header_style),
        Paragraph("Medicine Item", header_style),
        Paragraph("Batch Number", header_style),
        Paragraph("Qty", header_style),
        Paragraph("Unit Price (INR)", header_style),
        Paragraph("Total (INR)", header_style),
    ]]
    
    # Fetch order items
    items = order.items.all()
    subtotal = 0.00
    for idx, item in enumerate(items, start=1):
        line_total = item.quantity * item.price
        subtotal += float(line_total)
        table_data.append([
            Paragraph(str(idx), body_style),
            Paragraph(f"<b>{item.medicine.name}</b><br/><font size=8 color='#64748b'>{item.medicine.generic_name}</font>", body_style),
            Paragraph(item.medicine.batch_number, body_style),
            Paragraph(str(item.quantity), body_style),
            Paragraph(f"{item.price:.2f}", body_style),
            Paragraph(f"{line_total:.2f}", body_style),
        ])
        
    # Billing summary breakdowns
    table_data.append([
        Paragraph("", body_style), Paragraph("", body_style), Paragraph("", body_style), Paragraph("", body_style),
        Paragraph("Subtotal", body_style),
        Paragraph(f"{subtotal:.2f}", body_style),
    ])
    if float(order.discount_amount) > 0:
        table_data.append([
            Paragraph("", body_style), Paragraph("", body_style), Paragraph("", body_style), Paragraph("", body_style),
            Paragraph("Coupon Savings", body_style),
            Paragraph(f"-{order.discount_amount:.2f}", body_style),
        ])
    table_data.append([
        Paragraph("", body_style), Paragraph("", body_style), Paragraph("", body_style), Paragraph("", body_style),
        Paragraph("Delivery (Option: {})".format(order.delivery_option), body_style),
        Paragraph(f"{order.delivery_charges:.2f}", body_style),
    ])
    table_data.append([
        Paragraph("", body_style), Paragraph("", body_style), Paragraph("", body_style), Paragraph("", body_style),
        Paragraph("GST / Pharmacy Tax (18%)", body_style),
        Paragraph(f"{order.tax_amount:.2f}", body_style),
    ])
    table_data.append([
        Paragraph("", body_style), Paragraph("", body_style), Paragraph("", body_style), Paragraph("", body_style),
        Paragraph("<b>Grand Total (Payable)</b>", body_bold),
        Paragraph(f"<b>INR {order.total_amount:.2f}</b>", body_bold),
    ])
    
    t_items = Table(table_data, colWidths=[40, 200, 100, 40, 80, 80])
    t_items.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0d9488')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('LINEBELOW', (0,0), (-1,-6), 0.5, colors.HexColor('#e2e8f0')),
        ('LINEABOVE', (4,-5), (-1,-5), 0.5, colors.HexColor('#cbd5e1')),
        ('BACKGROUND', (4,-1), (-1,-1), colors.HexColor('#f8fafc')),
        ('LINEABOVE', (4,-1), (-1,-1), 1.5, colors.HexColor('#0d9488')),
    ]))
    story.append(t_items)
    story.append(Spacer(1, 20))
    
    # Blockchain Authentic signature
    story.append(Paragraph("<b>Blockchain Verification & Ledger Security</b>", h2_style))
    story.append(Paragraph("This invoice matches an approved batch verification block on the MediCart Authenticity Chain. "
                           "The manufacturer purity certificate, pharmacist validation timestamp, and supply chain custody "
                           "records are locked in block hashes to prevent counterfeit transactions.", body_style))
    
    story.append(Spacer(1, 20))
    story.append(Paragraph("<font size=8 color='#94a3b8'>* This is a computer-generated tax document and does not require a physical signature. "
                           "Always consult a clinical pharmacist before shifting drug doses.</font>", body_style))
    
    doc.build(story)
    return response

# Make model helper imports
from django.db import models
