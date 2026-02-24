from django.shortcuts import render, redirect
from django.http import JsonResponse
from .models import *
from django.db.models import Count
from django.db.models import Q
from decimal import Decimal, InvalidOperation
from django.contrib.auth.hashers import make_password, check_password
from django.db.models.functions import Random
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404
import random, time
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.models import User




def _parse_decimal(value: str | None):
    if value is None:
        return None
    value = str(value).strip()
    if not value:
        return None
    try:
        return Decimal(value)
    except (InvalidOperation, ValueError):
        return None


def _filtered_products_context(request):
    if "user_id" in request.session:
        user_name=request.session.get("user_name")  
    else:
        user_name="Welcome please Login"

    products = Product.objects.all()
    contacts=Contact.objects.first()
    category_ids = request.GET.getlist("category")
    category_param = request.GET.get("category") or request.GET.get("category_name")
    color_param = request.GET.get("color") or request.GET.get("color_name")
    min_price = _parse_decimal(request.GET.get("min_price"))
    max_price = _parse_decimal(request.GET.get("max_price"))

    # category filter: multiple (checkboxes) or single (links)
    selected_category_ids = set()
    if category_ids:
        valid_ids = [int(cid) for cid in category_ids if str(cid).strip().isdigit()]
        if valid_ids:
            selected_category_ids = set(valid_ids)
            products = products.filter(category_id__in=valid_ids)
    elif category_param:
        category_param = str(category_param).strip()
        if category_param.isdigit():
            products = products.filter(category_id=int(category_param))
            selected_category_ids = {int(category_param)}
        else:
            products = products.filter(category__name__iexact=category_param)

    # color filter (supports id or name)
    if color_param:
        color_param = str(color_param).strip()
        if color_param.isdigit():
            products = products.filter(color_id=int(color_param))
        else:
            products = products.filter(color__name__iexact=color_param)

    # price filter
    if min_price is not None:
        products = products.filter(price__gte=min_price)
    if max_price is not None:
        products = products.filter(price__lte=max_price)

    categories = Category.objects.annotate(count=Count("product"))
    colors = Color.objects.annotate(count=Count("product"))
    paginator = Paginator(products, 12)
    page_number = request.GET.get("page",1)
    try:
        page_number = int(page_number)
    except ValueError:
        page_number = 1 
    products = paginator.get_page(page_number)
    show_page=paginator.get_elided_page_range(page_number,on_each_side=1,on_ends=1)
    get_copy = request.GET.copy()
    if "page" in get_copy:
        del get_copy["page"]
    query_string = get_copy.urlencode()
    return {
        "products": products,
        "pid": products,  # template expects `pid`
        "categories": categories,
        "colors": colors,
        "selected_category": category_param or "",
        "selected_category_ids": selected_category_ids,
        "selected_color": color_param or "",
        "min_price": "" if min_price is None else str(min_price),
        "max_price": "" if max_price is None else str(max_price),
        "contacts":contacts,
        "show_page":show_page,
        "query_string": query_string,
        "user_name":user_name
    }

def product_list(request):
    # Keep /products/ working; use the existing shop template + filtering sidebar.
    context = _filtered_products_context(request)
    return render(request, "shop.html", context)







# Create your views here.
def index(request):
    contacts = Contact.objects.first()
    products = Product.objects.all()
    new_arrivals_products = Product.objects.all().order_by('-date')
    categories = Category.objects.annotate(count=Count("product"))
    paginator = Paginator(products,12)
    page_number = request.GET.get("page",1)
    if "user_id" in request.session:
        user_name=request.session.get("user_name")  
    else:
        user_name="Welcome please Login"
    # print(user_name)

    try:
        page_number = int(page_number)
    except ValueError:
        page_number = 1 
    products = paginator.get_page(page_number)
    show_page=paginator.get_elided_page_range(page_number,on_each_side=1,on_ends=1)
    return render(request, "index.html", {
    "contacts": contacts,
    "products": products,
    "new_arrivals_products": new_arrivals_products,
    "categories": categories,
    "show_page":show_page,
    "user_name":user_name
    })
    # return render(request,"index.html")

def shop(request):
    context= _filtered_products_context(request)
    return render(request, "shop.html",context)
def single(request):
    if "user_id" in request.session:
        user_name=request.session.get("user_name")  
    else:
        user_name="Welcome please Login"
    id=request.GET.get("product")
    product = Product.objects.order_by('-date').first()
    if id:
        product = get_object_or_404(Product, id=id)
    categories = Category.objects.annotate(count=Count("product"))
    contacts=Contact.objects.first()
    colors = Color.objects.annotate(count=Count("product"))
    return render(request,"single.html",{
        "contacts":contacts,
        "categories":categories,
        "user_name":user_name,
        "product":product,
        "colors":colors
        })

def bestseller(request):
    if "user_id" in request.session:
        user_name=request.session.get("user_name")  
    else:
        user_name="Welcome please Login"
    products = Product.objects.order_by(Random())
    contacts = Contact.objects.first()
    categories = Category.objects.annotate(count=Count("product"))
    new_arrivals_products = Product.objects.order_by('-date')[:8]
    return render(request, "bestseller.html", {
        "contacts": contacts,
        "products": products,
        "categories": categories,
        "new_arrivals_products": new_arrivals_products,
        "user_name":user_name
    })

def _get_cart(request):
    """Get cart from session (list of dicts: name, model, price, quantity)."""
    if 'cart' not in request.session:
        request.session['cart'] = []
    raw = request.session['cart']
    # Ensure all items are dicts (filter out corrupted/old-format entries)
    valid = [x for x in raw if isinstance(x, dict)]
    if len(valid) != len(raw):
        request.session['cart'] = valid
        request.session.modified = True
    return request.session['cart']

def add_to_cart(request):
    if request.method != 'POST':
        return redirect('cart')
    name = request.POST.get('name', 'Product').strip()
    price = request.POST.get('price', '0').strip()
    model = request.POST.get('model', '').strip()
    try:
        quantity = int(request.POST.get('quantity', 1))
    except ValueError:
        quantity = 1
    if quantity < 1:
        quantity = 1
    try:
        price_float = float(price.replace(',', ''))
    except ValueError:
        price_float = 0.0
    cart = _get_cart(request)
    # Match by name + model to update quantity (only dict items)
    for item in cart:
        if not isinstance(item, dict):
            continue
        if item.get('name') == name and item.get('model') == model:
            item['quantity'] = item.get('quantity', 0) + quantity
            break
    else:
        cart.append({
            'name': name,
            'model': model,
            'price': price_float,
            'quantity': quantity,
        })
    request.session.modified = True
    return redirect('cart')

def remove_from_cart(request):
    if request.method != 'POST':
        return redirect('cart')
    try:
        index = int(request.POST.get('index', -1))
    except ValueError:
        return redirect('cart')
    cart = _get_cart(request)
    if 0 <= index < len(cart):
        cart.pop(index)
        request.session.modified = True
    return redirect('cart')

def cart(request):
    if "user_id" in request.session:
        categories = Category.objects.annotate(count=Count("product"))
        contacts=Contact.objects.first()
        cart_items = _get_cart(request)
        user_name=request.session.get("user_name") 
        # Only process dict items (ignore corrupted/old session data)
        valid_items = [item for item in cart_items if isinstance(item, dict)]
        for item in valid_items:
            item['total'] = item.get('price', 0) * item.get('quantity', 0)
        cart_total = sum(item['total'] for item in valid_items)
        return render(request, "cart.html", {
            "contacts":contacts,
            'cart_items': valid_items,
            'cart_total': cart_total,
            "categories":categories,
            "user_name":user_name
        })
    else:
        return redirect("login")

def cheackout(request):
    if "user_id" in request.session:
        contacts=Contact.objects.first()
        user_name=request.session.get("user_name") 
        categories = Category.objects.annotate(count=Count("product"))
        return render(request,"cheackout.html",{"contacts":contacts,"categories":categories,"user_name":user_name})
    else:
        return redirect("login")

def error(request):
    if "user_id" in request.session:
        user_name=request.session.get("user_name")  
    else:
        user_name="Welcome please Login"
    contacts=Contact.objects.first()
    categories = Category.objects.annotate(count=Count("product"))
    return render(request,"404.html",{"contacts":contacts,"categories":categories,"user_name":user_name})

def contact(request):
    if "user_id" in request.session:
        contacts=Contact.objects.first()
        user_name=request.session.get("user_name") 
        categories = Category.objects.annotate(count=Count("product"))
        return render(request,"contact.html",{"contacts":contacts,"categories":categories,"user_name":user_name})
    else:
        return redirect("login")

def register(request):
    error = None
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        phoneno = request.POST.get('phoneno', '').strip()
        password = request.POST.get('password', '')
        confirmpassword = request.POST.get('confirmpassword', '')
        if not name or not email or not phoneno or not password or not confirmpassword:
            error = "All fields are required."
        elif password != confirmpassword:
            error = "Password and Confirm Password do not match."
        elif AppUser.objects.filter(email=email).exists():
            error = "Email already registered."
        elif AppUser.objects.filter(phoneno=phoneno).exists():
            error = "Phone number already registered."
        else:
            AppUser.objects.create(
                name=name,
                email=email,
                phoneno=phoneno,
                password=make_password(password),
            )
            return redirect('login')
    return render(request, "register.html", {"error": error})


def login(request):
    error = None
    if request.method == 'POST':
        email_or_phone = request.POST.get('email_or_phone', '').strip()
        password = request.POST.get('password', '')
        if not email_or_phone or not password:
            error = "Email/Phone and Password are required."
        else:
            user = AppUser.objects.filter(
                Q(email=email_or_phone) | Q(phoneno=email_or_phone)
            ).first()
            if user and check_password(password, user.password):
                request.session['user_id'] = user.id
                request.session['user_name'] = user.name
                return redirect('index')
            else:
                error = "Invalid email/phone or password."
    return render(request, "login.html", {"error": error})


def logout(request):
    request.session.pop('user_id', None)
    request.session.pop('user_name', None)
    return redirect('index')


def profile(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')
    try:
        user = AppUser.objects.get(id=user_id)
    except AppUser.DoesNotExist:
        request.session.pop('user_id', None)
        request.session.pop('user_name', None)
        return redirect('login')
    error = None
    success = None
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        phoneno = request.POST.get('phoneno', '').strip()
        profile_image = request.FILES.get('profile_image')
        if not name or not email or not phoneno:
            error = "Name, email and phone are required."
        elif AppUser.objects.filter(email=email).exclude(id=user.id).exists():
            error = "Email already in use."
        elif AppUser.objects.filter(phoneno=phoneno).exclude(id=user.id).exists():
            error = "Phone number already in use."
        else:
            user.name = name
            user.email = email
            user.phoneno = phoneno
            if profile_image:
                user.profile_image = profile_image
            user.save()
            request.session['user_name'] = user.name
            success = "Profile updated successfully."
    return render(request, "profile.html", {"user": user, "error": error, "success": success})

import random
from django.contrib.auth.hashers import make_password
from django.core.mail import send_mail
from django.shortcuts import render, redirect

def forgot(request):
    context = {}

    if request.method == "POST":

        # -------- SEND OTP --------
        if "send_otp" in request.POST:
            email = request.POST.get("email", "").strip()

            if not email:
                context["error"] = "Email is required"
                return render(request, "forgot.html", context)

            if not AppUser.objects.filter(email=email).exists():
                context["error"] = "Email not registered"
                return render(request, "forgot.html", context)

            otp = random.randint(100000, 999999)

            request.session["reset_email"] = email
            request.session["reset_otp"] = str(otp)
            request.session["otp_time"] = time.time()

            send_mail(
                "Password Reset OTP",
                f"Your OTP is {otp}",
                settings.EMAIL_HOST_USER,
                [email],
            )

            context["message"] = "OTP sent to your email"
            context["otp_sent"] = True
            return render(request, "forgot.html", context)

        # -------- VERIFY OTP --------
        if "verify_otp" in request.POST:
            entered_otp = request.POST.get("otp", "").strip()
            new_password = request.POST.get("new_password", "")
            confirm_password = request.POST.get("confirm_password", "")

            session_otp = request.session.get("reset_otp")
            email = request.session.get("reset_email")
            otp_time = request.session.get("otp_time")

            if not (session_otp and email and otp_time):
                context["error"] = "OTP session expired. Please request a new OTP."
                return render(request, "forgot.html", context)

            # OTP expiry check (5 minutes)
            if time.time() - otp_time > 300:
                context["error"] = "OTP expired. Please request a new OTP."
                return render(request, "forgot.html", context)

            if entered_otp != session_otp:
                context["error"] = "Invalid OTP"
                context["otp_sent"] = True
                return render(request, "forgot.html", context)

            if not new_password or new_password != confirm_password:
                context["error"] = "Passwords do not match"
                context["otp_sent"] = True
                return render(request, "forgot.html", context)

            try:
                user = AppUser.objects.get(email=email)
            except AppUser.DoesNotExist:
                context["error"] = "User not found"
                return render(request, "forgot.html", context)

            user.password = make_password(new_password)
            user.save()

            # Clear reset-related session keys
            for key in ("reset_email", "reset_otp", "otp_time"):
                if key in request.session:
                    del request.session[key]

            context["message"] = "Password reset successful. You can now login."
            return render(request, "forgot.html", context)

    return render(request, "forgot.html", context)
    
# def forgot(request):
#     if request.method == "POST":
#         if 'otp' in request.POST:
#             # Step 2: Verify OTP and change password
#             otp = request.POST.get('otp')
#             new_password = request.POST.get('new_password')
#             confirm_password = request.POST.get('confirm_password')
#             user_id = request.session.get('reset_user_id')
#             if not user_id:
#                 return redirect('forgot_password')
#             user = User.objects.get(id=user_id)
#             if str(user.forgot_password) == otp:
#                 if new_password == confirm_password:
#                     user.password = new_password
#                     user.forgot_password = None
#                     user.save()
#                     del request.session['reset_user_id']
#                     return render(request, "login.html", {"msg": "Your password changed successfully. Please login."})
#                 else:
#                     return render(request, "forgot.html", {"show_otp_form": True, "msg": "Passwords do not match"})
#             else:
#                 return render(request, "forgot.html", {"show_otp_form": True, "msg": "Invalid OTP"})
#         else:
#             # Step 1: Send OTP
#             identifier = request.POST.get('identifier')
#             try:
#                 if '@' in identifier:
#                     user = User.objects.get(email=identifier)
#                     otp = random.randint(1000, 9999)
#                     user.forgot_password = otp
#                     user.save()
#                     request.session['reset_user_id'] = user.id
#                     # Send OTP via email
#                     send_mail(
#                         'Forgot Password OTP',
#                         f'Your OTP for password reset is {otp}.',
#                         'your_gmail@gmail.com',  # Replace with your sender email
#                         [user.email],
#                         fail_silently=False,
#                     )
#                     msg = "OTP sent to your email."
#                 else:
#                     user = User.objects.get(phone=identifier)
#                     otp = random.randint(1000, 9999)
#                     user.forgot_password = otp
#                     user.save()
#                     request.session['reset_user_id'] = user.id
#                     # For demo: print OTP to console. For production, integrate SMS API here.
#                     # print(f"Send this OTP to the user's phone via SMS: {otp}")
#                     # send_sms_otp(user.phone, otp)
#                     msg = f"OTP sent to your phone number: {user.phone} (for demo, check console)"
#                 return render(request, "forgot.html", {"show_otp_form": True, "msg": msg})
#             except User.DoesNotExist:
#                 return render(request, "forgot.html", {"msg": "User not found"})
#     return render(request, "forgot.html")

# def otp_verify(request):
#     user_id = request.session.get('reset_user_id')
#     if not user_id:
#         return redirect('forgot_password')
#     user = User.objects.get(id=user_id)
#     if request.method == "POST":
#         otp = request.POST.get('otp')
#         password = request.POST.get('password')
#         confirm_password = request.POST.get('confirm_password')
#         if str(user.forgot_password) == otp:
#             if password == confirm_password:
#                 user.password = password
#                 user.forgot_password = None
#                 user.save()
#                 del request.session['reset_user_id']
#                 return redirect('login')
#             else:
#                 return render(request, "forgot.html", {"msg": "Passwords do not match"})
#         else:
#             return render(request, "forgot.html", {"msg": "Invalid OTP"})
#     return render(request, "login.html")



# def forgot(request):
#     context = {}

#     if request.method == "POST":

#         # -------- SEND OTP --------
#         if "send_otp" in request.POST:
#             email = request.POST.get("email")

#             if not AppUser.objects.filter(email=email).exists():
#                 context["error"] = "Email not registered"
#                 return render(request, "forgot.html", context)

#             otp = random.randint(100000, 999999)

#             request.session["reset_email"] = email
#             request.session["reset_otp"] = str(otp)
#             request.session["otp_time"] = time.time()

#             send_mail(
#                 "Password Reset OTP",
#                 f"Your OTP is {otp}",
#                 settings.EMAIL_HOST_USER,
#                 [email],
#             )

#             context["message"] = "OTP sent to your email"
#             context["otp_sent"] = True
#             return render(request, "forgot.html", context)

#         # -------- VERIFY OTP --------
#         if "verify_otp" in request.POST:
#             entered_otp = request.POST.get("otp")
#             new_password = request.POST.get("new_password")
#             confirm_password = request.POST.get("confirm_password")

#             session_otp = request.session.get("reset_otp")
#             email = request.session.get("reset_email")
#             otp_time = request.session.get("otp_time")

#             # OTP expiry check (5 minutes)
#             if time.time() - otp_time > 300:
#                 context["error"] = "OTP Expired"
#                 return render(request, "forgot.html", context)

#             if entered_otp != session_otp:
#                 context["error"] = "Invalid OTP"
#                 context["otp_sent"] = True
#                 return render(request, "forgot.html", context)

#             if new_password != confirm_password:
#                 context["error"] = "Passwords do not match"
#                 context["otp_sent"] = True
#                 return render(request, "forgot.html", context)

#             user = AppUser.objects.get(email=email)
#             user.set_password(new_password)
#             user.save()

#             # Clear session
#             request.session.flush()

#             context["message"] = "Password reset successful"
#             return render(request, "forgot.html", context)

#     return render(request, "forgot.html", context)

# # def forgot(request):
# #     return render(request,"forgot.html")

# # def send_otp(request):
# #     if request.method == "POST":
# #         email = request.POST.get("email")

# #         otp = random.randint(100000, 999999)

# #         request.session['reset_email'] = email
# #         request.session['reset_otp'] = str(otp)

# #         send_mail(
# #             subject="Your Password Reset OTP",
# #             message=f"Your OTP is: {otp}",
# #             from_email=settings.EMAIL_HOST_USER,
# #             recipient_list=[email],
# #             fail_silently=False,
# #         )

# #         return render(request, "forgot.html", {"message": "OTP sent to your email"})
    
# #     return render(request, "send_otp.html")
