from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from store.models import Category, Medicine
from orders.models import Cart, CartItem, Order, OrderItem, OrderAuditLog, BlockchainBlock
import datetime
import json

User = get_user_model()

class OrdersSystemTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="password123", email="test@example.com")
        
        # In custom User save(), superuser status is only set/maintained if role is 'Admin'
        self.staff_user = User.objects.create_superuser(
            username="adminuser", 
            password="password123", 
            email="admin@example.com",
            role="Admin"
        )
        
        self.category = Category.objects.create(name="Tablets")
        
        self.med_normal = Medicine.objects.create(
            category=self.category,
            name="Paracetamol 500mg",
            brand_name="Generic",
            price=20.00,
            original_price=20.00,
            stock=100,
            expiry_date=datetime.date.today() + datetime.timedelta(days=100),
            is_prescription_required=False,
            description="Pain relief"
        )
        
        self.med_rx = Medicine.objects.create(
            category=self.category,
            name="Azithromycin 500mg",
            brand_name="GenericRx",
            price=120.00,
            original_price=120.00,
            stock=50,
            expiry_date=datetime.date.today() + datetime.timedelta(days=120),
            is_prescription_required=True,
            description="Antibiotic"
        )

    def login_user(self):
        self.client.login(username="testuser", password="password123")

    def login_admin(self):
        self.client.login(username="adminuser", password="password123")

    def test_cart_operations(self):
        self.login_user()
        
        # Add to cart
        response = self.client.post(reverse('add_to_cart', args=[self.med_normal.id]), {'quantity': 3})
        self.assertEqual(response.status_code, 302) # redirects to cart_view
        
        cart = Cart.objects.get(user=self.user)
        self.assertEqual(cart.items.count(), 1)
        item = cart.items.first()
        self.assertEqual(item.medicine, self.med_normal)
        self.assertEqual(item.quantity, 3)
        
        # Test cart view
        response = self.client.get(reverse('cart_view'))
        self.assertEqual(response.status_code, 200)
        
        # Remove from cart
        response = self.client.get(reverse('remove_from_cart', args=[item.id]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(cart.items.count(), 0)

    def test_checkout_get(self):
        self.login_user()
        
        # When cart is empty
        response = self.client.get(reverse('checkout'))
        self.assertEqual(response.status_code, 302) # Redirects to medicine_list
        
        # With items in cart
        self.client.post(reverse('add_to_cart', args=[self.med_normal.id]), {'quantity': 2})
        response = self.client.get(reverse('checkout'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Paracetamol 500mg")

    def test_checkout_success_cod(self):
        self.login_user()
        self.client.post(reverse('add_to_cart', args=[self.med_normal.id]), {'quantity': 2})
        
        checkout_data = {
            'full_name': 'Ashok Kumar',
            'mobile_number': '9876543210',
            'email': 'ashok@example.com',
            'house_number': '12B',
            'street_address': 'Main Street',
            'city': 'Chennai',
            'state': 'Tamil Nadu',
            'pincode': '600001',
            'landmark': 'Near Hospital',
            'delivery_option': 'Standard',
            'payment_method': 'COD'
        }
        
        response = self.client.post(reverse('checkout'), checkout_data)
        
        # Should redirect to payment success
        orders = Order.objects.filter(user=self.user)
        self.assertEqual(orders.count(), 1)
        order = orders.first()
        self.assertEqual(order.payment_method, 'COD')
        self.assertEqual(order.payment_status, 'Pending')
        self.assertEqual(order.status, 'Order Placed')
        self.assertEqual(order.items.count(), 1)
        
        # Check stock deduction
        self.med_normal.refresh_from_db()
        self.assertEqual(self.med_normal.stock, 98)
        
        # Cart should be cleared
        cart = Cart.objects.get(user=self.user)
        self.assertEqual(cart.items.count(), 0)
        
        # Redirect assert
        self.assertRedirects(response, reverse('payment_success', args=[order.id]))

    def test_checkout_success_card(self):
        self.login_user()
        self.client.post(reverse('add_to_cart', args=[self.med_normal.id]), {'quantity': 1})
        
        checkout_data = {
            'full_name': 'Ashok Kumar',
            'mobile_number': '9876543210',
            'email': 'ashok@example.com',
            'house_number': '12B',
            'street_address': 'Main Street',
            'city': 'Chennai',
            'state': 'Tamil Nadu',
            'pincode': '600001',
            'landmark': 'Near Hospital',
            'delivery_option': 'Express',
            'payment_method': 'Card',
            'card_number': '4532 0122 3444 8888',
            'cvv': '123'
        }
        
        response = self.client.post(reverse('checkout'), checkout_data)
        
        orders = Order.objects.filter(user=self.user)
        self.assertEqual(orders.count(), 1)
        order = orders.first()
        self.assertEqual(order.payment_method, 'Card')
        self.assertEqual(order.payment_status, 'Successful')
        self.assertEqual(order.status, 'Payment Confirmed')
        self.assertRedirects(response, reverse('payment_success', args=[order.id]))

    def test_checkout_fail_expired_card(self):
        self.login_user()
        self.client.post(reverse('add_to_cart', args=[self.med_normal.id]), {'quantity': 1})
        
        checkout_data = {
            'full_name': 'Ashok Kumar',
            'mobile_number': '9876543210',
            'email': 'ashok@example.com',
            'house_number': '12B',
            'street_address': 'Main Street',
            'city': 'Chennai',
            'state': 'Tamil Nadu',
            'pincode': '600001',
            'landmark': 'Near Hospital',
            'delivery_option': 'Standard',
            'payment_method': 'Card',
            'card_number': '4532 0122 3444 4444', # ends with 4444 -> failure card
            'cvv': '123'
        }
        
        # Use follow=True so we follow the redirect to payment_failed and get the first load session variables intact
        response = self.client.post(reverse('checkout'), checkout_data, follow=True)
        self.assertRedirects(response, reverse('payment_failed'))
        self.assertContains(response, "Card Expired")

    def test_checkout_prescription_required(self):
        self.login_user()
        # Add a medicine that requires prescription
        self.client.post(reverse('add_to_cart', args=[self.med_rx.id]), {'quantity': 1})
        
        checkout_data = {
            'full_name': 'Ashok Rx',
            'mobile_number': '9876543210',
            'email': 'ashok@example.com',
            'house_number': '12B',
            'street_address': 'Main Street',
            'city': 'Chennai',
            'state': 'Tamil Nadu',
            'pincode': '600001',
            'landmark': 'Near Hospital',
            'delivery_option': 'Standard',
            'payment_method': 'COD'
        }
        
        # Post checkout WITHOUT prescription image
        response = self.client.post(reverse('checkout'), checkout_data)
        self.assertEqual(response.status_code, 200) # Re-renders checkout template
        self.assertContains(response, "A prescription is required for one or more items in your cart")
        
        # 1x1 transparent GIF bytes to pass ImageField validator in Django
        minimal_gif = (
            b'GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff'
            b'!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00'
            b'\x00\x02\x02D\x01\x00;'
        )
        fake_image = SimpleUploadedFile("prescription.gif", minimal_gif, content_type="image/gif")
        checkout_data['prescription_image'] = fake_image
        
        response = self.client.post(reverse('checkout'), checkout_data)
        
        self.assertEqual(Order.objects.filter(user=self.user).count(), 1)
        order = Order.objects.first()
        self.assertRedirects(response, reverse('payment_success', args=[order.id]))

    def test_order_tracking_and_blockchain(self):
        self.login_user()
        order = Order.objects.create(
            user=self.user,
            total_amount=150.00,
            status='Order Placed',
            payment_status='Successful',
            payment_method='Card',
            transaction_id='TXN-123456'
        )
        OrderItem.objects.create(order=order, medicine=self.med_normal, quantity=2, price=20.00)
        
        # Renders delivery tracking (Dijkstra)
        response = self.client.get(reverse('order_tracking', args=[order.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Order Transit Tracker")
        
        # Renders blockchain authenticity ledger
        response = self.client.get(reverse('blockchain_ledger'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Drug Authenticity Blockchain")

    def test_reorder_item(self):
        self.login_user()
        order = Order.objects.create(
            user=self.user,
            total_amount=40.00,
            status='Delivered',
            payment_status='Successful'
        )
        OrderItem.objects.create(order=order, medicine=self.med_normal, quantity=2, price=20.00)
        
        response = self.client.get(reverse('reorder_item', args=[order.id]))
        self.assertRedirects(response, reverse('cart_view'))
        
        # Cart should have the items now
        cart = Cart.objects.get(user=self.user)
        self.assertEqual(cart.items.count(), 1)
        self.assertEqual(cart.items.first().medicine, self.med_normal)
        self.assertEqual(cart.items.first().quantity, 2)

    def test_request_refund(self):
        self.login_user()
        order = Order.objects.create(
            user=self.user,
            total_amount=40.00,
            status='Delivered',
            payment_status='Successful'
        )
        
        response = self.client.get(reverse('request_refund', args=[order.id]))
        self.assertRedirects(response, reverse('order_history'))
        
        order.refresh_from_db()
        self.assertEqual(order.refund_status, 'Refund Pending')

    def test_admin_dashboard_operations(self):
        self.login_admin()
        
        order = Order.objects.create(
            user=self.user,
            total_amount=200.00,
            status='Order Placed',
            payment_status='Successful',
            refund_status='Refund Pending'
        )
        OrderItem.objects.create(order=order, medicine=self.med_normal, quantity=1, price=20.00)
        
        # View dashboard
        response = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(response.status_code, 200)
        
        # Update Status Admin
        response = self.client.post(reverse('update_status_admin', args=[order.id]), {'status': 'Shipped'})
        self.assertRedirects(response, reverse('admin_dashboard'))
        order.refresh_from_db()
        self.assertEqual(order.status, 'Shipped')
        
        # Approve Refund Admin
        response = self.client.get(reverse('process_refund_admin', args=[order.id, 'approve']))
        self.assertRedirects(response, reverse('admin_dashboard'))
        order.refresh_from_db()
        self.assertEqual(order.refund_status, 'Refunded')
        self.assertEqual(order.status, 'Cancelled')

    def test_download_invoice(self):
        self.login_user()
        order = Order.objects.create(
            user=self.user,
            total_amount=20.00,
            status='Payment Confirmed',
            payment_status='Successful',
            payment_method='Card',
            full_name='Ashok Kumar',
            mobile_number='9876543210',
            email='ashok@example.com',
            house_number='12B',
            street_address='Main Road',
            city='Chennai',
            state='Tamil Nadu',
            pincode='600001'
        )
        OrderItem.objects.create(order=order, medicine=self.med_normal, quantity=1, price=20.00)
        
        response = self.client.get(reverse('download_invoice', args=[order.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(len(response.content) > 0)
