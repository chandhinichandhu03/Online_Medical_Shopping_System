import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login as auth_login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth import views as auth_views
from django.contrib import messages
from django.urls import reverse_lazy
from django.utils import timezone
from .forms import CustomUserCreationForm
from .models import User, FamilyProfile, MedicationReminder
from store.models import Medicine

class CustomLoginView(auth_views.LoginView):
    template_name = 'accounts/login.html'
    
    def form_valid(self, form):
        user = form.get_user()
        if user.mfa_enabled:
            # Stage user in session for MFA check
            self.request.session['mfa_pending_user_id'] = user.id
            messages.info(self.request, "Multi-Factor Authentication required. Enter the verification code sent to your authenticator.")
            return redirect('mfa_verification')
        
        # Standard login
        auth_login(self.request, user)
        messages.success(self.request, f"Welcome back, {user.username}!")
        
        if user.role == 'Admin':
            return redirect('admin_dashboard')
        elif user.role == 'Pharmacist':
            return redirect('pharmacist_queue')
        return redirect('profile_view')

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user)
            messages.success(request, "Account created successfully!")
            
            if user.role == 'Admin':
                return redirect('admin_dashboard')
            elif user.role == 'Pharmacist':
                return redirect('pharmacist_queue')
            return redirect('profile_view')
        else:
            messages.error(request, "Please correct the details below.")
    else:
        form = CustomUserCreationForm()
    return render(request, 'accounts/register.html', {'form': form})

@login_required
def profile_view(request):
    reminders = request.user.reminders.all().order_by('time')
    family = request.user.family_members.all()
    
    # Simple Adherence rate calculations
    total_logs = 0
    taken_logs = 0
    for r in reminders:
        try:
            logs = json.loads(r.adherence_logs)
            total_logs += len(logs)
            taken_logs += sum(1 for log in logs if 'taken' in log.lower())
        except:
            pass
            
    adherence_pct = 100 if total_logs == 0 else int((taken_logs / total_logs) * 100)
    
    return render(request, 'accounts/profile.html', {
        'reminders': reminders,
        'family': family,
        'adherence_rate': adherence_pct
    })

@login_required
def profile_update(request):
    if request.method == 'POST':
        request.user.age = request.POST.get('age') or None
        request.user.gender = request.POST.get('gender')
        request.user.phone = request.POST.get('phone')
        request.user.address = request.POST.get('address')
        request.user.allergies = request.POST.get('allergies')
        request.user.medical_history = request.POST.get('medical_history')
        request.user.save()
        messages.success(request, "Profile updated successfully.")
        return redirect('profile_view')
    return redirect('profile_view')

@login_required
def family_add(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        relation = request.POST.get('relation')
        age = request.POST.get('age', 0)
        allergies = request.POST.get('allergies', '')
        history = request.POST.get('medical_history', '')
        
        FamilyProfile.objects.create(
            user=request.user,
            name=name,
            relation=relation,
            age=age,
            allergies=allergies,
            medical_history=history
        )
        messages.success(request, f"Added {name} to your family profile.")
    return redirect('profile_view')

@login_required
def family_delete(request, pk):
    member = get_object_or_404(FamilyProfile, pk=pk, user=request.user)
    name = member.name
    member.delete()
    messages.success(request, f"Removed {name} from family profile.")
    return redirect('profile_view')

@login_required
def reminder_add(request):
    if request.method == 'POST':
        med_name = request.POST.get('medicine_name')
        dosage = request.POST.get('dosage')
        time_str = request.POST.get('time')
        freq = request.POST.get('frequency', 'Daily')
        
        MedicationReminder.objects.create(
            user=request.user,
            medicine_name=med_name,
            dosage=dosage,
            time=time_str,
            frequency=freq
        )
        messages.success(request, f"Reminder set for {med_name}.")
    return redirect('profile_view')

@login_required
def reminder_delete(request, pk):
    rem = get_object_or_404(MedicationReminder, pk=pk, user=request.user)
    name = rem.medicine_name
    rem.delete()
    messages.success(request, f"Deleted reminder for {name}.")
    return redirect('profile_view')

@login_required
def reminder_log(request, pk):
    rem = get_object_or_404(MedicationReminder, pk=pk, user=request.user)
    status = request.POST.get('status', 'Taken')
    
    # Append log to JSON list
    try:
        logs = json.loads(rem.adherence_logs)
    except:
        logs = []
        
    log_entry = f"{timezone.localdate().isoformat()} - {status}"
    logs.append(log_entry)
    rem.adherence_logs = json.dumps(logs)
    rem.save()
    
    messages.success(request, f"Logged {rem.medicine_name} as {status} for today.")
    return redirect('profile_view')

def mfa_verification(request):
    user_id = request.session.get('mfa_pending_user_id')
    if not user_id:
        return redirect('login')
        
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        code = request.POST.get('code')
        # Dynamic verification mock: check if code is 123456
        if code == '123456' or code == user.mfa_secret:
            # Login successful
            auth_login(request, user)
            # Remove staging session
            del request.session['mfa_pending_user_id']
            messages.success(request, f"MFA Verified. Welcome, {user.username}!")
            
            if user.role == 'Admin':
                return redirect('admin_dashboard')
            elif user.role == 'Pharmacist':
                return redirect('pharmacist_queue')
            return redirect('profile_view')
        else:
            messages.error(request, "Invalid authentication code. Please try again (Hint: use 123456 for testing).")
            
    return render(request, 'accounts/mfa.html', {'mfa_username': user.username})

@login_required
def mfa_toggle(request):
    if request.method == 'POST':
        enabled = request.POST.get('mfa_enabled') == 'on'
        request.user.mfa_enabled = enabled
        if enabled and not request.user.mfa_secret:
            # Generate a simple mock secret
            request.user.mfa_secret = '123456'
        request.user.save()
        status_msg = "enabled" if enabled else "disabled"
        messages.success(request, f"Multi-Factor Authentication has been {status_msg}. Code for testing: 123456")
    return redirect('profile_view')
