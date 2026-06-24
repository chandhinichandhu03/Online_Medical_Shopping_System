from django.test import TestCase, Client
from django.urls import reverse
from store.models import Medicine, Category, DrugInteraction
from ai_health.views import markdown_to_html, local_chat_fallback
import datetime
import json
from unittest.mock import patch, MagicMock

class AIHealthViewsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.category, _ = Category.objects.get_or_create(name="Analgesics")
        self.medicine_calpol = Medicine.objects.create(
            category=self.category,
            name="Calpol 650",
            brand_name="GlaxoSmithKline",
            generic_name="Paracetamol",
            active_ingredient="Paracetamol",
            price=30.00,
            original_price=30.00,
            stock=100,
            expiry_date=datetime.date.today() + datetime.timedelta(days=365),
            description="Fever and pain relief tablet."
        )
        self.medicine_aspirin = Medicine.objects.create(
            category=self.category,
            name="Aspirin Cardio",
            brand_name="Bayer",
            generic_name="Aspirin",
            active_ingredient="Aspirin",
            price=50.00,
            original_price=50.00,
            stock=50,
            expiry_date=datetime.date.today() + datetime.timedelta(days=365),
            description="Heart health aspirin tablet."
        )
        self.medicine_ibuprofen = Medicine.objects.create(
            category=self.category,
            name="Ibuprofen 400",
            brand_name="Abbott",
            generic_name="Ibuprofen",
            active_ingredient="Ibuprofen",
            price=25.00,
            original_price=25.00,
            stock=80,
            expiry_date=datetime.date.today() + datetime.timedelta(days=365),
            description="Pain relief and anti-inflammatory."
        )
        self.interaction = DrugInteraction.objects.create(
            ingredient_a="aspirin",
            ingredient_b="ibuprofen",
            severity="Severe",
            effect="Stomach bleeding and ulcers risk."
        )

    def test_markdown_to_html_formatting(self):
        # Bold
        self.assertIn("<strong>bold</strong>", markdown_to_html("This is **bold**"))
        # Italic
        self.assertIn("<em>italic</em>", markdown_to_html("This is *italic*"))
        # Header
        self.assertIn('<h5 class="fw-bold mt-3 text-primary">Test Header</h5>', markdown_to_html("### Test Header"))
        # List
        html_list = markdown_to_html("- Item 1\n- Item 2")
        self.assertIn('<ul class="list-group list-group-flush mb-3">', html_list)
        self.assertIn("Item 1", html_list)
        self.assertIn("Item 2", html_list)

    def test_local_chat_fallback_routing(self):
        # 1. Test drug interaction triggers interaction message, not general medicine listing
        query = "Drug interaction warnings (e.g. Aspirin + Ibuprofen)"
        response = local_chat_fallback(query)
        self.assertIn("drug safety/interactions", response)
        self.assertNotIn("We currently stock", response) # should not match general medicine stock
        
        # 2. Test symptoms trigger symptom fallback
        query = "I have a headache and fever"
        response = local_chat_fallback(query)
        self.assertIn("symptoms related to pain, cough, or fever", response)
        
        # 3. Test generic medicine triggers stock listing
        query = "Do you have any drugs or medicines in stock?"
        response = local_chat_fallback(query)
        self.assertIn("We currently stock", response)
        self.assertNotIn("drug safety/interactions", response)

    @patch('ai_health.views.search_similar_documents')
    @patch('ai_health.views.query_local_ollama')
    def test_symptom_checker_ai_success(self, mock_query, mock_search):
        # Test case where Ollama runs and successfully returns a valid JSON response
        mock_search.return_value = []
        mock_query.return_value = json.dumps({
            "conditions": ["Upper Respiratory Tract Infection (Common Cold)"],
            "advice": ["Keep throat hydrated by sipping warm water throughout the day.", "Inhale steam with eucalyptus oil twice daily."],
            "remedies": ["Mix honey, ginger juice, and black pepper, and consume 1 teaspoon."],
            "medicines": [
                {"name": "Benadryl Syrup", "reason": "Soothing dry cough"},
                {"name": "Cofsils Syrup", "reason": "Relief for dry cough"}
            ]
        })

        response = self.client.post(reverse('symptom_checker'), {
            'age': 30,
            'gender': 'male',
            'symptoms': 'I have a sore throat and bad cough'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Upper Respiratory Tract Infection (Common Cold)")
        self.assertContains(response, "Keep throat hydrated")
        self.assertNotContains(response, "{{ tip }}")
        self.assertNotContains(response, "{{ item }}")

    @patch('ai_health.views.search_similar_documents')
    @patch('ai_health.views.query_local_ollama')
    def test_symptom_checker_fallback(self, mock_query, mock_search):
        # Test case where Ollama fails/is offline and system falls back to rule-based symptom analyzer
        mock_search.return_value = []
        mock_query.return_value = "Error connecting to local Ollama server: Connection refused"

        response = self.client.post(reverse('symptom_checker'), {
            'age': 30,
            'gender': 'male',
            'symptoms': 'I have a bad cough and cold'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Upper Respiratory Tract Infection (Common Cold)")
        self.assertContains(response, "Keep throat hydrated")
        self.assertNotContains(response, "{{ tip }}")
        self.assertNotContains(response, "{{ item }}")

    def test_doctor_chat_get(self):
        # Verify doctor chat view loads correctly
        response = self.client.get(reverse('doctor_chat'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dr. Llama")

    @patch('ai_health.views.search_similar_documents')
    @patch('ai_health.views.query_local_ollama')
    def test_doctor_chat_post_message(self, mock_query, mock_search):
        # Mock search results and Ollama output to avoid live local REST calls
        mock_search.return_value = []
        mock_query.return_value = "As a clinical AI assistant, I recommend taking Paracetamol as prescribed."

        response = self.client.post(reverse('doctor_chat'), {
            'message': 'What is the correct dose of Paracetamol?'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dr. Llama")
        self.assertContains(response, "recommend taking Paracetamol")

