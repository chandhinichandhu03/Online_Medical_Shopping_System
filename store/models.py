from django.db import models
from django.utils.text import slugify
from django.conf import settings
import datetime

class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = "Categories"

class Medicine(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    brand_name = models.CharField(max_length=200, blank=True)
    generic_name = models.CharField(max_length=200, blank=True, default="")
    active_ingredient = models.CharField(max_length=200, blank=True, default="")
    image = models.ImageField(upload_to='medicines/', blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    original_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.0) # Base price before dynamic pricing
    discount_percent = models.PositiveIntegerField(default=0)
    is_featured = models.BooleanField(default=False)
    rating = models.FloatField(default=4.0)
    review_count = models.PositiveIntegerField(default=0)
    medicine_type = models.CharField(max_length=20, default="tablet")
    stock = models.PositiveIntegerField(default=0)
    expiry_date = models.DateField()
    manufactured_date = models.DateField(default=datetime.date.today)
    batch_number = models.CharField(max_length=50, default="BATCH-001")
    warehouse_location = models.CharField(max_length=50, default="Row A / Shelf 1")
    demand_factor = models.FloatField(default=1.0)
    description = models.TextField()
    is_prescription_required = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    wishlist_users = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='wishlist_medicines', blank=True)
    
    def save(self, *args, **kwargs):
        if not self.original_price or self.original_price == 0:
            self.original_price = self.price
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.brand_name})"

class PositiveThought(models.Model):
    text = models.TextField()
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.text[:50]

class DrugInteraction(models.Model):
    ingredient_a = models.CharField(max_length=200, help_text="Generic active ingredient A (lowercase)")
    ingredient_b = models.CharField(max_length=200, help_text="Generic active ingredient B (lowercase)")
    severity = models.CharField(max_length=20, choices=(('Mild', 'Mild'), ('Moderate', 'Moderate'), ('Severe', 'Severe')), default='Moderate')
    effect = models.TextField(help_text="Detailed description of the negative interaction")

    def __str__(self):
        return f"Interaction: {self.ingredient_a} + {self.ingredient_b} ({self.severity})"

class SubscriptionOrder(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='subscriptions')
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    frequency_days = models.PositiveIntegerField(default=30, help_text="Days between automatic deliveries (e.g. 30)")
    next_delivery_date = models.DateField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Subscription of {self.medicine.name} every {self.frequency_days} days for {self.user.username}"
