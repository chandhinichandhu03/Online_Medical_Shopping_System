from django.db import models
from django.conf import settings
from store.models import Medicine

class Cart(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Cart of {self.user.username}"
    
    @property
    def total_price(self):
        return sum(item.total_price for item in self.items.all())

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, related_name='items', on_delete=models.CASCADE)
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    
    @property
    def total_price(self):
        return self.medicine.price * self.quantity

    def __str__(self):
        return f"{self.quantity} x {self.medicine.name}"

class Order(models.Model):
    STATUS_CHOICES = (
        ('Order Placed', 'Order Placed'),
        ('Payment Confirmed', 'Payment Confirmed'),
        ('Packed', 'Packed'),
        ('Shipped', 'Shipped'),
        ('Out for Delivery', 'Out for Delivery'),
        ('Delivered', 'Delivered'),
        ('Cancelled', 'Cancelled'),
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    address = models.TextField(blank=True, default="")
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='Order Placed')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    prescription_image = models.ImageField(upload_to='prescriptions/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Billing/Shipping Details
    full_name = models.CharField(max_length=100, default="")
    mobile_number = models.CharField(max_length=15, default="")
    email = models.EmailField(default="")
    house_number = models.CharField(max_length=50, default="")
    street_address = models.CharField(max_length=255, default="")
    city = models.CharField(max_length=100, default="")
    state = models.CharField(max_length=100, default="")
    pincode = models.CharField(max_length=10, default="")
    landmark = models.CharField(max_length=100, blank=True, default="")
    
    # Delivery & Cost Details
    delivery_option = models.CharField(max_length=50, default="Standard") # Standard, Express, Same Day
    delivery_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    # Payment & Security Details
    payment_method = models.CharField(max_length=50, default="COD") # UPI, Card, Net Banking, Wallet, COD
    payment_status = models.CharField(max_length=20, default="Pending") # Pending, Successful, Failed, Refunded
    transaction_id = models.CharField(max_length=100, blank=True, default="")
    invoice_number = models.CharField(max_length=100, blank=True, default="")
    tracking_number = models.CharField(max_length=100, blank=True, default="")
    estimated_delivery_date = models.DateField(null=True, blank=True)
    delivery_agent_name = models.CharField(max_length=100, blank=True, default="Rahul Sharma")
    refund_status = models.CharField(max_length=50, default="No Refund") # No Refund, Refund Pending, Refunded, Refund Rejected

    def __str__(self):
        return f"Order #{self.id} - {self.user.username}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    
    def __str__(self):
        return f"{self.quantity} x {self.medicine.name} in Order #{self.order.id}"

class OrderAuditLog(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='audit_logs')
    status_from = models.CharField(max_length=50)
    status_to = models.CharField(max_length=50)
    timestamp = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"Order #{self.order.id} status changed from {self.status_from} to {self.status_to}"

class BlockchainBlock(models.Model):
    index = models.PositiveIntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)
    data = models.TextField(help_text="JSON serialized batch info or order authenticity data")
    previous_hash = models.CharField(max_length=64)
    hash = models.CharField(max_length=64)

    def __str__(self):
        return f"Block #{self.index} - Hash: {self.hash[:10]}..."
