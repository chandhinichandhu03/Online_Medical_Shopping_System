
import os

path = r'd:\Online medical shoping system using AI\templates\store\medicine_detail.html'
content = """{% extends 'base.html' %}

{% block title %}{{ medicine.name }} - MediCart{% endblock %}

{% block content %}
<div class="card border-0 shadow-sm overflow-hidden mb-5">
    <div class="row g-0">
        <div class="col-md-5 bg-light d-flex align-items-center justify-content-center p-5">
            {% if medicine.image %}
            <img src="{{ medicine.image.url }}" class="img-fluid rounded shadow-sm bg-white p-2"
                alt="{{ medicine.name }}" style="max-height: 400px;">
            {% else %}
            <i class="fas fa-pills display-1 text-muted opacity-25"></i>
            {% endif %}
        </div>
        <div class="col-md-7">
            <div class="card-body p-4 p-lg-5">
                <div class="d-flex align-items-starts justify-content-between mb-2">
                    <span
                        class="badge bg-primary-subtle text-primary border border-primary-subtle px-3 py-2 rounded-pill mb-3">{{
                        medicine.category.name }}</span>
                    {% if medicine.is_prescription_required %}
                    <span
                        class="badge bg-danger-subtle text-danger border border-danger-subtle px-3 py-2 rounded-pill mb-3"><i
                            class="fas fa-file-prescription me-1"></i> Prescription Required</span>
                    {% else %}
                    <span
                        class="badge bg-success-subtle text-success border border-success-subtle px-3 py-2 rounded-pill mb-3"><i
                            class="fas fa-check me-1"></i> OTC Approved</span>
                    {% endif %}
                </div>

                <h1 class="display-5 fw-bold mb-1">{{ medicine.name }}</h1>
                <p class="text-muted fs-5 mb-4">By {{ medicine.brand_name }}</p>

                <h3 class="text-primary fw-bold mb-4">₹{{ medicine.price }}</h3>

                <p class="lead mb-4" style="font-size: 1rem;">{{ medicine.description }}</p>

                <div class="row g-3 mb-4">
                    <div class="col-6 col-md-4">
                        <div class="p-3 border rounded bg-light text-center">
                            <i class="fas fa-calendar-alt text-muted mb-2"></i>
                            <div class="small text-muted">Expiry Date</div>
                            <div class="fw-bold">{{ medicine.expiry_date }}</div>
                        </div>
                    </div>
                    <div class="col-6 col-md-4">
                        <div class="p-3 border rounded bg-light text-center">
                            <i class="fas fa-boxes text-muted mb-2"></i>
                            <div class="small text-muted">Stock Status</div>
                            <div
                                class="fw-bold {% if medicine.stock > 0 %}text-success{% else %}text-danger{% endif %}">
                                {% if medicine.stock > 0 %}{{ medicine.stock }} Available{% else %}Out of Stock{% endif %}
                            </div>
                        </div>
                    </div>
                </div>

                {% if medicine.stock > 0 %}
                <form action="{% url 'add_to_cart' medicine.pk %}" method="post"
                    class="d-flex align-items-center gap-3 mt-4">
                    {% csrf_token %}
                    <div class="input-group" style="width: 130px;">
                        <button class="btn btn-outline-secondary" type="button"
                            onclick="this.parentNode.querySelector('input[type=number]').stepDown()">-</button>
                        <input type="number" name="quantity" class="form-control text-center border-secondary" value="1"
                            min="1" max="{{ medicine.stock }}">
                        <button class="btn btn-outline-secondary" type="button"
                            onclick="this.parentNode.querySelector('input[type=number]').stepUp()">+</button>
                    </div>
                    <button type="submit" class="btn btn-primary btn-lg rounded-pill px-5 flex-grow-1 shadow-sm">
                        <i class="fas fa-cart-plus me-2"></i> Add to Cart
                    </button>
                </form>
                {% else %}
                <button class="btn btn-secondary btn-lg w-100 rounded-pill disabled" disabled>Currently
                    Unavailable</button>
                {% if user.is_staff %}
                <a href="/admin/store/medicine/{{ medicine.pk }}/change/"
                    class="btn btn-warning w-100 rounded-pill mt-2">Restock (Admin)</a>
                {% endif %}
                {% endif %}
            </div>
        </div>
    </div>
</div>
{% endblock %}
"""

if os.path.exists(path):
    os.remove(path)
with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print('File overwritten successfully')
